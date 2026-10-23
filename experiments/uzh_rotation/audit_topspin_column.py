"""TOPSPIN original event-camera one-column feasibility preflight.

Source: Zenodo 10884694, static event camera observing a spinning object.
This is NOT a spinning camera, carries NO gyroscope or external heading truth,
and does not independently establish any number of complete object turns.
Nothing in this preflight may produce a visual navigation correction.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from collections import Counter

PUBLIC_MD5 = {
    "hubble-perpendicular-slow.tar.gz":"791716392f201526d814267155291147",
    "switch-perpendicular-slow.tar.gz":"498aa6f860bd226384a60c773ee8a8a9",
}
PUBLIC_RECORD = "https://zenodo.org/records/10884694"
WINDOW_US=50000


def hash_file(path):
    md5=hashlib.md5()
    sha256=hashlib.sha256()
    with open(path,"rb") as stream:
        for block in iter(lambda:stream.read(16*1024*1024),b""):
            md5.update(block)
            sha256.update(block)
    return md5.hexdigest(),sha256.hexdigest()


def inspect_members(tf):
    members=tf.getmembers()
    if not members:
        raise ValueError("empty source archive")
    for item in members:
        p=Path(item.name)
        if (p.is_absolute() or ".." in p.parts or
                (not item.isfile() and not item.isdir()) or
                item.name.startswith("./../")):
            raise ValueError("unsafe archive member")
    def matches(suffix):
        return [m for m in members if m.isfile() and m.name.lower().endswith(suffix)]
    events=matches("events.csv")
    metadata=matches("meta.json")
    if len(events)!=1 or len(metadata)!=1:
        raise ValueError("expected unique events.csv and meta.json")
    return events[0],metadata[0]


def metadata_shape(meta):
    if not isinstance(meta,dict):
        raise ValueError("invalid source camera meta")
    # The source author documents dimensions in meta.json; do not infer from
    # maximum observed event coordinate, which would inspect future events.
    if "width" in meta and "height" in meta:
        width,height=meta["width"],meta["height"]
    elif "image_width" in meta and "image_height" in meta:
        width,height=meta["image_width"],meta["image_height"]
    elif "sensor_width" in meta and "sensor_height" in meta:
        width,height=meta["sensor_width"],meta["sensor_height"]
    elif isinstance(meta.get("resolution"),list) and len(meta["resolution"])==2:
        width,height=meta["resolution"]
    else:
        raise ValueError("source camera dimensions unavailable; cannot choose center column")
    if (not isinstance(width,int) or not isinstance(height,int)
            or width<2 or height<2 or width>4096 or height>4096):
        raise ValueError("source camera dimensions invalid")
    return width,height


def stream_events(file,width,height,source_name,window_us=WINDOW_US):
    center=width//2
    total=0
    column=0
    first_t=None
    last_t=None
    out_of_order=0
    center_windows=Counter()
    accepted_polarity=[0,0]
    for index,row in enumerate(csv.reader(io.TextIOWrapper(file,encoding="utf-8",newline=""))):
        if not row:continue
        # Allow header exactly on line zero; any other malformed row fails.
        if index==0 and any(c.isalpha() for c in ",".join(row)):
            continue
        if len(row)!=4:
            raise ValueError(f"invalid event row arity at line {index+1}")
        try:
            time,x,y,polarity=(int(value.strip()) for value in row)
        except ValueError as error:
            raise ValueError(f"invalid source event integer at line {index+1}") from error
        if (time<0 or not 0<=x<width or not 0<=y<height or
                polarity not in (0,1)):
            raise ValueError("source event timestamp/coordinate/polarity out of range")
        if last_t is not None and time<last_t:
            out_of_order+=1
        if first_t is None:
            first_t=time
        last_t=time
        total+=1
        if x==center:
            column+=1
            accepted_polarity[polarity]+=1
            center_windows[(time-first_t)//window_us]+=1
    if total==0:
        raise ValueError("empty original event stream")
    return {
        "source_name":source_name,
        "total_real_camera_events":total,
        "fixed_column_x":center,
        "fixed_column_selected_before_event_read":True,
        "fixed_column_events":column,
        "fixed_column_fraction":column/total,
        "fixed_column_polarities":accepted_polarity,
        "source_duration_s":(last_t-first_t)*1e-6,
        "events_out_of_timestamp_order":out_of_order,
        "counted_original_timestamps_in_microseconds":True,
        "nonempty_fixed_column_50ms_windows":len(center_windows),
        "maximum_fixed_column_events_per_50ms_window":max(center_windows.values(),default=0),
        "prospective_signal_feasible":bool(
            column>=2000 and len(center_windows)>=100 and out_of_order==0),
        "verified_turn_count":None,
        "independent_gyro_available":False,
        "independent_heading_truth_available":False,
        "navigation_correction_authorized":False,
    }


def audit(archive):
    source=Path(archive)
    if source.name not in PUBLIC_MD5:
        raise ValueError("unregistered archive name")
    md5,sha=hash_file(source)
    if md5!=PUBLIC_MD5[source.name]:
        raise ValueError("published Zenodo original source MD5 mismatch")
    with tarfile.open(source,"r:gz") as tf:
        events,meta=inspect_members(tf)
        decoded=json.load(tf.extractfile(meta))
        width,height=metadata_shape(decoded)
        source_result=stream_events(tf.extractfile(events),width,height,source.name)
    return {
        "source_repository":PUBLIC_RECORD,
        "source_archived_name":source.name,
        "source_published_md5":md5,
        "source_sha256":sha,
        "source_archive_bytes":source.stat().st_size,
        "physical_setup":"STATIC EVENT CAMERA, SPINNING OBJECT",
        "not_a_rotating_camera":True,
        "camera_dimensions":{"width":width,"height":height},
        "source_metadata":decoded,
        "column_audit":source_result,
        "admission_state":("REAL_COLUMN_SIGNAL_CANDIDATE_ONLY"
                           if source_result["prospective_signal_feasible"]
                           else "UNKNOWN_INSUFFICIENT_CENTER_COLUMN_EVIDENCE"),
        "verification_scope":"real one-column event coverage, not multi-turn heading or drone validation",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    data=audit(args.archive)
    args.out.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("TOPSPIN_COLUMN_FEASIBILITY",json.dumps({k:data[k] for k in (
        "source_archived_name","source_sha256","source_archive_bytes",
        "camera_dimensions","admission_state","column_audit")},sort_keys=True))

if __name__=="__main__":
    main()
