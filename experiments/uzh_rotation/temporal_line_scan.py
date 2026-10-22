#!/usr/bin/env python3
"""Timestamped one-column rotating-camera scan feasibility audit.

Each image contributes ONLY one central column sampled at its timestamp.
The gyro integrates rotation between acquisitions; yaw-indexed columns are
assembled as a sparse panorama. Empty angle bins stay unobserved.

This is genuine *temporal column acquisition from recorded frames*, but still
a synthetic sensor proxy: DAVIS exposures are global-frame images, not
Joshua's line camera. No panoramic filling from unseen image columns.
Motion capture is used ONLY for post-hoc evaluation.
"""
import argparse, json, time, zipfile
import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

p=argparse.ArgumentParser()
p.add_argument("dataset")
p.add_argument("--frames",type=int,default=450)
p.add_argument("--bins",type=int,default=72)
p.add_argument("--blackout-start",type=int,default=280)
p.add_argument("--blackout-length",type=int,default=90)
p.add_argument("--output",default="temporal_scan.json")
a=p.parse_args()
start=time.perf_counter()
with zipfile.ZipFile(a.dataset) as z:
    imu=np.loadtxt(z.open("imu.txt"))
    gt=np.loadtxt(z.open("groundtruth.txt"))
    cal=np.loadtxt(z.open("calib.txt")).ravel()
    files=set(z.namelist())
    ents=[(float(t),path) for t,path in
          (line.split()[:2] for line in z.read("images.txt").decode().splitlines() if line.strip())
          if path in files and max(gt[0,0],imu[0,0])<=float(t)<=min(gt[-1,0],imu[-1,0])][:a.frames]
    ts=np.array([t for t,_ in ents])
    if len(ts)<300: raise ValueError("too few aligned frames")
    w=np.stack([np.interp(ts,imu[:,0],imu[:,k]) for k in (4,5,6)],axis=1)
    dt=np.diff(ts)
    prior_bias=np.array([0.051082811871691926,0.0014642931263633785,0.003074659454040601])
    gyro=[R.identity()]
    for x,d in zip(.5*(w[:-1]+w[1:])*dt[:,None],dt):
        gyro.append(gyro[-1]*R.from_rotvec(x-prior_bias*d))
    truth=Slerp(gt[:,0],R.from_quat(gt[:,4:8]))(ts)
    columns=[]
    decode_s=0.0
    for _,path in ents:
        tick=time.perf_counter()
        im=cv2.imdecode(np.frombuffer(z.read(path),np.uint8),cv2.IMREAD_GRAYSCALE)
        # One unrectified detector column only; undistorting the entire
        # image would implicitly use neighboring unavailable sensor pixels.
        columns.append(im[:,im.shape[1]//2].astype(np.float32))
        decode_s+=time.perf_counter()-tick

# Sensing phase: wrapped relative yaw of gyro-integrated attitude. This
# requires gravity alignment and is NOT an actual unambiguous heading sensor.
yaw=np.unwrap(np.array([r.as_euler("zyx")[0] for r in gyro]))
turns=float((yaw.max()-yaw.min())/(2*np.pi))
bins=np.mod(np.floor(np.mod(yaw,2*np.pi)*a.bins/(2*np.pi)).astype(int),a.bins)
split=220
train={};held={};matches=[]
for i in range(len(ts)):
    if a.blackout_start<=i<a.blackout_start+a.blackout_length:continue
    b=int(bins[i])
    # No lookahead: only previous observations can be matched.
    if i<split:
        train.setdefault(b,[]).append(i)
    else:
        held.setdefault(b,[]).append(i)
        prior=train.get(b,[])
        if prior:
            # A single earlier scan sample at same gyro-predicted direction.
            j=prior[-1]
            x=columns[i]-columns[i].mean()
            y=columns[j]-columns[j].mean()
            corr=float(x@y/(np.linalg.norm(x)*np.linalg.norm(y)+1e-9))
            matches.append((i,j,corr))
# Measure actual evidence availability. Correlation is not heading truth:
# no angular sub-bin estimator or loop-closure correction is implied.
strong=[(i,j,c) for i,j,c in matches if c>=0.7]
matched_after=[i for i,j,c in strong if i>=a.blackout_start+a.blackout_length]
reacquire_idx=min(matched_after) if matched_after else None
time_after=(float(ts[reacquire_idx]-ts[a.blackout_start+a.blackout_length])
            if reacquire_idx is not None and a.blackout_start+a.blackout_length<len(ts) else None)
grel=gyro[split].inv()*R.concatenate(gyro[split:])
trel=truth[split].inv()*truth[split:]
err=np.rad2deg((grel.inv()*trel).magnitude())
out=dict(dataset=a.dataset,frames=len(ts),image_rows=len(columns[0]),
         actual_pixels_per_sample=len(columns[0]),
         acquisition_is_one_real_column_per_recorded_frame=True,
         is_physical_line_camera=False,gyro_angular_excursion_turns=turns,
         bins=a.bins,train_angular_bins=len(train),test_angular_bins=len(held),
         train_bin_coverage=len(train)/a.bins,test_bin_coverage=len(held)/a.bins,
         revisit_candidates=len(matches),strong_correlated_revisits=len(strong),
         blacklist=[a.blackout_start,a.blackout_start+a.blackout_length],
         first_correlated_revisit_after_blackout=reacquire_idx,
         seconds_to_first_correlated_revisit=time_after,
         calibrated_gyro_orientation_rmse_deg=float(np.sqrt(np.mean(err*err))),
         no_visual_correction_claim=True,decode_seconds=decode_s,
         total_processing_seconds=time.perf_counter()-start,
         limitation="One-column time-series from 240x180 DAVIS frames, binned by gyro yaw. Correlated columns can share gyro error; this does not establish independently observable heading or a validated relocalization.")
open(a.output,"w").write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
