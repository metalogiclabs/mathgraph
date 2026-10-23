"""Source-only EFRD discovery. Listing is NOT admission for a visual compass.

Research design: classify original-author dataset files BEFORE reading camera,
IMU, or reference poses. Only mocap-labelled sources are eligible for testing
whether independent heading ground truth exists. None is assumed to contain
two full turns merely because it is named a fast rotation sequence.
"""
import argparse
import json
from pathlib import Path
import re

SOURCE_URL="https://drive.google.com/drive/folders/1tOlC-aOPL0YmYcQKetyEFWWRYONG8kF0"
UPSTREAM_REPO="https://github.com/shicy17/MSA"
UPSTREAM_COMMIT="f8a89a0eb842e5f82b982493e636c200f8bf9dee"
VALID_SEQUENCES=["mahjong-1","mahjong-2","building","staircase","blocks","miscellany","bicycles","cabinets"]
MOCAP={"mahjong-1","mahjong-2"}

def sequence_for_path(path):
    name=str(path).lower().replace("\\","/")
    for seq in VALID_SEQUENCES:
        # Match a complete hyphen-delimited token with flexible underscore/space,
        # never mistake mahjong-10 for mahjong-1.
        token=re.escape(seq).replace(r"\-",r"[-_ ]?")
        if re.search(r"(?<![a-z0-9])"+token+r"(?![a-z0-9])",name):
            return seq
    return None

def evaluate_file_manifest(rows):
    if not isinstance(rows,list):
        raise ValueError("manifest must be list")
    seen=set()
    paths=[]
    for r in rows:
        if not isinstance(r,dict) or not isinstance(r.get("id"),str) or not isinstance(r.get("path"),str):
            raise ValueError("invalid Drive manifest record")
        if not r["id"] or not r["path"] or r["path"].startswith("/") or ".." in Path(r["path"]).parts:
            raise ValueError("unsafe Drive path or empty source")
        if r["id"] in seen:
            raise ValueError("duplicate source object id")
        seen.add(r["id"])
        seq=sequence_for_path(r["path"])
        suffix=Path(r["path"].lower()).suffix
        # No data input to an estimator. This is a metadata-only classification.
        paths.append({
            "id":r["id"],
            "path":r["path"],
            "sequence":seq,
            "container_suffix":suffix,
            "external_mocap_advertised_by_authors":seq in MOCAP,
            "independent_heading_verified":False,
            "two_consecutive_full_turns_verified":False,
            "raw_event_and_imu_timing_verified":False,
            "heading_correction_authorized":False,
        })
    by_seq={s:[p for p in paths if p["sequence"]==s] for s in VALID_SEQUENCES}
    return {
        "source":SOURCE_URL, "upstream_code":UPSTREAM_REPO,
        "upstream_revision_at_freeze":UPSTREAM_COMMIT,
        "scope":"original author-hosted Drive folder metadata; no source bytes read",
        "files_count":len(paths),
        "mocap_file_candidates":sum(len(by_seq[s]) for s in MOCAP),
        "declared_mocap_sequences":sorted(MOCAP),
        "declared_imu_derived_reference_sequences":sorted(set(VALID_SEQUENCES)-MOCAP),
        "files_by_sequence":{s:len(by_seq[s]) for s in VALID_SEQUENCES},
        "file_records":sorted(paths,key=lambda x:(x["path"],x["id"])),
        "scientific_state":"CANDIDATE_FOR_SOURCE_ADMISSION_ONLY",
        "qualified_multirevolution_dataset":False,
        "decision":"UNKNOWN: access original poses/IMU and event timestamps before promoting",
        "known_limitation":"IMU-derived /imu/gt cannot independently validate gyro drift",
    }

def enumerate_source():
    import gdown
    result=gdown.download_folder(url=SOURCE_URL,skip_download=True,quiet=True)
    if result is None:
        raise RuntimeError("EFRD public source listing unavailable")
    return [{"id":x.id,"path":x.path} for x in result]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    manifest=evaluate_file_manifest(enumerate_source())
    args.out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("EFRD_METADATA",json.dumps({
        k:manifest[k] for k in ("files_count","mocap_file_candidates","files_by_sequence",
            "scientific_state","qualified_multirevolution_dataset")},sort_keys=True))
    for row in manifest["file_records"]:
        print("EFRD_FILE",json.dumps({"path":row["path"],"id":row["id"],
              "mocap_advertised":row["external_mocap_advertised_by_authors"]}))
if __name__=="__main__":
    main()
