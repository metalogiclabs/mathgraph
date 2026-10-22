#!/usr/bin/env python3
"""Qualify RobotEvt UR5 pose text for repeated-revolution admission.

Input: original RobotEvt ground-truth file, each row timestamp + row-major
3x3 rotation + translation. Does not infer turns from filenames. Reports
signed unwrapped yaw and total 3D path length (not equivalent quantities).
"""
import argparse,json
import numpy as np
from scipy.spatial.transform import Rotation as R
p=argparse.ArgumentParser()
p.add_argument("groundtruth")
p.add_argument("--output",default="robotevt_qualification.json")
a=p.parse_args()
arr=np.loadtxt(a.groundtruth)
if arr.ndim!=2 or arr.shape[1]!=13 or len(arr)<10:
 raise ValueError("Expected N x 13 RobotEvt timestamp/R/t file")
ts=arr[:,0]; matrices=arr[:,1:10].reshape(-1,3,3)
if not np.all(np.diff(ts)>0):raise ValueError("timestamps not strictly increasing")
if np.max(np.abs(matrices@np.transpose(matrices,(0,2,1))-np.eye(3)))>.02:
 raise ValueError("invalid rotation matrix")
rot=R.from_matrix(matrices)
relative=(rot[:-1].inv()*rot[1:]).magnitude()
yaw=np.unwrap(rot.as_euler("zyx")[:,0])
signed=float((yaw[-1]-yaw[0])/(2*np.pi))
extent=float(np.ptp(yaw)/(2*np.pi))
arc=float(relative.sum()/(2*np.pi))
r=dict(samples=len(ts),duration_s=float(ts[-1]-ts[0]),yaw_net_turns=signed,
 yaw_excursion_turns=extent,total_3d_rotation_path_equivalent_turns=arc,
 meets_two_yaw_revolutions=bool(extent>=2),
 warning="Independent frame/IMU timestamp synchronization and continuous yaw still require verification; total 3D rotational arc is not equivalent to yaw turns.")
open(a.output,"w").write(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))
