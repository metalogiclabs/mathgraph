#!/usr/bin/env python3
"""Causal revisiting-image visual compass on UZH DAVIS rotation recordings.

Prototype with full-frame ORB features, not a line-scan sensor. Frames are
processed in timestamp order. Ground truth is used ONLY to score outcomes.
A fixed previously learned gyro bias is an explicit conventional baseline.
"""
import argparse
import json
import zipfile

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R, Slerp

p = argparse.ArgumentParser()
p.add_argument("dataset")
p.add_argument("--frames", type=int, default=450)
p.add_argument("--strip-width",type=int,default=0,help="center pixel strip width; 0=full frame")
p.add_argument("--blackout-start",type=int,default=-1)
p.add_argument("--blackout-length",type=int,default=0)
p.add_argument("--output", default="visual_compass.json")
a = p.parse_args()

with zipfile.ZipFile(a.dataset) as z:
    imu = np.loadtxt(z.open("imu.txt"))
    gt = np.loadtxt(z.open("groundtruth.txt"))
    cal = np.loadtxt(z.open("calib.txt")).ravel()
    files = set(z.namelist())
    ents = [(float(t), path) for t, path in
            (line.split()[:2] for line in z.read("images.txt").decode().splitlines() if line.strip())
            if path in files and max(gt[0,0], imu[0,0]) <= float(t) <= min(gt[-1,0], imu[-1,0])]
    ents = ents[:a.frames]
    if len(ents) < 300:
        raise ValueError("not enough aligned images")
    ts = np.array([x[0] for x in ents])
    dt = np.diff(ts)
    w = np.stack([np.interp(ts, imu[:,0], imu[:,k]) for k in (4,5,6)], axis=1)
    incs = .5*(w[:-1]+w[1:])*dt[:,None]
    truth = Slerp(gt[:,0], R.from_quat(gt[:,4:8]))(ts)
    K = np.array([[cal[0],0,cal[2]],[0,cal[1],cal[3]],[0,0,1.]])
    orb = cv2.ORB_create(nfeatures=850, fastThreshold=12)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    features = []
    image_dimensions = None
    effective_strip_width = None
    for _, path in ents:
        im = cv2.imdecode(np.frombuffer(z.read(path), np.uint8), cv2.IMREAD_GRAYSCALE)
        im = cv2.undistort(im, K, cal[4:9])
        image_dimensions = list(im.shape)
        effective_strip_width = min(a.strip_width,im.shape[1]) if a.strip_width else im.shape[1]
        # Limited-information vertical-window proxy only.
        # NOT a time-swept line sensor: no scan-motion geometry.
        mask = None
        if a.strip_width:
            mask = np.zeros_like(im,dtype=np.uint8)
            x0=max(0,im.shape[1]//2-a.strip_width//2)
            mask[:,x0:min(im.shape[1],x0+a.strip_width)] = 255
        features.append(orb.detectAndCompute(im,mask))

prior_bias = np.array([0.051082811871691926,0.0014642931263633785,0.003074659454040601])
def integrated(b):
    xs = [R.identity()]
    for x, d in zip(incs, dt):
        xs.append(xs[-1]*R.from_rotvec(x-b*d))
    return xs

raw = integrated(np.zeros(3))
prior = integrated(prior_bias)
split = 220
# Revisit search is causal; all indices considered for j are earlier than i.
# Feature matches are never chosen using motion-capture truth.
edges = []
for i in range(80,len(ts),3):
    opts = np.arange(0,i-30)
    diff = np.array([(prior[j].inv()*prior[i]).magnitude() for j in opts])
    j = int(opts[np.argmin(diff)])
    if np.rad2deg(diff.min()) > 18:
        continue
    ka, da = features[j]
    kb, db = features[i]
    if da is None or db is None:
        continue
    knn = matcher.knnMatch(da,db,k=2)
    good = [m for pair in knn if len(pair)==2 for m,n in [pair] if m.distance < .72*n.distance]
    if len(good)<15:
        continue
    x = np.float32([ka[m.queryIdx].pt for m in good])
    y = np.float32([kb[m.trainIdx].pt for m in good])
    H, mask = cv2.findHomography(x,y,cv2.RANSAC,3.)
    if H is None or int(mask.sum())<15:
        continue
    A = np.linalg.inv(K)@H@K
    u,_,v = np.linalg.svd(A)
    M = u@np.diag([1.,1.,np.linalg.det(u@v)])@v
    edges.append((j,i,R.from_matrix(M),int(mask.sum())))

train = [e for e in edges if e[1]<split]
test = [e for e in edges if e[0]>=split]
if len(train)<10:
    raise ValueError("insufficient visual training edges")
# Estimate fixed IMU-camera rotation and transformation convention from
# training-only matches, holding gyro bias at its externally frozen value.
fits=[]
for convention in (0,1):
    def residual(c):
        C=R.from_rotvec(c)
        return np.concatenate([((C*(rc if convention==0 else rc.inv())*C.inv()).inv()*
                      (prior[j].inv()*prior[i])).as_rotvec() for j,i,rc,_ in train[:20]])
    fit=least_squares(residual,np.zeros(3),loss="soft_l1",f_scale=.05,
                      bounds=(-np.pi*np.ones(3),np.pi*np.ones(3)),max_nfev=80)
    fits.append((fit.cost,convention,fit.x))
_,convention,extrinsic=min(fits,key=lambda t:t[0])
C=R.from_rotvec(extrinsic)
checks={i:[] for i in range(split,len(ts))}
for j,i,rc,n in test:
    if a.blackout_start<=i<a.blackout_start+a.blackout_length:
        continue
    checks[i].append((j,C*(rc if convention==0 else rc.inv())*C.inv(),n))

def simulate(gain):
    xs=prior[:split+1].copy()
    accepted=0
    rejected=0
    # Every correction is applied only when the arriving image is available.
    for i in range(split+1,len(ts)):
        estimate=xs[-1]*R.from_rotvec(incs[i-1]-prior_bias*dt[i-1])
        for j,visual,n in checks.get(i,[]):
            innovation=(estimate.inv()*(xs[j]*visual)).as_rotvec()
            if not np.all(np.isfinite(innovation)) or np.linalg.norm(innovation)>np.deg2rad(25):
                rejected+=1
                continue
            estimate=estimate*R.from_rotvec(gain*innovation)
            accepted+=1
        xs.append(estimate)
    return xs,accepted,rejected

def score(xs):
    # Only the held-out future relative to its first state matters.
    target=truth[split].inv()*truth[split:]
    estimate=xs[split].inv()*R.concatenate(xs[split:])
    errors=np.rad2deg((estimate.inv()*target).magnitude())
    return dict(rmse_deg=float(np.sqrt(np.mean(errors**2))),
                final_error_deg=float(errors[-1]),
                max_error_deg=float(np.max(errors)))

compass,accepted,rejected=simulate(0.25)
zero,_,_=simulate(0.)
result=dict(dataset=a.dataset,frames=len(ts),train_edges=len(train),
            heldout_revisits=len(test),strip_width=a.strip_width,image_dimensions=image_dimensions,effective_strip_width=effective_strip_width,blackout_start=a.blackout_start,blackout_length=a.blackout_length,accepted_revisits=accepted,rejected_revisits=rejected,
            convention=convention,train_only_extrinsic_rotvec=extrinsic.tolist(),
            gyro_raw=score(raw),gyro_frozen_prior=score(prior),
            zero_visual_gain=score(zero),visual_compass=score(compass),
            result_scope="ORB revisit correction on full frame or masked static vertical strip (NOT motion-swept line-scan); prior gyro bias externally calibrated, same sensor family; not line-scan, embedded hardware, or flight. Ground truth score-only.")
with open(a.output,"w") as f:
    json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
