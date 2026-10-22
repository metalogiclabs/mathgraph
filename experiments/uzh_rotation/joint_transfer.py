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
  # SVD projection of the *change from prior*, not absolute parameters.
  # Scale dimensions to comparable perturbation units. The prior extrinsic
  # is fit using identical fitting edges; no held-out truth is consulted.
  scales=np.array([.1,.1,.1,.01,.01,.01])
  _,svals,Vt=np.linalg.svd(fit10.jac*scales[None,:],full_matrices=False)
  delta=(fit10.x-np.r_[fit_prior.x,prior_bias])/scales
  strong=svals>=0.01
  basis=Vt[strong,:]
  projected_delta=basis.T@(basis@delta) if len(basis) else np.zeros(6)
  projected=np.r_[fit_prior.x,prior_bias]+scales*projected_delta
  projected_validation=independent_check(projected,conv10,selection_check)
  partial_accept=bool(fit10.success and fit_prior.success and projected_validation+.005<held_prior)
  partial_bias=projected[3:] if partial_accept else prior_bias
  partial_rmse=score(integrate(partial_bias))
  # Equally informed conventional Tikhonov filter of the same SVD.
  # No claim of MathGraph algorithmic novelty without beating this.
  ridge_strength=.01
  ridge_gain=svals*svals/(svals*svals+ridge_strength*ridge_strength)
  ridge_delta=Vt.T@(ridge_gain*(Vt@delta))
  ridge=np.r_[fit_prior.x,prior_bias]+scales*ridge_delta
  ridge_validation=independent_check(ridge,conv10,selection_check)
  ridge_accept=bool(fit10.success and fit_prior.success and ridge_validation+.005<held_prior)
  ridge_rmse=score(integrate(ridge[3:] if ridge_accept else prior_bias))
  # Evidence-diversity test: evaluate the proposed partial update on
  # separate motion families defined WITHOUT truth or validation residuals.
  # These are two gyro-derived duration / rotation-excitation categories.
  # Abstain if either category has fewer than 3 validation observations.
  def family(e):
   j,i,_,_=e
   gyro_vec=(gyro[j].inv()*gyro[i]).as_rotvec()
   # Orientation-independent angular excursion magnitude; threshold
   # declared before observing either unseen-scene result.
   return int(np.linalg.norm(gyro_vec)>=np.deg2rad(12))
  families={g:[e for e in selection_check if family(e)==g] for g in (0,1)}
  supported_families=all(len(group)>=3 for group in families.values())
  family_stats=[]
  if supported_families:
   for group in families.values():
    candidate_err=independent_check(projected,conv10,group)
    old_err=independent_check(np.r_[fit_prior.x,prior_bias],conv10,group)
    family_stats.append(dict(n=len(group),candidate_rad=candidate_err,prior_rad=old_err,
                             improvement_rad=old_err-candidate_err))
  diverse_accept=bool(partial_accept and supported_families and
                      all(x["improvement_rad"]>=0.005 for x in family_stats))
  diverse_rmse=score(integrate(projected[3:] if diverse_accept else prior_bias))


  # Bounded reversible recalibration: gradual bias change over the holdout,
  # keeping prior calibration recoverable. This is an OPEN-LOOP holdout
  # simulation, not a flight controller or a deployed online monitor.
  def bounded_trajectory(target_bias, fraction):
   # fraction is a fixed deployment limit, not fitted to GT.
   b=prior_bias+fraction*(target_bias-prior_bias)
   return score(integrate(b))
  bounded_25_rmse=bounded_trajectory(fit.x[3:],.25)
  bounded_50_rmse=bounded_trajectory(fit.x[3:],.50)
  bounded_subspace_25_rmse=bounded_trajectory(projected[3:],.25)
  # Conventional gradual adaptation baseline: identical interpolation.
  # A different label cannot constitute an independent advantage.
  conventional_25_rmse=bounded_25_rmse
  # Causal replay: proposed calibration becomes available only after
  # training. Revisit checks are released at their actual end index.
  # A previous accepted update cannot retroactively change past state.
  # This is a lightweight bias-only replay, not a flight controller.
  def replay(candidate, policy):
   estimated=R.identity();prior_est=R.identity()
   current=prior_bias.copy();active=False;accepted=0;withdrawn=0
   tracker=[];time_errors=[]
   visible=sorted(test,key=lambda e:e[1]);ptr=0
   for i in range(split,len(incs)):
    # The test residual uses only revisits ending at/before i.
    while ptr<len(visible) and visible[ptr][1]<=i:
     ptr+=1
    recent=visible[max(0,ptr-5):ptr]
    if policy!="fixed" and len(recent)>=3:
     # Evaluate candidate/prior against independent, matured checks.
     cand_err=independent_check(np.r_[fit10.x[:3],candidate],conv10,recent)
     base_err=independent_check(np.r_[fit_prior.x,prior_bias],conv10,recent)
     should_use=bool(cand_err+0.005<base_err)
     if policy=="gradual":should_use=True
     if should_use and not active:accepted+=1
     if not should_use and active:withdrawn+=1
     active=should_use
    target=prior_bias if not active else prior_bias+0.25*(candidate-prior_bias)
    # Bounded per-timestep change; this makes rollback gradual.
    max_step=.002
    step=np.clip(target-current,-max_step,max_step)
    current=current+step
    estimated=estimated*R.from_rotvec(incs[i]-current*dt[i])
    prior_est=prior_est*R.from_rotvec(incs[i]-prior_bias*dt[i])
    true_rel=truth[split].inv()*truth[i+1]
    time_errors.append(np.rad2deg((estimated.inv()*true_rel).magnitude()))
    tracker.append(np.linalg.norm(current-prior_bias))
   return dict(rmse_deg=float(np.sqrt(np.mean(np.square(time_errors)))),
               accepted=accepted,withdrawn=withdrawn,
               active_final=active,mean_delta_rad_s=float(np.mean(tracker)))
  replay_fixed=replay(fit10.x[3:],"fixed")
  replay_conventional=replay(fit10.x[3:],"gradual")
  replay_evidence=replay(fit10.x[3:],"evidence")
  result=dict(dataset=a.dataset,frames=len(ts),training_edges=len(train),test_edges=len(test),gyro_rmse_deg=raw,frozen_prior_bias_rmse_deg=frozen_bias_rmse,startup_window_rmse_deg=startup_bias_rmse,fitted_rmse_deg=score(integrate(fit.x[3:])),selected_rmse_deg=score(integrate(selected_bias)),selected_candidate=accepted,crossfit_selected_candidate=crossfit_accept,observability_selected_candidate=observable_accept,observability_rmse_deg=observable_rmse,partial_subspace_rmse_deg=partial_rmse,evidence_diverse_rmse_deg=diverse_rmse,bounded_25_rmse_deg=bounded_25_rmse,causal_replay_fixed=replay_fixed,causal_replay_conventional=replay_conventional,causal_replay_evidence=replay_evidence,bounded_50_rmse_deg=bounded_50_rmse,bounded_subspace_25_rmse_deg=bounded_subspace_25_rmse,conventional_gradual_25_rmse_deg=conventional_25_rmse,evidence_diverse_accepted=diverse_accept,evidence_diverse_supported_families=supported_families,evidence_diverse_family_sizes=[len(families[x]) for x in (0,1)],evidence_diverse_family_validation=family_stats,partial_subspace_accepted=partial_accept,partial_subspace_rank=int(strong.sum()),partial_validation_rad=projected_validation,ridge_rmse_deg=ridge_rmse,ridge_accepted=ridge_accept,ridge_validation_rad=ridge_validation,scaled_jacobian_min_singular=float(singular[-1]),scaled_jacobian_ratio=obs_ratio,observability_pass=obs_pass,crossfit_rmse_deg=crossfit_rmse,crossfit_validation_candidate_rad=held_candidate,crossfit_validation_prior_rad=held_prior,training_prior_residual_rad=prior_residual,training_candidate_residual_rad=candidate_residual,selector_margin_rad=selector_margin,convention=k,training_cost=float(cost),fit_success=bool(fit.success),bias_rad_s=fit.x[3:].tolist(),status="CANDIDATE" if fit.success else "OPTIMIZER_NOT_CONVERGED")
 result["verification_boundary"]="Same predeclared method/settings on new scenes; GT used only for score, still per-sequence calibration. Not real spinning-drone flight or standard VIO benchmark."
 open(a.output,"w").write(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
