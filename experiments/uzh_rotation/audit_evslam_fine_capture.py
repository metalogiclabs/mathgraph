"""Source-GT comparison: old and fine C99 map-admission quantization.

The original EvSLAM publisher camera/IMU nominal offset is used only as
a hypothetical +/- timing sensitivity around each original GT pose sample.
It is NOT an authenticated timing-error bound or actual event-camera sample.
C99 map capture is called with placeholder column bytes; no raw camera
sensor exists in this experiment and no correction may be authorized.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path
import subprocess
import tempfile

from audit_finite_partial_map import Map
from evslam_source_phase_clock import (
    admit_calibrations,body_y_phase,interval_membership,read_original_gt,
    SOURCE_BLOBS,UPSTREAM_COMMIT,TWO_PI,BINS,
)

HERE=Path(__file__).parent
COARSE_TICKS=1024
FINE_TICKS=65536


def native_library():
    directory=tempfile.TemporaryDirectory(prefix="evslam-real-source-c99-")
    out=Path(directory.name)/"libcapture.so"
    subprocess.run(["gcc","-std=c99","-Wall","-Wextra","-Werror","-O2",
                    "-fPIC","-shared",
                    str(HERE/"firstturn_fine_capture.c"),
                    str(HERE/"firstturn_interval_capture.c"),
                    str(HERE/"finite_partial_map.c"),
                    str(HERE/"finite_jitter_embedded.c"),"-o",str(out)],
                   check=True,capture_output=True,text=True)
    lib=ctypes.CDLL(str(out))
    lib.mg_map_init.argtypes=[ctypes.POINTER(Map)]
    for name in ("mg_firstturn_capture_fine_interval","mg_firstturn_capture_interval"):
        fn=getattr(lib,name)
        fn.argtypes=[ctypes.POINTER(Map),ctypes.c_uint16,ctypes.c_uint16,ctypes.c_uint16]
        fn.restype=ctypes.c_int
    return lib,directory


def admitted(native,method,phase,radius):
    map=Map()
    native.mg_map_init(ctypes.byref(map))
    result=getattr(native,method)(ctypes.byref(map),phase,radius,0x1234)
    if result not in (0,2):
        raise AssertionError("unexpected source-only map capture status "+str(result))
    if result==0 and map.count!=1:
        raise AssertionError("admitted source-only map not recorded")
    if result==2 and map.count:
        raise AssertionError("uncertain map capture mutated frozen-source representation")
    return result==0


def compare_one(gt,halfwidth,native):
    t,phase,_,error=body_y_phase(gt)
    r={
        "sample_source":"original published reference poses at 10Hz only",
        "hypothetical_timing_halfwidth_ms":halfwidth*1000,
        "source_pose_count":len(t),
        "independent_relative_rotation_agreement_rad":error,
        "reference_map_angular_bins":64,
        "C99_original_integer_ticks_per_turn":COARSE_TICKS,
        "C99_fine_integer_ticks_per_turn":FINE_TICKS,
        "samples_first_turn_evaluable":0,
        "continuous_interval_ambiguous":0,
        "coarse_refused":0,
        "fine_refused":0,
        "coarse_accepted":0,
        "fine_accepted":0,
        "coarse_false_admissions_inside_model":0,
        "fine_false_admissions_inside_model":0,
        "nominal_10hz_pose_coverage_bins":set(),
        "coarse_accepted_coverage_bins":set(),
        "fine_accepted_coverage_bins":set(),
        "cases_where_fine_admits_and_coarse_refuses":[],
        "raw_camera_column_observed":False,
        "physical_sensor_time_uncertainty_authenticated":False,
        "navigation_correction_authorized":False,
    }
    for i,tm in enumerate(t):
        nominal=phase[i]
        if not 0<=nominal<TWO_PI:
            continue
        bounds=interval_membership(t,phase,float(tm),halfwidth)
        if bounds is None:
            continue
        lower,upper=bounds
        if lower<0 or upper>=TWO_PI:
            continue
        nbin=int(math.floor(nominal/TWO_PI*BINS))
        lbin=int(math.floor(lower/TWO_PI*BINS))
        ubin=int(math.floor(upper/TWO_PI*BINS))
        radius_angle=max(abs(nominal-lower),abs(upper-nominal))
        # Floor point phase into a fixed-point tick, add one extra tick to
        # preserve the continuum fractional-quantization remainder.
        coarsephase=int(math.floor(nominal/TWO_PI*COARSE_TICKS))
        finephase=int(math.floor(nominal/TWO_PI*FINE_TICKS))
        coarse_r=int(math.ceil(radius_angle/TWO_PI*COARSE_TICKS))+1
        fine_r=int(math.ceil(radius_angle/TWO_PI*FINE_TICKS))+1
        coarse=admitted(native,"mg_firstturn_capture_interval",coarsephase,coarse_r)
        fine=admitted(native,"mg_firstturn_capture_fine_interval",finephase,fine_r)
        r["samples_first_turn_evaluable"]+=1
        r["nominal_10hz_pose_coverage_bins"].add(nbin)
        ambiguous=lbin!=ubin
        if ambiguous:
            r["continuous_interval_ambiguous"]+=1
        for key,ok in (("coarse",coarse),("fine",fine)):
            if ok:
                r[key+"_accepted"]+=1
                r[key+"_accepted_coverage_bins"].add(nbin)
                if ambiguous or nbin!=lbin or nbin!=ubin:
                    r[key+"_false_admissions_inside_model"]+=1
            else:r[key+"_refused"]+=1
        if fine and not coarse and len(r["cases_where_fine_admits_and_coarse_refuses"])<12:
            r["cases_where_fine_admits_and_coarse_refuses"].append({
                "timestamp_s":float(tm),
                "reference_angular_bin":nbin,
                "coarse_error_ticks":coarse_r,
                "fine_error_ticks":fine_r,
                "continuous_interval_ambiguous":ambiguous})
    if r["coarse_false_admissions_inside_model"] or r["fine_false_admissions_inside_model"]:
        raise AssertionError("guard accepted a GT-model interval that crosses bins")
    if r["fine_accepted"]<r["coarse_accepted"]:
        raise AssertionError("high-resolution guard should not reduce admitted source samples")
    for key in ("nominal_10hz_pose_coverage_bins","coarse_accepted_coverage_bins",
                "fine_accepted_coverage_bins"):
        r[key+"_count"]=len(r.pop(key))
    r["recovered_admission_samples"]=r["fine_accepted"]-r["coarse_accepted"]
    return r


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--calib",type=Path,required=True)
    p.add_argument("--imu-calib",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    calibration=admit_calibrations(args.calib,args.imu_calib)
    lib,temp=native_library()
    try:
        out={
            "source_revision":UPSTREAM_COMMIT,
            "source_blobs":SOURCE_BLOBS,
            "calibration_source_hashes":[calibration["camera_calibration_original_sha256"],
                                         calibration["imu_calibration_original_sha256"]],
            "nominal_offset_is_not_certified_uncertainty":True,
            "GT_samples_not_camera_events":True,
            "original_map_and_coarse_source_intact":True,
            "new_c99_map_struct_is_unchanged":True,
            "regime":"hypothetical +/- nominal publisher shift at 10Hz GT poses",
            "results":{},
        }
        for name in SOURCE_BLOBS:
            gt=read_original_gt(args.source_dir/(name+"_gt.txt"))
            res=compare_one(gt,calibration["sensitivity_halfwidth_s"],lib)
            out["results"][name]=res
            print("REAL_REFERENCE_FINE_CAPTURE_SENSITIVITY",name,json.dumps({
                "source_samples":res["samples_first_turn_evaluable"],
                "ambiguous_samples":res["continuous_interval_ambiguous"],
                "coarse_refused":res["coarse_refused"],
                "fine_refused":res["fine_refused"],
                "recovered_samples":res["recovered_admission_samples"],
                "coarse_map_coverage":res["coarse_accepted_coverage_bins_count"],
                "fine_map_coverage":res["fine_accepted_coverage_bins_count"]},sort_keys=True))
        args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    finally:
        temp.cleanup()


if __name__=="__main__":
    main()
