"""DARK-GS first physical camera-column/gyro source feasibility (no oracle).

Original 360.zip is independently source-pinned. Extract original 600
CompressedImage payloads and original 13,434 IMU packets. Build only a
retrospective DIAGNOSTIC first-turn reference using causal-past gyro samples.
No publisher pose/odometry messages are read here; no scene-match GT, no
clock/gyro physical error certificate and no navigational authority.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image
from rosbags.highlevel import AnyReader

from qualify_darkgs_360 import validate_zip,walk_original_bag,hashes


SOURCE_NAME="360.zip"
SOURCE_MD5="2b6eb3220c82ecab96dc8a4d918464ed"
SOURCE_SHA="f0c6bccfe0bd6bf20fb040280b212883c142fac609a70587da26efedd52649c2"
AUTHOR_FILE_ID=730164
URL=f"https://entrepot.recherche.data.gouv.fr/api/access/datafile/{AUTHOR_FILE_ID}"
IMU_TOPIC="/filtered_imu_xsens"
IMAGE_TOPIC="/camera/color/image_raw/compressed"
VERTICAL_BINS=16
ANGULAR_BINS=64
MIN_MAP_SOURCE_INTERVAL_S=0
MIN_COL_CONFLICT_HAMMING=2


def header_ns(header):
    t=header.stamp
    ns=int(t.sec)*1_000_000_000+int(t.nanosec)
    if not 0<=int(t.nanosec)<1_000_000_000:
        raise ValueError("invalid original source header nanoseconds")
    return ns


def original_color_column_descriptor(original_data):
    """Fixed conventional 16-bit grayscale center-column descriptor."""
    try:
        with Image.open(io.BytesIO(original_data)) as im:
            im.load()
            grey=np.asarray(im.convert("L"),dtype=np.uint8)
    except Exception as exc:
        raise ValueError("invalid source compressed image") from exc
    if grey.ndim!=2 or min(grey.shape)<16:
        raise ValueError("unsupported original sensor image geometry")
    h,w=grey.shape
    x=w//2
    raw=grey[:,x].astype(np.float64)
    value=0
    for y in range(VERTICAL_BINS):
        lower=(y*h)//VERTICAL_BINS
        upper=((y+1)*h)//VERTICAL_BINS
        if upper<=lower:raise ValueError("unsupported compressed image dimensions")
        avg=float(np.mean(raw[lower:upper]))
        if avg>=128.:value|=1<<y
    return value,(w,h,x)


def running_causal_gyro_integral(ns,angular_velocity_z):
    t=np.asarray(ns,dtype=np.int64)
    w=np.asarray(angular_velocity_z,dtype=np.float64)
    if t.ndim!=1 or t.shape!=w.shape or len(t)<10 or not np.isfinite(w).all():
        raise ValueError("source camera IMU samples missing or nonfinite")
    if np.any(np.diff(t)<=0):
        raise ValueError("source gyro header times not strictly monotone")
    step=(np.diff(t)*1e-9)*(w[:-1]+w[1:])/2
    return np.r_[0.,np.cumsum(step)]


def causal_phase_at(t,angular_t,omega_z,cumulative_phase):
    """Past-only IMU interpolation: extrapolate last known angular rate."""
    i=int(np.searchsorted(angular_t,t,side="right")-1)
    if i<0 or i>=len(angular_t):return None
    dt=(int(t)-int(angular_t[i]))*1e-9
    if dt<0 or dt>.020:return None
    return float(cumulative_phase[i]+float(omega_z[i])*dt)


def inspect_observations(times,omega_z,frames):
    imu_t=np.asarray(times,dtype=np.int64)
    omega=np.asarray(omega_z,dtype=float)
    if len(frames)<50:
        raise ValueError("insufficient actual camera frames")
    integrated=running_causal_gyro_integral(imu_t,omega)
    image_times=np.array([t for t,_,_ in frames],dtype=np.int64)
    if np.any(np.diff(image_times)<=0):
        raise ValueError("original camera timestamps nonmonotone")
    if image_times[-1]<imu_t[0] or image_times[0]>imu_t[-1]:
        return {"state":"UNKNOWN_DISJOINT_SOURCE_CLOCK_DOMAINS",
                "navigation_correction_authorized":False}
    first_valid=None
    map_members=Counter()
    map_reference={}
    quarantine=set()
    changes=[]
    count_after_full=0
    usable=0
    max_since_gyro=0
    ended=False
    reached=None
    shape=None
    invalid_shape=0
    for t,fingerprint,dim in frames:
        phase=causal_phase_at(t,imu_t,omega,integrated)
        if phase is None:continue
        if shape is None:shape=dim
        if dim!=shape:
            invalid_shape+=1
            continue
        if first_valid is None:
            first_valid=phase
            first_image_t=t
        shift=phase-first_valid
        if abs(shift)>=2*math.pi:
            if not ended:
                ended=True
                reached=int(t)
            count_after_full+=1
            continue
        if ended:continue
        phase_mod=(shift%(2*math.pi))
        cell=int(math.floor(phase_mod/(2*math.pi)*ANGULAR_BINS))%ANGULAR_BINS
        map_members[cell]+=1
        usable+=1
        if cell not in map_reference:
            map_reference[cell]=fingerprint
        elif (map_reference[cell]^fingerprint).bit_count()>MIN_COL_CONFLICT_HAMMING:
            quarantine.add(cell)
            if len(changes)<25:
                changes.append({"bin":cell,"time_ns":int(t),
                                "first_captured_descriptor":int(map_reference[cell]),
                                "contradicting_descriptor":int(fingerprint)})
    distinct=list(map_reference.values())
    pairwise=[]
    for i in range(len(distinct)):
        for j in range(i+1,len(distinct)):
            pairwise.append((distinct[i]^distinct[j]).bit_count())
    evidence={
      "state":("DIAGNOSTIC_SOURCE_GYRO_COMPLETE_TURN" if ended
               else "DIAGNOSTIC_PARTIAL_SOURCE_GYRO_TURN"),
      "original_frame_samples":len(frames),
      "original_imu_samples":len(imu_t),
      "original_frame_header_first_ns":int(image_times[0]),
      "original_frame_header_last_ns":int(image_times[-1]),
      "original_imu_header_first_ns":int(imu_t[0]),
      "original_imu_header_last_ns":int(imu_t[-1]),
      "zero_time_offset_assumed_only_for_offline_diagnostic":True,
      "timing_source_independent_warrant":"UNAVAILABLE",
      "gyro_bias_and_phase_error_independently_warranted":"UNAVAILABLE",
      "camera_to_gyro_yaw_axis_verified":"UNAVAILABLE",
      "source_imu_median_rate_hz":float(1e9/np.median(np.diff(imu_t))),
      "source_image_median_rate_hz":float(1e9/np.median(np.diff(image_times))),
      "gyroscope_integrated_signed_turns_full_source":float(integrated[-1]/(2*math.pi)),
      "first_image_integrated_phase_rad":float(first_valid) if first_valid is not None else None,
      "firstturn_source_model_complete_time_ns":reached,
      "firstturn_model_observation_count":usable,
      "post_firstturn_frames_not_used_for_map":count_after_full,
      "source_image_geometry":[*shape] if shape else None,
      "source_image_geometry_mismatch_frames":invalid_shape,
      "diagnostic_nominal_64bin_coverage":len(map_members),
      "diagnostic_nominal_bin_counts":{str(k):int(v) for k,v in sorted(map_members.items())},
      "diagnostic_unique_16bit_vertical_descriptors":len(set(distinct)),
      "descriptors_source_conflict_bins_gt2_hamming":sorted(quarantine),
      "descriptors_source_conflict_bin_count":len(quarantine),
      "descriptor_conflict_examples":changes,
      "nominal_unquarantined_firstturn_bins":len(map_members)-len(quarantine),
      "pairwise_stored_descriptor_Hamming_min":min(pairwise) if pairwise else None,
      "pairwise_stored_descriptor_Hamming_median":float(np.median(pairwise)) if pairwise else None,
      "physical_sensor_noise_bound_known":False,
      "independently_groundtruthed_firstturn_bins":False,
      "source_has_two_actual_continuous_revolutions":False,
      "camera_pixels_are_not_a_hardware_single_line_camera":True,
      "navigation_correction_authorized":False,
      "warranted_embedded_firstturn_reference":False,
    }
    return evidence


def run(out):
    import requests
    r={
        "source":"DARK-GS-Fusion 360.zip original publisher deposited ROS2 MCAP",
        "source_MD5":SOURCE_MD5,
        "source_SHA256":SOURCE_SHA,
        "source_dataverse_id":AUTHOR_FILE_ID,
        "source_previously_admitted":"https://github.com/metalogiclabs/mathgraph/actions/runs/40036024138",
        "source_visual_reference_authority":"DIAGNOSTIC_ONLY",
        "no_navigation_heading_correction_authorized":True,
        "no_reference_pose_or_odometry_payload_used":True,
        "status":"UNKNOWN",
    }
    try:
        original=Path(SOURCE_NAME)
        with requests.get(URL,stream=True,timeout=(30,120)) as response:
            response.raise_for_status()
            with original.open("wb") as f:
                for chunk in response.iter_content(chunk_size=4*1024*1024):
                    if chunk:f.write(chunk)
        md5,sha=hashes(original)
        if md5!=SOURCE_MD5 or sha!=SOURCE_SHA:
            raise ValueError("source archive hash mismatch")
        r["source_original_bytes"]=original.stat().st_size
        with zipfile.ZipFile(original) as archive:
            validate_zip(archive.infolist())
            folder=Path("darkgs_camera_real")
            folder.mkdir(exist_ok=True)
            archive.extractall(folder)
        rosroot,_=walk_original_bag(Path("darkgs_camera_real"))
        if rosroot is None:raise ValueError("original ROS2 metadata not uniquely present")
        with AnyReader([rosroot]) as reader:
            imu=[c for c in reader.connections if c.topic==IMU_TOPIC]
            frames=[c for c in reader.connections if c.topic==IMAGE_TOPIC]
            if len(imu)!=1 or len(frames)!=1:
                raise ValueError("original source lacks unique IMU/image topic")
            ts=[];omega=[]
            for c,receipt,raw in reader.messages(connections=imu):
                msg=reader.deserialize(raw,c.msgtype)
                t=header_ns(msg.header)
                ts.append(t)
                omega.append(float(msg.angular_velocity.z))
            frame_rows=[]
            for c,receipt,raw in reader.messages(connections=frames):
                msg=reader.deserialize(raw,c.msgtype)
                desc,dim=original_color_column_descriptor(bytes(msg.data))
                frame_rows.append((header_ns(msg.header),desc,dim))
        r["source_image_and_imu_values_processed"]=True
        r["result"]=inspect_observations(ts,omega,frame_rows)
        r["status"]=r["result"]["state"]
    except Exception as exc:
        r["status"]="UNKNOWN_ORIGINAL_SOURCE_DIAGNOSTIC_FAILED"
        r["failure"]=type(exc).__name__+": "+str(exc)[:950]
    out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("DARKGS_ONE_COLUMN_REAL_SOURCE",json.dumps(r,sort_keys=True))
    return r


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.out)


if __name__=="__main__":main()
