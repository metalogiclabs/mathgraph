"""DARK-GS original-camera post-firstturn angular support and matcher audit.

Reuses the byte-frozen v2 column descriptor and publisher source provenance.
No image or IMU modifications and NO publisher pose/odometry accessed.

This is a retrospective real-source diagnostic, not external heading
validation, a temporal error-bound certificate or a flight algorithm.
A first-turn reference is compared to held-back camera frames only, and
heading correction remains forbidden. A conventional cosine tracker sees
the same reference, columns, and timing as the evidence gate.
"""
import argparse
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import requests
from rosbags.highlevel import AnyReader

from qualify_darkgs_360 import validate_zip, walk_original_bag, hashes
from darkgs_column_v2 import SOURCES, BINS, extract_column, firstturn
from darkgs_camera_gyro_firstturn import header_ns, causal_phase_at, running_causal_gyro_integral

V2_DESCRIPTOR_GIT_BLOB = "2a00bf9ec471a0d03edfe85d1622cb78b1c8efb7"
MIN_PAIR_COSINE_MARGIN = 0.02  # descriptive; no physical threshold certified
NO_REAL_HEADING_TRUTH = True


def expected_bin(phase, start):
    delta=float(phase)-float(start)
    return int(math.floor((abs(delta)%(2*math.pi))*BINS/(2*math.pi)))%BINS


def cosine(a,b):
    return float(np.asarray(a["vec"],dtype=float)@np.asarray(b["vec"],dtype=float))


def classify_revisit(gyro_t,gyro_z,images):
    t=np.asarray(gyro_t,dtype=np.int64)
    w=np.asarray(gyro_z,dtype=float)
    accumulated=running_causal_gyro_integral(t,w)
    if len(images)<50:
        raise ValueError("insufficient original camera images")
    camera_t=np.asarray([r[0] for r in images],dtype=np.int64)
    if np.any(np.diff(camera_t)<=0):
        raise ValueError("original image headers not monotone")
    gaps=np.diff(camera_t)*1e-9
    first_start=None
    first=[]
    after=[]
    completion_time=None
    excluded=0
    for timestamp,descriptor in images:
        phase=causal_phase_at(timestamp,t,w,accumulated)
        if phase is None:
            excluded+=1
            continue
        if first_start is None:
            first_start=phase
        relative=float(phase-first_start)
        index=expected_bin(phase,first_start)
        entry=(int(timestamp),relative,index,descriptor)
        if completion_time is None and abs(relative)<2*math.pi:
            first.append(entry)
        else:
            if completion_time is None:
                completion_time=int(timestamp)
            after.append(entry)
    references={}
    quarantined=set()
    usable=0
    conflicting=0
    for stamp,angle,index,d in first:
        if not d["usable"]:
            continue
        usable+=1
        if index not in references:
            references[index]=d
        elif (references[index]["bits"]^d["bits"]).bit_count()>2:
            quarantined.add(index)
            conflicting+=1
    frozen={k:v for k,v in references.items() if k not in quarantined}
    eligible=[]
    raw_late=[]
    for stamp,angle,index,d in after:
        if not d["usable"]:
            raw_late.append({"time_ns":stamp,"nominal_idx":index,"status":"LOW_CONTRAST"})
            continue
        if not frozen:
            raw_late.append({"time_ns":stamp,"nominal_idx":index,"status":"EMPTY_REFERENCE"})
            continue
        full=sorted(((cosine(d,ref),idx) for idx,ref in frozen.items()),reverse=True)
        hamming=sorted((((d["bits"]^ref["bits"]).bit_count(),idx)
                        for idx,ref in frozen.items()))
        # Query is never added to the map. Strong ordinary comparator sees
        # the identical observed column and frozen reference.
        best,best_idx=full[0]
        second=full[1][0] if len(full)>1 else None
        gap=best-second if second is not None else None
        within=sum(1 for score,_ in full if score>=best-MIN_PAIR_COSINE_MARGIN)
        minhd=hamming[0][0]
        ties=sum(1 for delta,_ in hamming if delta==minhd)
        nominal_index_known=index in frozen
        sample={
            "time_ns":stamp,"integrated_phase_after_firstturn_rad":angle,
            "nominal_gyro_phase_bin":index,
            "cosine_best_score":best,"cosine_best_reference_bin":best_idx,
            "cosine_second_score":second,"cosine_margin":gap,
            "cosine_near_best_candidate_count":within,
            "minimum_hamming":minhd,"minimum_hamming_ties":ties,
            "nominal_gyro_phase_has_reference":nominal_index_known,
            "cosine_top_agrees_with_nominal_gyro":best_idx==index if nominal_index_known else None,
            "normalized_similarity_at_nominal_gyro_bin":
                cosine(d,frozen[index]) if nominal_index_known else None,
            "similarity_is_not_independent_heading_truth":True,
        }
        eligible.append(sample)
        raw_late.append({"time_ns":stamp,"nominal_idx":index,"status":"MATCHED_OFFLINE"})
    def pct(values):
        if not values:return None
        return {"p50":float(np.percentile(values,50)),
                "p90":float(np.percentile(values,90)),
                "min":float(np.min(values)),
                "max":float(np.max(values))}
    laterangles=[r[1] for r in after]
    additional=(
        max(abs(a) for a in laterangles)/(2*math.pi)-1 if laterangles else 0
    )
    firstturn_result=firstturn(t,w,images)
    if firstturn_result["firstturn_camera_column_reads"]!=len(first):
        raise AssertionError("frozen source firstturn count and independent replay differ")
    if firstturn_result["later_camera_frames_not_learned"]!=len(after):
        raise AssertionError("frozen postfirstturn source partition differs")
    if firstturn_result["relative_accepted_bin_coverage"]!=len(frozen):
        raise AssertionError("frozen v2 map and replay accepted-coverage disagree")
    total_warranted_revisit=0
    # Without a second completed rotation, no later FULL revolution exists.
    # This is an angular-range condition, not a heading accuracy claim.
    status=(
        "NO_FIRST_COMPLETE_GYRO_TURN"
        if completion_time is None else
        "NO_SECOND_COMPLETE_GYRO_TURN"
        if additional<1 else
        "TWO_GYRO_TURNS_BUT_NO_INDEPENDENT_HEADING_OR_TIMING_WARRANT"
    )
    # Preserve all source anomalies, including an image timestamp far
    # outside IMU-domain and 501 s camera timestamp gap.
    return {
        "source_image_samples":len(images),
        "source_gyro_samples":len(t),
        "image_frames_outside_causal_gyro_source":excluded,
        "max_original_camera_header_gap_sec":float(gaps.max()),
        "gyro_image_clock_integrity_certified":False,
        "gyro_source_signed_turns":float(accumulated[-1]/(2*math.pi)),
        "first_valid_frame_gyro_phase_rad":float(first_start) if first_start is not None else None,
        "first_turn_completion_source_timestamp_ns":completion_time,
        "first_turn_frames_used_for_reference":len(first),
        "first_turn_lowcontrast_or_duplicate_observations":len(first)-usable,
        "source_conflicting_firstturn_duplicate_reads":conflicting,
        "frozen_reference_bins":len(frozen),
        "frozen_reference_duplicates_quarantined":len(quarantined),
        "postfirstturn_original_frames":len(after),
        "postfirstturn_distinct_nominal_gyro_bins":len({a[2] for a in after}),
        "postfirstturn_nominal_gyro_bins":sorted({a[2] for a in after}),
        "remaining_progress_to_second_turns":float(additional),
        "postfirstturn_phase_span_turns":(
            float((max(laterangles)-min(laterangles))/(2*math.pi))
            if laterangles else 0.0),
        "postfirstturn_contrast_qualified_comparisons":len(eligible),
        "postfirstturn_nominal_gyro_has_map_reference":sum(
            e["nominal_gyro_phase_has_reference"] for e in eligible),
        "offline_cosine_best_scores":pct([e["cosine_best_score"] for e in eligible]),
        "offline_cosine_best_second_margin":pct([e["cosine_margin"] for e in eligible
                                                if e["cosine_margin"] is not None]),
        "offline_hamming_best_distance":pct([e["minimum_hamming"] for e in eligible]),
        "offline_binary_best_match_ties":sum(e["minimum_hamming_ties"]>1 for e in eligible),
        "offline_cosine_ambiguous_margin_lt_0_02":sum(
            e["cosine_margin"] is not None and e["cosine_margin"]<MIN_PAIR_COSINE_MARGIN
            for e in eligible),
        "offline_cosine_gyro_agreement_count":sum(
            e["cosine_top_agrees_with_nominal_gyro"] is True for e in eligible),
        "raw_later_query_summary":raw_late[:25],
        "no_heldout_appearance_leaked_to_firstturn_reference":True,
        "v2_original_frozen_firstturn_summary":{
            "firstturn_frames":firstturn_result["firstturn_camera_column_reads"],
            "later_frames":firstturn_result["later_camera_frames_not_learned"],
            "reference_bins":firstturn_result["relative_accepted_bin_coverage"],
            "source_clock_status":firstturn_result["camera_imu_clock_status"],
        },
        "fully_separate_later_gyro_revolution_observed":additional>=1,
        "physical_true_camera_gyro_time_error_bound":"UNKNOWN",
        "physical_sensor_fingerprint_error_bound":"UNKNOWN",
        "observed_visual_matches_not_headings":True,
        "independent_heading_ground_truth_used":False,
        "navigation_correction_authorized":False,
        "independent_flight_readiness":"UNKNOWN",
        "state":status,
    }


def replay_archive(name):
    if name not in SOURCES:raise ValueError("unregistered source identity")
    fid,md5wanted,shawanted,nframes,ngyro=SOURCES[name]
    url="https://entrepot.recherche.data.gouv.fr/api/access/datafile/"+str(fid)
    original=Path(name)
    with requests.get(url,stream=True,timeout=(30,120)) as request:
        request.raise_for_status()
        with original.open("wb") as handle:
            for chunk in request.iter_content(4*1024*1024):
                if chunk:handle.write(chunk)
    md5,sha=hashes(original)
    if (md5,sha)!=(md5wanted,shawanted):
        raise ValueError("original publisher source checksum mismatch")
    with zipfile.ZipFile(original) as source:
        validate_zip(source.infolist())
        directory=Path("unpacked_"+name[:-4])
        directory.mkdir(exist_ok=True)
        source.extractall(directory)
    folder,_=walk_original_bag(directory)
    if folder is None:raise ValueError("unrecognized publisher ROS2 bag")
    with AnyReader([folder]) as reader:
        cc=[c for c in reader.connections if c.topic=="/camera/color/image_raw/compressed"]
        gg=[c for c in reader.connections if c.topic=="/filtered_imu_xsens"]
        if len(cc)!=1 or len(gg)!=1:
            raise ValueError("missing unique source image or gyro connection")
        gyro_t=[];gyro_z=[]
        for c,_,raw in reader.messages(connections=gg):
            msg=reader.deserialize(raw,c.msgtype)
            gyro_t.append(header_ns(msg.header))
            gyro_z.append(float(msg.angular_velocity.z))
        image_records=[]
        for c,_,raw in reader.messages(connections=cc):
            msg=reader.deserialize(raw,c.msgtype)
            image_records.append((header_ns(msg.header),extract_column(bytes(msg.data))))
    if len(gyro_t)!=ngyro or len(image_records)!=nframes:
        raise ValueError("original publisher sensor message count mismatch")
    return {
        "source_original_name":name,
        "source_original_dataverse_id":fid,
        "source_MD5":md5,
        "source_SHA256":sha,
        "source_frames":nframes,
        "source_gyro_packets":ngyro,
        "frozen_v2_descriptor_git_blob":V2_DESCRIPTOR_GIT_BLOB,
        "result":classify_revisit(gyro_t,gyro_z,image_records),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True,choices=sorted(SOURCES))
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    out={
        "source":args.source,
        "source_state":"UNKNOWN",
        "origins":"Original DARK-GS-Fusion Dataverse files, not generated data",
        "sensor_authority":"SOURCE-AUTHENTIC camera frames and gyro, no external GT",
        "visual_heading_or_navigation_correction_authorized":False,
    }
    try:
        out.update(replay_archive(args.source))
        out["source_state"]="COMPLETE_BOUNDED_REAL_SOURCE_OFFLINE_DIAGNOSTIC"
    except Exception as err:
        out["source_state"]="UNKNOWN_FAILED_TO_REPLAY_OR_VERIFY_REAL_SOURCE"
        out["error"]=type(err).__name__+": "+str(err)[:1000]
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    result=out.get("result",{})
    print("DARKGS_POSTFIRSTTURN_REVISIT",json.dumps({
        "source":args.source,"source_state":out["source_state"],
        "revisit_state":result.get("state"),
        "frozen_reference_bins":result.get("frozen_reference_bins"),
        "postfirstturn_original_frames":result.get("postfirstturn_original_frames"),
        "postfirstturn_nominal_gyro_bins":result.get("postfirstturn_nominal_gyro_bins"),
        "remaining_progress_to_second_turns":result.get("remaining_progress_to_second_turns"),
        "ambiguous_cosine_matches":result.get("offline_cosine_ambiguous_margin_lt_0_02"),
        "cosine_gyro_agreements":result.get("offline_cosine_gyro_agreement_count"),
        "clock_status":result.get("v2_original_frozen_firstturn_summary",{}).get("source_clock_status"),
        "navigation_correction_authorized":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
