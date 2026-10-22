#!/usr/bin/env python3
"""Audit official DARK-GS-Fusion yaw recordings, without model fitting."""
import argparse, hashlib, json, pathlib, requests, zipfile, time, math
import numpy as np
from scipy.spatial.transform import Rotation as Rotation
p=argparse.ArgumentParser()
p.add_argument("--sequence",default="360")
p.add_argument("--output",default="darkgs_audit.json")
p.add_argument("--max-download-mb",type=int,default=260)
a=p.parse_args()
base="https://entrepot.recherche.data.gouv.fr"
s=requests.Session()
r=s.get(base+"/api/datasets/:persistentId/",params={"persistentId":"doi:10.57745/EV12AZ"},timeout=60);r.raise_for_status()
files=r.json()["data"]["latestVersion"]["files"]
items=[x["dataFile"] for x in files if x["dataFile"]["filename"]==a.sequence+".zip"]
if len(items)!=1:raise RuntimeError("Archive not uniquely listed: "+str([x["dataFile"]["filename"] for x in files]))
entry=items[0];length=entry.get("filesize",0)
if length>a.max_download_mb*1024*1024:raise RuntimeError("Archive over fixed download budget")
dest=pathlib.Path(a.sequence+".zip")
with s.get(base+"/api/access/datafile/"+str(entry["id"]),stream=True,timeout=(30,120)) as r:
 r.raise_for_status()
 with dest.open("wb") as f:
  for chunk in r.iter_content(1024*1024):
   if chunk:f.write(chunk)
md5=hashlib.md5(dest.read_bytes()).hexdigest()
if entry.get("md5") and md5!=entry["md5"]:raise RuntimeError("Official archive checksum mismatch")
with zipfile.ZipFile(dest) as z:
 entries=z.namelist()
 dbs=[x for x in entries if x.endswith(".db3")]
 if not dbs:raise RuntimeError("No sqlite ROS2 bag found: "+str(entries[:25]))
 work=pathlib.Path("rosbag_"+a.sequence);work.mkdir(exist_ok=True)
 for path in dbs:
  dst=work/pathlib.Path(path).name
  with z.open(path) as src,dst.open("wb") as out:
   import shutil;shutil.copyfileobj(src,out)
import sqlite3
topics=[];angles=[];timestamps=[];imu_count=0;camera_count=0
for db in work.glob("*.db3"):
 con=sqlite3.connect(str(db))
 rows=con.execute("SELECT id,name,type FROM topics").fetchall()
 topics.extend([{"name":x[1],"type":x[2]} for x in rows])
 poses=[x for x in rows if x[1]=="/Darknav/pose"]
 # rosbags uses standard ros2 geometry messages where supported.
 from rosbags.typesys import Stores,get_typestore
 store=get_typestore(Stores.ROS2_HUMBLE)
 for tid,name,typ in poses:
  for stamp,raw in con.execute("SELECT timestamp,data FROM messages WHERE topic_id=? ORDER BY timestamp",(tid,)):
   try:msg=store.deserialize_cdr(raw,typ)
   except Exception as exc:
    print("POSE_DESERIALIZATION_ERROR",str(exc));break
   pose=getattr(msg,"pose",msg)
   pose=getattr(pose,"pose",pose)
   q=getattr(pose,"orientation",None)
   if q is not None:
    angles.append(Rotation.from_quat([q.x,q.y,q.z,q.w]).as_euler("zyx")[0])
    timestamps.append(stamp*1e-9)
 imu_count+=sum(x[0] for x in con.execute("SELECT COUNT(*) FROM messages JOIN topics ON messages.topic_id=topics.id WHERE topics.name='/filtered_imu_xsens'"))
 camera_count+=sum(x[0] for x in con.execute("SELECT COUNT(*) FROM messages JOIN topics ON messages.topic_id=topics.id WHERE topics.name='/camera/color/image_raw/compressed'"))
 con.close()
if angles:
 unwrapped=np.unwrap(angles)
 turn_total=float((unwrapped[-1]-unwrapped[0])/(2*math.pi))
 turn_excursion=float((unwrapped.max()-unwrapped.min())/(2*math.pi))
else: turn_total=None;turn_excursion=None
out=dict(sequence=a.sequence,doi="10.57745/EV12AZ",source_file_id=entry["id"],bytes=dest.stat().st_size,checksum_md5=md5,expected_md5=entry.get("md5"),archives=entries[:40],topics=topics,pose_samples=len(angles),imu_samples=imu_count,camera_samples=camera_count,pose_duration_s=(timestamps[-1]-timestamps[0] if len(timestamps)>1 else None),net_turns=turn_total,yaw_excursion_turns=turn_excursion,multiple_full_revolutions_confirmed=(turn_excursion>=2 if turn_excursion is not None else False),status="QUALIFIED" if turn_excursion is not None and turn_excursion>=2 and imu_count>0 and camera_count>0 else "NOT_YET_QUALIFIED")
pathlib.Path(a.output).write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
