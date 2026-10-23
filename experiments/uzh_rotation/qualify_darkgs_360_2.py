"""Independent original DARK-GS 360_2 source screening with 360 frozen method.

Only source and publisher reference pose are accessed, no camera/IMU content.
Original first-scene geometry, extraction and archive safety code must match
previously passed published Git blob before this prospective source is opened.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path

import requests
from qualify_darkgs_360 import (API,DATASET_ID,datafile_entry,hashes,
                                validate_zip,inspect_bag)

ORIGINAL_DEPOSIT_NAME="360_2.zip"
ORIGINAL_DEPOSIT_MD5="9a05e7d528241ad9a4f055170f3a710f"
FROZEN_360_METHOD_BLOB="4a8138ab153243aa656342e4cf704fb662fd7e46"


def qualify(args):
    report={
        "original_publisher":"DARK-GS-Fusion: doi:10.57745/EV12AZ",
        "source_name":ORIGINAL_DEPOSIT_NAME,
        "source_md5_expected":ORIGINAL_DEPOSIT_MD5,
        "frozen_original_source_classifier_git_blob":FROZEN_360_METHOD_BLOB,
        "selection_predeclared_before_new_source":"360_2.zip; no post-hoc axis selection",
        "gyro_values_opened":False,
        "image_values_opened":False,
        "source_mocap_externally_independent":False,
        "first_turn_visual_reference_built":False,
        "navigation_correction_authorized":False,
        "state":"UNKNOWN",
    }
    try:
        response=requests.get(API,params={"persistentId":DATASET_ID},timeout=40)
        response.raise_for_status()
        entry=datafile_entry(response.json(),name=ORIGINAL_DEPOSIT_NAME)
        if str(entry["expected_md5"]).lower()!=ORIGINAL_DEPOSIT_MD5:
            raise ValueError("original deposited 360_2 MD5 changed from public preregistration")
        report["publisher_record"]=entry
        url=f"https://entrepot.recherche.data.gouv.fr/api/access/datafile/{entry['datafile_id']}"
        p=Path(ORIGINAL_DEPOSIT_NAME)
        with requests.get(url,stream=True,timeout=(30,120)) as source:
            source.raise_for_status()
            with p.open("wb") as out:
                for chunk in source.iter_content(4*1024*1024):
                    if chunk:out.write(chunk)
        md5,sha=hashes(p)
        report["original_source_bytes"]=p.stat().st_size
        report["original_source_md5"]=md5
        report["original_source_sha256"]=sha
        if md5!=ORIGINAL_DEPOSIT_MD5:
            report["state"]="UNKNOWN_ORIGINAL_PUBLISHER_MD5_CHANGED"
        elif not zipfile.is_zipfile(p):
            report["state"]="UNKNOWN_UNEXPECTED_ORIGINAL_CONTAINER"
        else:
            with zipfile.ZipFile(p) as archive:
                rows=archive.infolist()
                report["archive_declared_uncompressed_bytes"]=validate_zip(rows)
                report["archive_original_member_count"]=len(rows)
                report["archive_original_member_list"]=[
                    {"path":r.filename,"uncompressed":r.file_size}
                    for r in rows[:100]]
                dest=Path("original_darkgs_360_2")
                dest.mkdir(exist_ok=True)
                archive.extractall(dest)
            inspect_bag(Path("original_darkgs_360_2"),report)
            report["source_mocap_externally_independent"]=False
    except Exception as exc:
        report["state"]="UNKNOWN_SOURCE_INSPECTION_OR_ACCESS_FAILURE"
        report["failure"]=type(exc).__name__+": "+str(exc)[:900]
    args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("DARKGS_360_2_FROZEN_SOURCE",json.dumps(report,sort_keys=True))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    qualify(args)


if __name__=="__main__":
    main()
