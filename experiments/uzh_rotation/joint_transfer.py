#!/usr/bin/env python3
"""Frozen algorithm-transfer evaluation on independent UZH DAVIS rotation scenes.
Per-sequence fit uses visual + gyro only. Motion capture is never used in fit,
convention selection, or model selection; solely for reporting held-out error.
Single sequence split, no uncertainty certification or flight claims.
"""
import argparse,json,zipfile
import numpy as np,cv2
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.optimize import least_squares
p=argparse.ArgumentParser();p.add_argument("dataset");p.add_argument("--frames",type=int,default=450);p.add_argument("--output",default="transfer_summary.json");a=p.parse_args()
with zipfile.ZipFile(a.dataset) as z:
 imu=np.loadtxt(z.open("imu.txt"));gt=np.loadtxt(z.open("groundtruth.txt"));cal=np.loadtxt(z.open("calib.txt")).ravel()
 files=set(z.namelist())
 ents=[(float(t),f) for t,f in (line.split()[:2] for line in z.read("images.txt").decode().splitlines() if line.strip()) if f in files and max(gt[0,0],imu[0,0])<=float(t)<=min(gt[-1,0],imu[-1,0])][:a.frames]
 if len(ents)<300:raise ValueError("insufficient timestamp-aligned images")
 ts=np.array([t for t,_ in ents]);dt=np.diff(ts)
 w=np.stack([np.interp(ts,imu[:,0],imu[:,k]) for k in (4,5,6)],axis=1)
 incs=(w[:-1]+w[1:])*.5*dt[:,None];truth=Slerp(gt[:,0],R.from_quat(gt[:,4:8]))(ts)
 gr=[R.identity()]
 for x in incs:gr.append(gr[-1]*R.from_rotvec(x))
 gyro=R.concatenate(gr)
 K=np.array([[cal[0],0,cal[2]],[0,cal[1],cal[3]],[0,0,1.]])
 orb=cv2.ORB_create(nfeatures=850,fastThreshold=12);matcher=cv2.BFMatcher(cv2.NORM_HAMMING);features=[]
 for _,f in ents:
  im=cv2.imdecode(np.frombuffer(z.read(f),np.uint8),0)
  im=cv2.undistort(im,K,cal[4:9])
  features.append(orb.detectAndCompute(im,None))
 edges=[]
 for i in range(80,len(ts),3):
  opts=np.arange(0,i-30);diff=(gyro[opts].inv()*gyro[i]).magnitude()
  j=int(opts[np.argmin(diff)])
  if np.rad2deg(diff.min())>18:continue
  ka,da=features[j];kb,db=features[i]
  if da is None or db is None:continue
  pairs=matcher.knnMatch(da,db,k=2)
  mm=[m for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.72*n.distance]
  if len(mm)<15:continue
  x=np.float32([ka[m.queryIdx].pt for m in mm]);y=np.float32([kb[m.trainIdx].pt for m in mm])
  H,mask=cv2.findHomography(x,y,cv2.RANSAC,3.)
  if H is None or int(mask.sum())<15:continue
  A=np.linalg.inv(K)@H@K;u,_,vt=np.linalg.svd(A);Rc=u@np.diag([1.,1.,np.linalg.det(u@vt)])@vt
  edges.append((j,i,R.from_matrix(Rc),int(mask.sum())))
 split=220;train=[e for e in edges if e[1]<split];test=[e for e in edges if e[0]>=split]
 def integrate(b):
  rr=[R.identity()]
  for step,d in zip(incs,dt):rr.append(rr[-1]*R.from_rotvec(step-b*d))
  return R.concatenate(rr)
 def score(rr):
  est=rr[split].inv()*rr[split:]
  target=truth[split].inv()*truth[split:]
  return float(np.sqrt(np.mean(np.rad2deg((est.inv()*target).magnitude())**2)))
 raw=score(gyro)
 # Two conventional low-cost checks: reuse an externally frozen bias
 # from the previous shapes_rotation startup experiment; and calibrate
 # from the first 0.3 s of this sequence (not certified stationary).
 prior_bias=np.array([0.051082811871691926,0.0014642931263633785,0.003074659454040601])
 frozen_bias_rmse=score(integrate(prior_bias))
 early=imu[(imu[:,0]>=ts[0]) & (imu[:,0]<ts[0]+0.30),4:7]
 startup_bias_rmse=score(integrate(np.mean(early,axis=0))) if len(early)>5 else None
 if len(train)<20:
  result=dict(dataset=a.dataset,frames=len(ts),training_edges=len(train),test_edges=len(test),gyro_rmse_deg=raw,frozen_prior_bias_rmse_deg=frozen_bias_rmse,startup_window_rmse_deg=startup_bias_rmse,status="INSUFFICIENT_TRAINING_SUPPORT",fitted_rmse_deg=None)
 else:
  sub=train[:20];fits=[]
  for convention in (0,1):
   def residual(v):
    C=R.from_rotvec(v[:3]);rr=integrate(v[3:])
    return np.concatenate([((C*(rc if convention==0 else rc.inv())*C.inv()).inv()*(rr[j].inv()*rr[i])).as_rotvec() for j,i,rc,_ in sub])
   fit=least_squares(residual,np.zeros(6),loss="soft_l1",f_scale=.05,max_nfev=70,bounds=([-3.14]*3+[-.2]*3,[3.14]*3+[.2]*3))
   fits.append((fit.cost,convention,fit))
  cost,k,fit=min(fits,key=lambda v:v[0])
  # Compare candidate and frozen prior using identical *training-only*
  # visual constraints and a declared complexity penalty.
  def edge_rms(b,orientation):
   C=R.from_rotvec(orientation)
   rr=integrate(b)
   return float(np.sqrt(np.mean([np.linalg.norm(((C*(rc if k==0 else rc.inv())*C.inv()).inv()*(rr[j].inv()*rr[i])).as_rotvec())**2 for j,i,rc,_ in sub])))
  candidate_residual=edge_rms(fit.x[3:],fit.x[:3])
  prior_residual=edge_rms(prior_bias,fit.x[:3])
  # A conventional calibration-selection rule: require a strictly
  # lower training residual with an absolute margin (radians).
  selector_margin=0.005
  accepted=bool(fit.success and np.isfinite(candidate_residual) and candidate_residual+selector_margin<prior_residual)
  selected_bias=fit.x[3:] if accepted else prior_bias
  # Independent within-training holdout: first 10 revisit edges fit, next
  # 10 select. No motion capture, and no evaluation-holdout feedback.
  selection_fit=train[:10]
  selection_check=train[10:20]
  def independent_check(v,convention,subset):
   C=R.from_rotvec(v[:3]);rr=integrate(v[3:])
   return float(np.sqrt(np.mean([np.linalg.norm(((C*(rc if convention==0 else rc.inv())*C.inv()).inv()*(rr[j].inv()*rr[i])).as_rotvec())**2 for j,i,rc,_ in subset])))
  competing=[]
  for convention in (0,1):
   def first_ten_residual(v):
    C=R.from_rotvec(v[:3]);rr=integrate(v[3:])
    return np.concatenate([((C*(rc if convention==0 else rc.inv())*C.inv()).inv()*(rr[j].inv()*rr[i])).as_rotvec() for j,i,rc,_ in selection_fit])
   fit10=least_squares(first_ten_residual,np.zeros(6),loss="soft_l1",f_scale=.05,max_nfev=70,bounds=([-3.14]*3+[-.2]*3,[3.14]*3+[.2]*3))
   competing.append((fit10.cost,convention,fit10))
  _,conv10,fit10=min(competing,key=lambda t:t[0])
  # Fair prior baseline: optimize its extrinsic orientation on same first
  # ten samples, but keep its previously measured gyro bias frozen.
  def prior_first_ten(c):
   v=np.r_[c,prior_bias]
   C=R.from_rotvec(c);rr=integrate(prior_bias)
   return np.concatenate([((C*(rc if conv10==0 else rc.inv())*C.inv()).inv()*(rr[j].inv()*rr[i])).as_rotvec() for j,i,rc,_ in selection_fit])
  fit_prior=least_squares(prior_first_ten,np.zeros(3),loss="soft_l1",f_scale=.05,max_nfev=70,bounds=(-np.pi*np.ones(3),np.pi*np.ones(3)))
  held_candidate=independent_check(fit10.x,conv10,selection_check)
  held_prior=independent_check(np.r_[fit_prior.x,prior_bias],conv10,selection_check)
  crossfit_accept=bool(fit10.success and fit_prior.success and held_candidate+0.005<held_prior)
  crossfit_rmse=score(integrate(fit10.x[3:] if crossfit_accept else prior_bias))
  # Finite-difference observability diagnostic on the same 10 fitting
  # edges. Dimensionless column scaling corresponds to 0.1 rad
  # extrinsic changes and 0.01 rad/s gyro bias changes.
  jac=fit10.jac @ np.diag([.1,.1,.1,.01,.01,.01])
  singular=np.linalg.svd(jac,compute_uv=False)
  obs_ratio=float(singular[-1]/singular[0]) if singular[0]>1e-12 else 0.0
  obs_pass=bool(singular[-1]>=0.01 and obs_ratio>=0.02)
  observable_accept=bool(crossfit_accept and obs_pass)
  observable_rmse=score(integrate(fit10.x[3:] if observable_accept else prior_bias))
  result=dict(dataset=a.dataset,frames=len(ts),training_edges=len(train),test_edges=len(test),gyro_rmse_deg=raw,frozen_prior_bias_rmse_deg=frozen_bias_rmse,startup_window_rmse_deg=startup_bias_rmse,fitted_rmse_deg=score(integrate(fit.x[3:])),selected_rmse_deg=score(integrate(selected_bias)),selected_candidate=accepted,crossfit_selected_candidate=crossfit_accept,observability_selected_candidate=observable_accept,observability_rmse_deg=observable_rmse,scaled_jacobian_min_singular=float(singular[-1]),scaled_jacobian_ratio=obs_ratio,observability_pass=obs_pass,crossfit_rmse_deg=crossfit_rmse,crossfit_validation_candidate_rad=held_candidate,crossfit_validation_prior_rad=held_prior,training_prior_residual_rad=prior_residual,training_candidate_residual_rad=candidate_residual,selector_margin_rad=selector_margin,convention=k,training_cost=float(cost),fit_success=bool(fit.success),bias_rad_s=fit.x[3:].tolist(),status="CANDIDATE" if fit.success else "OPTIMIZER_NOT_CONVERGED")
 result["verification_boundary"]="Same predeclared method/settings on new scenes; GT used only for score, still per-sequence calibration. Not real spinning-drone flight or standard VIO benchmark."
 open(a.output,"w").write(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
