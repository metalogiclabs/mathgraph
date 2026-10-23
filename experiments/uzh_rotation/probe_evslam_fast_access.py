"""Exactly one publisher-source acquisition attempt for EvSLAM fast raw drone bag.

The independent authentic reference is already qualified. Acquisition may
fail due to Google Drive quota; preserve that as a named obstruction, not
a green real camera/gyro claim. Do not retry beyond one attempt in this run.
"""
import argparse
import json
from pathlib import Path
import subprocess
from probe_evslam_original_bag import inspect_original

FAST_FILE_ID="1t4viDrRV40_uOS3Tfh9-jMbGKgHorTI1"
FAST_METADATA_BYTES=6551527649
SOURCE="NAIL-HNU/EvSLAM_Dataset@f116a9fe305f3ad8b1a379e1bb52becfc87654dc"


def report_status(returncode,stderr,exists,size):
    text=str(stderr)
    if returncode and ("Too many users have viewed or downloaded" in text or
                       "download quota is exceeded" in text):
        return "UNKNOWN_PUBLISHER_DOWNLOAD_QUOTA"
    if returncode:
        return "UNKNOWN_ORIGINAL_SOURCE_TRANSFER_FAILED"
    if not exists:
        return "UNKNOWN_NO_SOURCE_BYTES"
    if size!=FAST_METADATA_BYTES:
        return "UNKNOWN_ORIGINAL_SIZE_MISMATCH"
    return "SOURCE_ACQUIRED_FOR_RAW_BAG_PROBE"


def run(out):
    file=Path("evslam_drone_rot_fast.bag")
    result={
        "published_drive_id":FAST_FILE_ID,
        "publisher":SOURCE,
        "publisher_metadata_size_bytes":FAST_METADATA_BYTES,
        "other_original_source_norm": "UNKNOWN_DOWNLOAD_QUOTA",
        "attempts":1,
        "authenticated_original_sensor_contents":False,
        "camera_event_values_read":False,
        "imu_values_read":False,
        "source_state":"UNKNOWN",
        "heading_correction_authorized":False,
    }
    cmd=["gdown",FAST_FILE_ID,"-O",str(file)]
    try:
        completed=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,check=False)
        size=file.stat().st_size if file.exists() else None
        state=report_status(completed.returncode,completed.stderr,file.exists(),size)
        result["source_state"]=state
        result["source_bytes_present"]=size
        result["download_returncode"]=completed.returncode
        result["download_error_excerpt"]=completed.stderr[-1100:] if completed.returncode else None
        if state=="SOURCE_ACQUIRED_FOR_RAW_BAG_PROBE":
            inspected=inspect_original(file)
            inspected["dataset"]="EvSLAM real FPV drone, drone_rot_fast"
            inspected["original_source_drive_file_id"]=FAST_FILE_ID
            inspected["source_metadata_file_size_bytes"]=FAST_METADATA_BYTES
            result["original_bag_probe"]=inspected
            result["authenticated_original_sensor_contents"]=bool(
                inspected["source_status"].startswith("CANDIDATE_"))
    except Exception as e:
        result["source_state"]="UNKNOWN_SOURCE_PROBE_ERROR"
        result["probe_error"]=type(e).__name__+": "+str(e)[:650]
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("EVSLAM_FAST_SOURCE_ACQUISITION",json.dumps(result,sort_keys=True))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    run(args.out)
if __name__=="__main__":
    main()
