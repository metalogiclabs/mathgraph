#!/usr/bin/env python3
"""Diagnostic: separate gyro bias, extrinsic rotation, and loop-closure effects.
Truth is used only for scoring unless explicitly labelled oracle calibration.
The early low-motion window is not guaranteed to be stationary.
"""
import json,zipfile,argparse
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
p=argparse.ArgumentParser();p.add_argument("dataset");p.add_argument("--output",default="gyro_bias_summary.json");a=p.parse_args()
with zipfile.ZipFile(a.dataset) as z:
 imu=np.loadtxt(z.open("imu.txt"));gt=np.loadtxt(z.open("groundtruth.txt"))
 refs=[(float(t),f) for t,f in (s.split()[:2] for s in z.read("images.txt").decode().splitlines() if s.strip()) if max(gt[0,0],imu[0,0])<=float(t)<=min(gt[-1,0],imu[-1,0])][:450]
ts=np.array([t for t,_ in refs]);dt=np.diff(ts);s=220
w=np.stack([np.interp(ts,imu[:,0],imu[:,i]) for i in (4,5,6)],axis=1)
raw_inc=(w[:-1]+w[1:])*.5*dt[:,None]
truth=Slerp(gt[:,0],R.from_quat(gt[:,4:8]))(ts)
gt_inc=(truth[:-1].inv()*truth[1:]).as_rotvec()
U,_,V=np.linalg.svd(raw_inc[:s].T@gt_inc[:s]);Q=U@np.diag([1,1,np.linalg.det(U@V)])@V
oracle_bias=np.sum(raw_inc[:s]@Q-gt_inc[:s],axis=0)/np.sum(dt[:s])
start=imu[(imu[:,0]>=0.02)&(imu[:,0]<0.32)]
startup_bias=np.mean(start[:,4:7],axis=0)
def score(inc):
 r=[R.identity()]
 for v in inc:r.append(r[-1]*R.from_rotvec(v))
 measured=R.concatenate(r);t=truth[s:]
 return float(np.sqrt(np.mean(np.rad2deg(((t[0]*measured).inv()*t).magnitude())**2)))
result={
 "dataset":"UZH shapes_rotation","calibration_intervals":s,"holdout_intervals":len(raw_inc)-s,
 "uncorrected_rmse_deg":score(raw_inc[s:]),
 "startup_bias_rmse_deg":score(raw_inc[s:]-dt[s:,None]*startup_bias),
 "oracle_training_bias_rmse_deg":score((raw_inc[s:]-dt[s:,None]*(oracle_bias@Q.T))@Q),
 "startup_bias_rad_s":startup_bias.tolist(),
 "oracle_bias_rad_s":oracle_bias.tolist(),
 "notes":["Startup bias estimated from raw gyro only in first 0.30 seconds; low motion, not proven stationary.","Oracle bias and alignment require ground-truth motion in calibration segment; diagnostic only.","Results are held-out relative SO(3) orientation, not absolute heading or drone flight.","No visual-estimator or robust-loop-closure advantage is claimed."]
}
open(a.output,"w").write(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
