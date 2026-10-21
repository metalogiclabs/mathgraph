#!/usr/bin/env python3
"""Exploratory UZH DAVIS shapes_rotation relative angle magnitude benchmark.
NOT absolute yaw, not drone flight validation."""
import argparse,csv,json,zipfile
import cv2,numpy as np
from scipy.spatial.transform import Rotation,Slerp

def table(z,name):
    rows=[]
    for s in z.read(name).decode().splitlines():
        if not s.strip() or s.lstrip().startswith('#'): continue
        rows.append([float(t) for t in s.split()])
    return np.asarray(rows)
def angle(r):
    return np.linalg.norm(r.as_rotvec())*180/np.pi
def main():
    p=argparse.ArgumentParser()
    p.add_argument("dataset")
    p.add_argument("--pairs",type=int,default=300)
    p.add_argument("--output",default="rotation_results.csv")
    a=p.parse_args()
    with zipfile.ZipFile(a.dataset) as z:
        gt=table(z,"groundtruth.txt")
        imu=table(z,"imu.txt")
        cal=table(z,"calib.txt").ravel()
        K=np.array([[cal[0],0,cal[2]],[0,cal[1],cal[3]],[0,0,1]],dtype=float)
        valid=(gt[:,0]>=imu[0,0])&(gt[:,0]<=imu[-1,0])
        g=gt[valid]
        spline=Slerp(g[:,0],Rotation.from_quat(g[:,4:8]))
        refs=[]
        for line in z.read("images.txt").decode().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):continue
            t,f=line.split()[:2]
            t=float(t)
            if g[0,0]<=t<=g[-1,0] and f in z.namelist():refs.append((t,f))
        orb=cv2.ORB_create(nfeatures=1200,fastThreshold=12)
        bf=cv2.BFMatcher(cv2.NORM_HAMMING)
        def load(f):return cv2.imdecode(np.frombuffer(z.read(f),np.uint8),cv2.IMREAD_GRAYSCALE)
        out=[]
        for i in range(min(a.pairs,len(refs)-1)):
            t0,f0=refs[i];t1,f1=refs[i+1]
            im0=load(f0);im1=load(f1)
            kp0,d0=orb.detectAndCompute(im0,None);kp1,d1=orb.detectAndCompute(im1,None)
            ms=[]
            if d0 is not None and d1 is not None:
                ms=[m for pair in bf.knnMatch(d0,d1,k=2) if len(pair)==2 for m,n in [pair] if m.distance<.73*n.distance]
            v=np.nan;inliers=0
            if len(ms)>=12:
                xy0=np.float32([kp0[m.queryIdx].pt for m in ms])
                xy1=np.float32([kp1[m.trainIdx].pt for m in ms])
                H,mask=cv2.findHomography(xy0,xy1,cv2.RANSAC,3.)
                if H is not None:
                    M=np.linalg.inv(K)@H@K
                    U,_,VT=np.linalg.svd(M)
                    R=U@np.diag([1.,1.,np.linalg.det(U@VT)])@VT
                    v=angle(Rotation.from_matrix(R));inliers=int(mask.sum())
            r0,r1=spline([t0,t1])
            truth=angle(r0.inv()*r1)
            si=imu[(imu[:,0]>=t0)&(imu[:,0]<=t1)]
            gyro=np.nan
            if len(si)>=2:
                inc=np.sum((si[:-1,4:7]+si[1:,4:7])*.5*np.diff(si[:,0])[:,None],axis=0)
                gyro=float(np.linalg.norm(inc)*180/np.pi)
            out.append(dict(t0=t0,t1=t1,truth_deg=truth,visual_deg=v,gyro_deg=gyro,matches=len(ms),inliers=inliers,visual_abs_error_deg=abs(v-truth),gyro_abs_error_deg=abs(gyro-truth)))
        if not out:raise RuntimeError("No image pairs evaluated")
        with open(a.output,"w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
        result={"pairs":len(out),"visual_valid":int(sum(np.isfinite(x["visual_deg"]) for x in out)),"visual_median_abs_error_deg":float(np.nanmedian([x["visual_abs_error_deg"] for x in out])),"gyro_median_abs_error_deg":float(np.nanmedian([x["gyro_abs_error_deg"] for x in out])),"qualification":"incremental rotation magnitude only; no absolute heading or vehicle-stability claim"}
        print(json.dumps(result,indent=2))
        with open("summary.json","w") as f:json.dump(result,f,indent=2)
if __name__=="__main__":main()
