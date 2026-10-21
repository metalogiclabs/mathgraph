#!/usr/bin/env python3
"""Exploratory relative-heading comparison; calibration first 30%, holdout 70%.
Not absolute heading; visual homography rotation is approximate.
"""
import argparse,csv,json,zipfile
import cv2,numpy as np
from scipy.spatial.transform import Rotation,Slerp
def tab(z,p):
 return np.array([[float(a) for a in l.split()] for l in z.read(p).decode().splitlines() if l.strip() and not l.startswith('#')])
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset");p.add_argument("--pairs",type=int,default=300);p.add_argument("--output",default="heading.csv");a=p.parse_args()
 with zipfile.ZipFile(a.dataset) as z:
  imu=tab(z,"imu.txt");gt=tab(z,"groundtruth.txt");cal=tab(z,"calib.txt").ravel();names=set(z.namelist())
  frames=[]
  for line in z.read("images.txt").decode().splitlines():
   if not line.strip() or line.startswith("#"):continue
   t,f=line.split()[:2];t=float(t)
   if f in names and max(imu[0,0],gt[0,0])<=t<=min(imu[-1,0],gt[-1,0]):frames.append((t,f))
  frames=frames[:a.pairs+1]
  if len(frames)<30:raise RuntimeError("Insufficient frames")
  K=np.array([[cal[0],0,cal[2]],[0,cal[1],cal[3]],[0,0,1.]])
  rg=Slerp(gt[:,0],Rotation.from_quat(gt[:,4:8]))(np.array([t for t,_ in frames]))
  truth3=(rg[:-1].inv()*rg[1:]).as_rotvec()
  dt=np.diff([t for t,_ in frames])
  def gyro(t0,t1):
   m=imu[(imu[:,0]>t0)&(imu[:,0]<t1)]
   ts=np.r_[t0,m[:,0],t1]
   W=np.stack([np.interp(ts,imu[:,0],imu[:,k]) for k in (4,5,6)],axis=1)
   return np.sum((W[1:]+W[:-1])*.5*np.diff(ts)[:,None],axis=0)
  dg3=np.array([gyro(frames[i][0],frames[i+1][0]) for i in range(len(frames)-1)])
  n=len(dg3);split=max(10,int(.3*n))
  _,_,V=np.linalg.svd(dg3[:split],full_matrices=False);axis=V[0]
  if axis@np.sum(dg3[:split],axis=0)<0:axis=-axis
  U,_,V=np.linalg.svd(dg3[:split].T@truth3[:split])
  M=U@np.diag([1,1,np.linalg.det(U@V)])@V
  truth=truth3@(axis@M);dg=dg3@axis
  orb=cv2.ORB_create(nfeatures=1300,fastThreshold=12);bf=cv2.BFMatcher(cv2.NORM_HAMMING)
  def extract(path):
   im=cv2.imdecode(np.frombuffer(z.read(path),np.uint8),0)
   return orb.detectAndCompute(cv2.undistort(im,K,cal[4:9]),None)
  k0,d0=extract(frames[0][1]);vv=[];counts=[]
  for t,path in frames[1:]:
   k1,d1=extract(path);v=np.array([np.nan]*3);count=0
   if d0 is not None and d1 is not None:
    good=[m for pair in bf.knnMatch(d0,d1,k=2) if len(pair)==2 for m,n2 in [pair] if m.distance<.73*n2.distance]
    if len(good)>=12:
     x=np.float32([k0[m.queryIdx].pt for m in good]);y=np.float32([k1[m.trainIdx].pt for m in good])
     srcn=cv2.undistortPoints(x.reshape(-1,1,2),K,None).reshape(-1,2)
     dstn=cv2.undistortPoints(y.reshape(-1,1,2),K,None).reshape(-1,2)
     E,mask=cv2.findEssentialMat(srcn,dstn,np.eye(3),cv2.RANSAC,0.999,0.002)
     if E is not None:
      if E.shape[0]>3:E=E[:3,:]
      count,R,t,posemask=cv2.recoverPose(E,srcn,dstn,np.eye(3),mask=mask)
      if count>=12:
       v=Rotation.from_matrix(R).as_rotvec()
   vv.append(v);counts.append(count);k0,d0=k1,d1
  vv=np.array(vv);counts=np.array(counts)
  good=np.isfinite(vv).all(axis=1)&(counts>=12)
  train=good[:split];coef=np.linalg.lstsq(vv[:split][train],dg[:split][train],rcond=None)[0]
  visual=np.full(n,np.nan);visual[good]=vv[good]@coef
  bias=np.median((dg[:split][train]-visual[:split][train])/dt[:split][train])
  corrected=dg-bias*dt
  ground=np.cumsum(truth[split:]);raw=np.cumsum(dg[split:]);corr=np.cumsum(corrected[split:])
  fused=[];state=0.;age=0.;active=[]
  for i in range(split,n):
   if np.isfinite(visual[i]) and abs(visual[i]-corrected[i])<np.deg2rad(8):
    increment=.6*corrected[i]+.4*visual[i];age=0.
   else:increment=corrected[i];age+=dt[i]
   state+=increment;fused.append(state);active.append(age<.5)
  fused=np.array(fused)
  rmse=lambda q:float(np.sqrt(np.mean(np.rad2deg(q-ground)**2)))
  summary=dict(estimator="calibrated-essential-matrix",total_pairs=n,calibration_pairs=split,holdout_pairs=n-split,holdout_visual_coverage=float(np.mean(good[split:])),gyro_only_rmse_deg=rmse(raw),gyro_bias_corrected_rmse_deg=rmse(corr),visual_gyro_fused_rmse_deg=rmse(fused),authorized_fraction=float(np.mean(active)),scope="relative one-dimensional rotation; GT used on training portion for coordinate calibration; no global heading or flight claims")
  with open(a.output,"w",newline="") as f:
   w=csv.writer(f);w.writerow(["time","truth_rel_deg","gyro_rel_deg","corrected_rel_deg","fused_rel_deg","inliers","visual_valid"])
   for j,i in enumerate(range(split,n)):w.writerow([frames[i+1][0],np.rad2deg(ground[j]),np.rad2deg(raw[j]),np.rad2deg(corr[j]),np.rad2deg(fused[j]),int(counts[i]),int(good[i])])
  with open("heading_summary.json","w") as f:json.dump(summary,f,indent=2)
  print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
