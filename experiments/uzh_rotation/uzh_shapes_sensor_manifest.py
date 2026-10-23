"""Original UZH shapes_rotation source sensor manifest (no estimator).

Source hash was first independently observed at Actions 40019636282.
Read metadata, IMU/calib contents and only a small prefix of groundtruth;
DO NOT read events or pictures or promote rejected multi-turn trajectory.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path,PurePosixPath

SOURCE_SHA256="56aade6bf53dcf73e8fe40905ccac8385cd7606bc9a85103bf2c9f9045117551"
URL="https://files.ifi.uzh.ch/rpg/datasets/davis/shapes_rotation.zip"

def digest(stream):
    h=hashlib.sha256()
    for chunk in iter(lambda:stream.read(16*1024*1024),b""):
        h.update(chunk)
    return h.hexdigest()

def safe_members(z):
    entries=z.infolist()
    for m in entries:
        p=PurePosixPath(m.filename)
        if p.is_absolute() or ".." in p.parts or "\\" in m.filename:
            raise ValueError("unsafe archive path")
    return entries

def first_rows(data,at_most=8):
    lines=data.decode("utf-8").splitlines()
    informative=[x for x in lines if x.strip() and not x.strip().startswith("#")]
    return informative[:at_most],len(informative),lines[:at_most]

def inspect(path):
    path=Path(path)
    with path.open("rb") as f:source_sha=digest(f)
    if source_sha!=SOURCE_SHA256:
        raise ValueError("original source sha256 mismatch")
    with zipfile.ZipFile(path) as z:
        members=safe_members(z)
        files=[m for m in members if not m.is_dir()]
        named={}
        for name in ("imu.txt","groundtruth.txt","calib.txt","events.txt"):
            options=[x for x in files if x.filename.lower().split("/")[-1]==name]
            if len(options)!=1:raise ValueError(f"expected unique {name}")
            m=options[0]
            named[name]={"path":m.filename,"size_bytes":m.file_size,
                         "compressed_bytes":m.compress_size}
            if name!="events.txt":
                raw=z.read(m)
                named[name]["sha256"]=hashlib.sha256(raw).hexdigest()
                preview,rows,heads=first_rows(raw)
                named[name]["rows_noncomment"]=rows
                named[name]["first_8_data_rows"]=preview
                named[name]["first_8_raw_lines"]=heads
        result={
            "source_url":URL,
            "source_archive_sha256":source_sha,
            "source_original_archive_bytes":path.stat().st_size,
            "source_frozen_from_run":"https://github.com/metalogiclabs/mathgraph/actions/runs/40019636282",
            "named_sources":named,
            "all_members":[{"name":m.filename,"size":m.file_size} for m in files
                           if m.file_size<20_000 or
                           m.filename.lower().split("/")[-1] in
                           ("imu.txt","groundtruth.txt","calib.txt","events.txt")],
            "source_trajectory_continuous_two_turn_qualifies":False,
            "source_data_reads":{"imu":True,"calib":True,"groundtruth_prefix":True,
                                 "events":False,"images":False},
            "navigation_correction_authorized":False,
            "status":"ORIGINAL_IMU_AND_MOCAP_SENSOR_SOURCE_CANDIDATE_ONLY",
        }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--zip",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    r=inspect(args.zip)
    args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("UZH_AUTHENTIC_SENSOR_SCHEMA",json.dumps(r,sort_keys=True))

if __name__=="__main__":
    main()
