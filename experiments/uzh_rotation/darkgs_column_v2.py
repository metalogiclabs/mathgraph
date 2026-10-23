"""Real DARK-GS UAV one-pixel-column discriminability and clock audit.

Uses ONLY original compressed images and gyro, no pose/odometry oracle. After
v1's exposed constant threshold descriptor, fix an ordinary contrast-relative
descriptor and a full-column cosine comparator BEFORE opening 360_2 images.
A nominal gyro angle, a clock header, or visually distinct fingerprints
do not authenticate an actual heading correction.
"""
import argparse,io,json,math,zipfile
from pathlib import Path
import requests
import numpy as np
from PIL import Image
from rosbags.highlevel import AnyReader
from qualify_darkgs_360 import hashes,validate_zip,walk_original_bag
from darkgs_camera_gyro_firstturn import header_ns,causal_phase_at,running_causal_gyro_integral

SOURCES={
 "360.zip":(730164,"2b6eb3220c82ecab96dc8a4d918464ed","f0c6bccfe0bd6bf20fb040280b212883c142fac609a70587da26efedd52649c2",600,13434),
 "360_2.zip":(730162,"9a05e7d528241ad9a4f055170f3a710f","36da03f876b34c94e34b721e61bf114cfa04ec19857dba1db3899c41c599dfa1",761,17413),
}
VERT=16
CONTRAST_FLOOR=12.0
BINS=64

def extract_column(blob):
    with Image.open(io.BytesIO(blob)) as im:
        im.load()
        a=np.asarray(im.convert("L"),dtype=np.float64)
    if a.ndim!=2 or min(a.shape)<VERT:raise ValueError("unsupported original compressed image")
    h,w=a.shape
    raw=a[:,w//2]
    means=[float(np.mean(raw[i*h//VERT:(i+1)*h//VERT])) for i in range(VERT)]
    middle=float(np.median(means))
    contrast=float(np.percentile(means,90)-np.percentile(means,10))
    relative=sum((1<<i) for i,v in enumerate(means) if v>=middle+3)
    absolute=sum((1<<i) for i,v in enumerate(means) if v>=128)
    centered=raw-raw.mean()
    norm=float(np.linalg.norm(centered))
    vector=centered/norm if norm>1e-9 else np.zeros(h,dtype=float)
    return {"bits":relative,"absolute":absolute,"contrast":contrast,
            "usable":contrast>=CONTRAST_FLOOR,"vec":vector,
            "geometry":(w,h,w//2)}

def pairs(source):
    records=list(source.values())
    hd=[];cs=[]
    for i in range(len(records)):
        for j in range(i+1,len(records)):
            a=records[i];b=records[j]
            hd.append((a["bits"]^b["bits"]).bit_count())
            cs.append(float(a["vec"]@b["vec"]))
    unique=0
    for a in records:
        if all((a["bits"]^b["bits"]).bit_count()>4
               for b in records if b is not a):unique+=1
    return {
        "reference_bins":len(records),
        "reference_pairs":len(hd),
        "duplicate_binary_pairs":sum(n==0 for n in hd),
        "pairwise_binary_witness_if_observation_error_le_2bits":sum(n>4 for n in hd),
        "all_alternative_heading_separated_if_error_le_2bits":unique,
        "ordinary_full_column_cosine_near_duplicates_gt_0_98":sum(c>.98 for c in cs),
        "ordinary_full_column_cosine_max":max(cs) if cs else None,
        "two_bit_error_limit_physically_authenticated":False,
    }

def firstturn(gyro_t,gyro_z,images):
    stamps=np.asarray(gyro_t,dtype=np.int64)
    w=np.asarray(gyro_z,dtype=float)
    angle=running_causal_gyro_integral(stamps,w)
    image_t=np.asarray([r[0] for r in images],dtype=np.int64)
    if len(images)<50 or np.any(np.diff(image_t)<=0):
        raise ValueError("original camera chronological order invalid")
    gap=np.diff(image_t)*1e-9
    out_of_domain=int(np.sum((image_t<stamps[0])|(image_t>stamps[-1])))
    clock_anomaly=out_of_domain>0 or float(gap.max())>1.
    current={}
    mapall={}
    quarantined=set()
    source_start=None
    complete=None
    used=0
    post=0
    rejected_contrast=0
    for t,desc in images:
        phase=causal_phase_at(t,stamps,w,angle)
        if phase is None:continue
        if source_start is None:source_start=phase
        d=phase-source_start
        if complete is not None or abs(d)>=2*math.pi:
            if complete is None:complete=int(t)
            post+=1
            continue
        idx=int(math.floor((d%(2*math.pi))*BINS/(2*math.pi)))%BINS
        used+=1
        if idx not in mapall:mapall[idx]=desc
        if not desc["usable"]:
            rejected_contrast+=1
            continue
        if idx not in current:current[idx]=desc
        elif (current[idx]["bits"]^desc["bits"]).bit_count()>2:
            quarantined.add(idx)
    score=pairs({k:v for k,v in current.items() if k not in quarantined})
    return {
        "source_image_count":len(images),"source_gyro_count":len(stamps),
        "camera_imu_clock_status":"UNKNOWN_SOURCE_TIME_GAP_OR_DOMAIN"
           if clock_anomaly else "HEADER_OVERLAP_ONLY_NOT_CERTIFIED",
        "source_frames_outside_gyro_domain":out_of_domain,
        "max_source_camera_timestamp_gap_s":float(gap.max()),
        "gyro_integrated_total_signed_turns":float(angle[-1]/(2*math.pi)),
        "source_model_first_turn_complete":complete is not None,
        "source_model_first_turn_ending_ns":complete,
        "firstturn_camera_column_reads":used,
        "later_camera_frames_not_learned":post,
        "nominal_phase_map_coverage":len(mapall),
        "original_absolute_threshold_unique":len({v["absolute"] for v in mapall.values()}),
        "relative_contrast_threshold":CONTRAST_FLOOR,
        "relative_insufficient_contrast_frames":rejected_contrast,
        "relative_candidate_bin_coverage":len(current),
        "relative_quarantined_nominal_cells":sorted(quarantined),
        "relative_accepted_bin_coverage":len(current)-len(quarantined),
        "relative_unique_16bit_signatures":len({v["bits"] for k,v in current.items() if k not in quarantined}),
        "reference_pair_analysis":score,
        "source_geometry":images[0][1]["geometry"],
        "source_true_camera_gyro_offset_bound":"UNKNOWN",
        "sensor_phase_error_bound":"UNKNOWN",
        "reference_pose_never_used_in_map":True,
        "actual_later_revolution_recognition":"NOT_TESTED",
        "navigation_correction_authorized":False,
    }

def audit(name):
    identity=SOURCES[name]
    url=f"https://entrepot.recherche.data.gouv.fr/api/access/datafile/{identity[0]}"
    original=Path(name)
    with requests.get(url,stream=True,timeout=(30,120)) as response:
        response.raise_for_status()
        with original.open("wb") as f:
            for chunk in response.iter_content(4*1024*1024):
                if chunk:f.write(chunk)
    md5,sha=hashes(original)
    if md5!=identity[1] or sha!=identity[2]:
        raise ValueError("untrusted original publisher source identity")
    with zipfile.ZipFile(original) as archive:
        validate_zip(archive.infolist())
        dest=Path("extracted_"+name[:-4])
        dest.mkdir(exist_ok=True)
        archive.extractall(dest)
    folder,_=walk_original_bag(dest)
    if folder is None:raise ValueError("missing unique original ROS2 metadata")
    with AnyReader([folder]) as reader:
        imus=[c for c in reader.connections if c.topic=="/filtered_imu_xsens"]
        cams=[c for c in reader.connections if c.topic=="/camera/color/image_raw/compressed"]
        if len(imus)!=1 or len(cams)!=1:raise ValueError("missing unique original camera or IMU")
        t=[];w=[]
        for c,_,raw in reader.messages(connections=imus):
            m=reader.deserialize(raw,c.msgtype)
            t.append(header_ns(m.header));w.append(float(m.angular_velocity.z))
        frames=[]
        for c,_,raw in reader.messages(connections=cams):
            m=reader.deserialize(raw,c.msgtype)
            frames.append((header_ns(m.header),extract_column(bytes(m.data))))
    if len(t)!=identity[4] or len(frames)!=identity[3]:
        raise ValueError("original source message counts differ from previously pinned index")
    if len({r[1]["geometry"] for r in frames})!=1:
        raise ValueError("original camera image geometry changed within sequence")
    return firstturn(t,w,frames)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True,choices=list(SOURCES))
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    d={"name":args.source,"source_identity":SOURCES[args.source],
       "source_context":"Original publisher camera+gyro, no pose/odometry read",
       "qualifier":"OFFLINE_ONLY_UNCERTIFIED_CLOCK_AND_GYRO",
       "navigation_correction_authorized":False,"status":"UNKNOWN"}
    try:
        d["result"]=audit(args.source)
        d["status"]="SOURCE_DIAGNOSTIC_NO_HEADING_AUTHORITY"
    except Exception as exc:
        d["status"]="UNKNOWN_SOURCE_SENSOR_AUDIT_FAILURE"
        d["failure"]=type(exc).__name__+": "+str(exc)[:800]
    args.out.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
    print("DARKGS_REAL_COLUMN_V2",json.dumps(d,sort_keys=True))
if __name__=="__main__":main()
