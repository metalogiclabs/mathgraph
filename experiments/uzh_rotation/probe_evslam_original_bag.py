"""Source-admission probe for original EvSLAM drone_rot_norm camera/IMU bag.

Original Drive ID is taken from the dataset publisher's HTML download table.
Do not process event image values or use evaluation poses to select an angular
phase, visual candidate, time offset or navigation correction here.
"""
import argparse, hashlib, json, pathlib, struct, zipfile

PUBLIC_ORIGIN="https://github.com/NAIL-HNU/EvSLAM_Dataset"
UPSTREAM_REV="f116a9fe305f3ad8b1a379e1bb52becfc87654dc"
PUBLISHED_DRIVE_ID="1NNUZgkzpyR321AFeI1j5Uv2DKV8E_W3u"
EXPECTED_EVENT_TOPIC="/dvxplorer_left/events"
EXPECTED_IMU_TOPIC="/dvxplorer_left/imu"

def source_digest(file):
    sha=hashlib.sha256()
    md5=hashlib.md5()
    with pathlib.Path(file).open("rb") as stream:
        for part in iter(lambda: stream.read(16*1024*1024),b""):
            sha.update(part)
            md5.update(part)
    return sha.hexdigest(),md5.hexdigest()


def safe_archive_names(names):
    from pathlib import PurePosixPath
    for name in names:
        p=PurePosixPath(name)
        if name.startswith("/") or ".." in p.parts or "\\" in name or not name:
            raise ValueError("dangerous source archive member path")
    return names


def inspect_original(file):
    source=pathlib.Path(file)
    sha,md5=source_digest(source)
    with source.open("rb") as stream:
        magic=stream.read(32)
    result={
        "dataset": "EvSLAM real FPV drone, drone_rot_norm",
        "original_author_repository":PUBLIC_ORIGIN,
        "original_author_revision":UPSTREAM_REV,
        "original_source_drive_file_id":PUBLISHED_DRIVE_ID,
        "original_sha256":sha,
        "original_md5":md5,
        "original_bytes":source.stat().st_size,
        "magic_prefix_hex":magic[:16].hex(),
        "original_source_record_type":"UNDETERMINED",
        "original_sensor_connections":[],
        "left_event_topic_available":False,
        "left_imu_topic_available":False,
        "camera_event_values_opened":False,
        "camera_gyro_values_opened":False,
        "reference_gt_quaternions_opened":False,
        "post_turn_visual_relocalization":"NOT_TESTED",
        "heading_correction_authorized":False,
        "physical_line_camera":"NOT_TESTED",
        "source_status":"UNKNOWN",
    }
    if magic.startswith(b"#ROSBAG V2.0"):
        result["original_source_record_type"]="ROS1_BAG"
        from rosbags.highlevel import AnyReader
        with AnyReader([source]) as reader:
            con=[{"topic":c.topic,"msgtype":c.msgtype,
                  "indexed_message_count":int(c.msgcount)}
                 for c in reader.connections]
            result["original_sensor_connections"]=sorted(con,key=lambda x:x["topic"])
            result["left_event_topic_available"]=any(x["topic"]==EXPECTED_EVENT_TOPIC and "EventArray" in x["msgtype"] for x in con)
            result["left_imu_topic_available"]=any(x["topic"]==EXPECTED_IMU_TOPIC and "Imu" in x["msgtype"] for x in con)
            if reader.end_time is not None and reader.start_time is not None:
                result["bag_indexed_time_span_s"]=(reader.end_time-reader.start_time)*1e-9
            else:result["bag_indexed_time_span_s"]=None
        result["source_status"]=(
          "CANDIDATE_FOR_ORIGINAL_SENSOR_TIMESTAMP_REPLAY"
          if result["left_event_topic_available"] and result["left_imu_topic_available"]
          else "UNKNOWN_MISSING_DECLARED_SENSOR_TOPIC")
    elif zipfile.is_zipfile(source):
        result["original_source_record_type"]="ZIP_ARCHIVE"
        with zipfile.ZipFile(source) as archive:
            names=safe_archive_names(archive.namelist())
            result["original_archive_members"]=[
                {"filename":z.filename,"uncompressed_bytes":z.file_size,
                 "compressed_bytes":z.compress_size}
                for z in archive.infolist()[:100]]
            result["archive_member_count"]=len(names)
        result["source_status"]="UNKNOWN_ZIP_NEEDS_SEPARATE_SAFE_ORIGINAL_BAG_REPLAY"
    elif magic.startswith(b"\x1f\x8b"):
        result["original_source_record_type"]="GZIP"
        result["source_status"]="UNKNOWN_COMPRESSED_ORIGINAL_NOT_YET_PARSED"
    elif magic[:6]==b"SQLite":
        result["original_source_record_type"]="SQLITE"
        result["source_status"]="UNKNOWN_ROS2_DB3_NEEDS_SEPARATE_READER"
    else:
        result["source_status"]="UNKNOWN_ORIGINAL_CONTAINER_UNRECOGNIZED"
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    r=inspect_original(a.source)
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("EVSLAM_ORIGINAL_SENSOR_SOURCE_ADMISSION",json.dumps(r,sort_keys=True))


if __name__=="__main__":
    main()
