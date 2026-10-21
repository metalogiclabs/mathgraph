#!/usr/bin/env python3
"""Gyro-selected distant image revisit on UZH shapes_rotation.
No ground truth in selection; no heading correction or full revolution claim."""
import argparse,csv,json,zipfile
import cv2,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('--frames',type=int,default=450);a=p.parse_args()
z=zipfile.ZipFile(a.dataset);imu=np.loadtxt(z.open('imu.txt'));gt=np.loadtxt(z.open('groundtruth.txt'))
refs=[(float(t),f) for t,f in (l.split()[:2] for l in z.read('images.txt').decode().splitlines() if l.strip()) if gt[0,0]<=float(t)<=gt[-1,0] and float(t)<=imu[-1,0]][:a.frames]
ts=np.array([t for t,f in refs]);w=np.stack([np.interp(ts,imu[:,0],imu[:,i]) for i in (4,5,6)],axis=1)
rot=[R.identity()]
for i in range(1,len(ts)):rot.append(rot[-1]*R.from_rotvec((w[i-1]+w[i])*.5*(ts[i]-ts[i-1])))
rot=R.concatenate(rot);truth=Slerp(gt[:,0],R.from_quat(gt[:,4:8]))(ts)
orb=cv2.ORB_create(nfeatures=850,fastThreshold=12);kps=[];desc=[]
for _,f in refs:
 im=cv2.imdecode(np.frombuffer(z.read(f),np.uint8),0)
 k,d=orb.detectAndCompute(im,None);kps.append(k);desc.append(d)
bf=cv2.BFMatcher(cv2.NORM_HAMMING)
def match(i,j):
 if desc[i] is None or desc[j] is None:return 0,0
 pairs=bf.knnMatch(desc[i],desc[j],k=2)
 good=[m for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.72*n.distance]
 if len(good)<8:return len(good),0
 x=np.float32([kps[i][m.queryIdx].pt for m in good]);y=np.float32([kps[j][m.trainIdx].pt for m in good])
 H,mask=cv2.findHomography(x,y,cv2.RANSAC,3)
 return len(good),int(mask.sum()) if mask is not None else 0
rows=[]
for i in range(80,len(ts),3):
 opts=np.arange(0,i-30)
 if len(opts)==0:continue
 dist=np.rad2deg((rot[opts].inv()*rot[i]).magnitude())
 j=int(opts[np.argmin(dist)])
 if np.min(dist)>18:continue
 k=int(opts[np.argmax(dist)])
 m,n=match(j,i);cm,cn=match(k,i)
 actual=float(np.rad2deg((truth[j].inv()*truth[i]).magnitude()))
 rows.append(dict(frame=i,previous=j,elapsed_s=float(ts[i]-ts[j]),gyro_predicted_deg=float(np.min(dist)),groundtruth_relative_deg=actual,matches=m,inliers=n,control_matches=cm,control_inliers=cn))
if not rows:raise RuntimeError('No valid revisits')
with open('revisit_results.csv','w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary=dict(dataset='UZH shapes_rotation',frames=len(ts),revisits=len(rows),selected_ge15=sum(r['inliers']>=15 for r in rows),control_ge15=sum(r['control_inliers']>=15 for r in rows),median_selected_inliers=float(np.median([r['inliers'] for r in rows])),median_control_inliers=float(np.median([r['control_inliers'] for r in rows])),median_gt_rotation_deg=float(np.median([r['groundtruth_relative_deg'] for r in rows])),scope='feature reidentification only; far-orientation control is not a performance-matched VO baseline; not a full revolution, absolute heading, or flight test')
open('revisit_summary.json','w').write(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
