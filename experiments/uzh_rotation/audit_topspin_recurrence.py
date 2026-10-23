"""TOPSPIN genuine-event single-column temporal recurrence assay.

This is a stationary camera observing a rotating object, not the drone.
Training is the first half of each original 60s recording, validation is the
chronologically later half. No gyro, encoder, independent heading or verified
turn count is available. Validation is evaluation-only, never training.

A strong conventional matcher and the evidence gate share the identical
48-dimensional center-column event descriptor, timestamps and candidate set.
The gate only withholds if multiple lags remain plausible.
"""
import argparse
from collections import defaultdict
import csv
import io
import json
import math
from pathlib import Path
import tarfile

import numpy as np

from audit_topspin_column import (
    PUBLIC_MD5, hash_file, inspect_members, metadata_shape,
)

TIME_BIN_US=100000
VERTICAL_BINS=24
POLARITIES=2
MIN_LAG=5
MAX_LAG=150
MIN_PAIRS=40
TRAIN_SCORE_FLOOR=0.08
TRAIN_MIN_SEPARATION=0.04
PEAK_NEIGHBORHOOD=2
PUBLISHED_HUBBLE_SHA="de27852e28ba0ceff828aeda578fb56db8cb5166599324368522cd105b379526"


def load_center_rows(file,width,height):
    selected=width//2
    initial=None
    previous=None
    accum=defaultdict(lambda: np.zeros(VERTICAL_BINS*POLARITIES,dtype=np.int64))
    centers=0
    total=0
    for index,row in enumerate(csv.reader(io.TextIOWrapper(file,encoding="utf-8",newline=""))):
        if not row:continue
        if index==0 and any(c.isalpha() for c in ",".join(row)):continue
        if len(row)!=4:
            raise ValueError("unexpected original event CSV arity")
        try:
            timestamp,x,y,polarity=(int(v.strip()) for v in row)
        except ValueError as err:
            raise ValueError("invalid original event CSV integer") from err
        if (timestamp<0 or x<0 or x>=width or y<0 or y>=height or
                polarity not in (0,1)):
            raise ValueError("out-of-range original event")
        if previous is not None and timestamp<previous:
            raise ValueError("unordered original event timestamp")
        if initial is None:initial=timestamp
        previous=timestamp
        total+=1
        if x==selected:
            binid=(timestamp-initial)//TIME_BIN_US
            vertical=min(y*VERTICAL_BINS//height,VERTICAL_BINS-1)
            accum[binid][vertical*POLARITIES+polarity]+=1
            centers+=1
    if total==0:raise ValueError("empty original event stream")
    windows=(previous-initial)//TIME_BIN_US+1
    matrix=np.zeros((windows,VERTICAL_BINS*POLARITIES),dtype=np.int64)
    for binid,row in accum.items():
        matrix[binid]=row
    return matrix,{
        "selected_column":selected,
        "source_events":total,
        "center_column_events":centers,
        "time_windows":int(windows),
        "nonempty_windows":len(accum),
        "duration_s":(previous-initial)*1e-6,
    }


def standardized_features(counts,training_length):
    data=np.asarray(counts,dtype=np.float64)
    if (data.ndim!=2 or len(data)<300 or data.shape[1]!=VERTICAL_BINS*POLARITIES
            or np.any(data<0) or not np.all(np.isfinite(data))
            or not 0<training_length<len(data)):
        raise ValueError("invalid descriptor time series")
    transformed=np.sqrt(data)
    train=transformed[:training_length]
    mean=np.mean(train,axis=0)
    scale=np.maximum(np.std(train,axis=0),0.5)
    standardized=(transformed-mean)/scale
    norm=np.maximum(np.linalg.norm(standardized,axis=1),1e-12)
    return standardized/norm[:,None]


def lag_similarity(matrix,events,lag,start,end):
    """Continuous conventional whitened cosine, same information as gate."""
    if lag<=0 or end-start<=lag:
        return {"score":None,"eligible_pairs":0,"dot_products":0}
    left=np.arange(start,end-lag)
    right=left+lag
    allowed=(events[left]>0)&(events[right]>0)
    indices=left[allowed]
    n=len(indices)
    if n<MIN_PAIRS:
        return {"score":None,"eligible_pairs":n,"dot_products":0}
    score=float(np.mean(np.sum(matrix[indices]*matrix[indices+lag],axis=1)))
    return {"score":score,"eligible_pairs":n,"dot_products":n}


def scalar_rate_lag(counts,lag,start,end):
    """Equally informed conventional event-rate-only scalar autocorrelation."""
    x=np.log1p(np.asarray(counts.sum(axis=1),dtype=float))
    left=np.arange(start,end-lag)
    if len(left)==0:
        return {"score":None,"eligible_pairs":0}
    right=left+lag
    valid=(counts.sum(axis=1)[left]>0)&(counts.sum(axis=1)[right]>0)
    a=x[left[valid]]
    b=x[right[valid]]
    if len(a)<MIN_PAIRS:
        return {"score":None,"eligible_pairs":len(a)}
    a=a-a.mean();b=b-b.mean()
    norm=np.linalg.norm(a)*np.linalg.norm(b)
    if norm<1e-10:
        return {"score":None,"eligible_pairs":len(a)}
    return {"score":float(a@b/norm),"eligible_pairs":len(a)}


def training_selection(scores):
    finite=[(int(k),float(v["score"])) for k,v in scores.items()
            if v["score"] is not None]
    if not finite:
        return {"decision":"UNKNOWN_NO_TRAINING_RECURRENT_CUE",
                "best_lag_bins":None,"second_lag_bins":None,
                "best_score":None,"second_score":None,"margin":None}
    finite.sort(key=lambda x:(-x[1],x[0]))
    lag,top=finite[0]
    runners=[(k,v) for k,v in finite[1:]
             if abs(k-lag)>PEAK_NEIGHBORHOOD]
    runner=runners[0] if runners else None
    second=runner[1] if runner else None
    gap=top-second if second is not None else None
    admitted=(top>=TRAIN_SCORE_FLOOR and gap is not None
              and gap>=TRAIN_MIN_SEPARATION)
    return {"decision":("CANDIDATE_TRAINING_DISTINCT_TEMPORAL_RECURRENCE"
                        if admitted else "UNKNOWN_TEMPORAL_AMBIGUITY"),
            "best_lag_bins":lag,"second_lag_bins":runner[0] if runner else None,
            "best_score":top,"second_score":second,"margin":gap,
            "candidate_lags_evaluated":len(finite)}


def analyze_counts(counts):
    a=np.asarray(counts)
    train_size=len(a)//2
    feat=standardized_features(a,train_size)
    occupancy=a.sum(axis=1)
    # Source window size and lag grammar predeclared before observing source.
    allowed=range(MIN_LAG,min(MAX_LAG,train_size-MIN_PAIRS)+1)
    full={str(lag):lag_similarity(feat,occupancy,lag,0,train_size)
          for lag in allowed}
    scalar={str(lag):scalar_rate_lag(a,lag,0,train_size)
            for lag in allowed}
    full_choice=training_selection(full)
    scalar_choice=training_selection(scalar)
    # Later-half evaluation is never provided to training_selection.
    possible_lags=range(MIN_LAG,min(MAX_LAG,len(a)-train_size-MIN_PAIRS)+1)
    full_second={str(k):lag_similarity(feat,occupancy,k,train_size,len(a))
                 for k in possible_lags}
    scalar_second={str(k):scalar_rate_lag(a,k,train_size,len(a))
                   for k in possible_lags}
    def replay(choice,second):
        k=choice["best_lag_bins"]
        if k is None or str(k) not in second:
            return {"frozen_lag_score":None,"heldout_rank":None,
                    "heldout_eligible_pairs":0,"validation_not_used_for_selection":True}
        observed=second[str(k)]
        all_scores=[(int(z),v["score"]) for z,v in second.items()
                    if v["score"] is not None]
        better=sum(1 for q,s in all_scores if s>observed["score"]+1e-10)
        return {"frozen_lag_score":observed["score"],
                "heldout_rank":int(better+1),
                "heldout_compared_lags":len(all_scores),
                "heldout_eligible_pairs":observed["eligible_pairs"],
                "validation_not_used_for_selection":True}
    return {
        "settings":{"time_bin_us":TIME_BIN_US,"vertical_bins":VERTICAL_BINS,
                    "polarity_buckets":POLARITIES,
                    "lag_range_bins":[MIN_LAG,MAX_LAG],
                    "lag_neighbor_exclusion":PEAK_NEIGHBORHOOD,
                    "min_pairs":MIN_PAIRS,
                    "training_peak_floor":TRAIN_SCORE_FLOOR,
                    "training_min_peak_separation":TRAIN_MIN_SEPARATION,
                    "training_fraction":.5},
        "training_time_bins":train_size,
        "later_time_bins":len(a)-train_size,
        "conventional_full_column_descriptor_training":full_choice,
        "conventional_full_column_descriptor_later":replay(full_choice,full_second),
        "event_rate_only_baseline_training":scalar_choice,
        "event_rate_only_baseline_later":replay(scalar_choice,scalar_second),
        "evidence_gate_uses_same_full_column_scores":True,
        "evidence_gate_decision":full_choice["decision"],
        "absolute_heading_truth":"UNAVAILABLE",
        "object_period_encoder_truth":"UNAVAILABLE",
        "physical_revolution_count":"UNKNOWN",
        "navigation_correction_authorized":False,
        "relocalization_accuracy_measured":False,
        "validation_leakage":"NONE; selected lags and training gates use first chronological half only",
        "dot_products_training_full":int(sum(v["dot_products"] for v in full.values())),
    }


def audit(file,expected_sha=None):
    file=Path(file)
    if file.name not in PUBLIC_MD5:
        raise ValueError("source archive not in predeclared list")
    md5,sha=hash_file(file)
    if md5!=PUBLIC_MD5[file.name]:
        raise ValueError("source original public digest changed")
    if expected_sha is not None and sha!=expected_sha:
        raise ValueError("pinned source SHA256 mismatch")
    with tarfile.open(file,"r:gz") as tar:
        events,meta=inspect_members(tar)
        meta=json.load(tar.extractfile(meta))
        width,height=metadata_shape(meta)
        mat,read_summary=load_center_rows(tar.extractfile(events),width,height)
    result=analyze_counts(mat)
    return {
        "original_archive":file.name,
        "original_author_md5":md5,
        "original_sha256":sha,
        "physical_setup":"stationary camera observing spinning object",
        "camera_dimensions":[width,height],
        "raw_observation":read_summary,
        "experiment":result,
        "result_authority":"real periodic visual statistics only; no camera spin/gyro/encoder/heading truth",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--sha256")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.archive,args.sha256)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("TOPSPIN_TEMPORAL_TRANSFER",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
