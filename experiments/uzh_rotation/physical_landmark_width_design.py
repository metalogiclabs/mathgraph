#!/usr/bin/env python3
"""Synthetic width-vs-timing-jitter design experiment using canonical C99.

Constructs a passive four-sector laboratory visual fiducial in a 64-bin scene.
For each width and declared +/- j bins of phase uncertainty, exhaustively
sweeps all integer source shifts in [-j,+j] and all four initial headings.
No physical camera, real phase calibration, flight or safety warrant.
"""
import argparse
import json
from pathlib import Path
import random
import tempfile

from audit_finite_partial_map import load_library
from finite_witness_compass import HYPOTHESES
from physical_native_witness_replay import native_follow

BINS=64
SECTOR_BINS=16
CENTER=7
HORIZON=32
MARKERS=(0x0000,0xFFFF,0x0F0F,0xF0F0)
WIDTHS=(1,3,5,7)
JITTERS=(0,1,2,3)
BOUNDARY="SYNTHETIC_FOUR_SECTOR_PASSIVE_LANDMARK_ASSUMED_NOISE2_PHASESHIFT"

def make_trial(seed, heading, width, phase_shift=0, occluded=()):
    if width not in WIDTHS or heading not in HYPOTHESES or not -3<=phase_shift<=3:
        raise ValueError("invalid finite fiducial trial")
    rng=random.Random(708170+seed*97)
    base=[rng.getrandbits(16) for _ in range(SECTOR_BINS)]
    scene=base*4
    radius=width//2
    for sector,marker in enumerate(MARKERS):
        for k in range(CENTER-radius,CENTER+radius+1):
            scene[sector*SECTOR_BINS+k]=marker
    # First revolution map and later camera have separate <=1 bit changes:
    # total Hamming difference to the physical source is <=2.
    reference=tuple(word^(1<<rng.randrange(16)) for word in scene)
    excluded=set(occluded)
    columns=tuple(
        None if s in excluded else
        scene[(heading+s+phase_shift)%BINS]^(1<<rng.randrange(16))
        for s in range(HORIZON+1)
    )
    return reference, columns

def independent_minimum_cross_sector_distance(reference, jitter):
    """Referee-only center-bin exhaustive pair/offset separation bound."""
    if not 0<=jitter<=3:
        raise ValueError("outside declared phase-jitter grammar")
    values=[]
    for a in HYPOTHESES:
        for b in HYPOTHESES:
            if a>=b:
                continue
            for da in range(-jitter,jitter+1):
                for db in range(-jitter,jitter+1):
                    ia=(a+CENTER+da)%BINS
                    ib=(b+CENTER+db)%BINS
                    values.append((reference[ia]^reference[ib]).bit_count())
    return min(values)

def experiment(seeds=16):
    if not 1<=seeds<=128:
        raise ValueError("unbounded synthetic census")
    rows=[]
    with tempfile.TemporaryDirectory() as temp:
        native=load_library(Path(temp)/"canonical_partial_map.so")
        for width in WIDTHS:
            for jitter in JITTERS:
                result={"landmark_width_bins":width,"phase_error_radius_bins":jitter,
                        "trials":0,"model_unique":0,"model_unknown":0,
                        "model_false_unique":0,"camera_attempts":0,
                        "center_pair_separation_warranted":0,
                        "observed_source_shift_values":list(range(-jitter,jitter+1))}
                examples=[]
                for seed in range(seeds):
                    for heading in HYPOTHESES:
                        for shift in range(-jitter,jitter+1):
                            ref, columns=make_trial(seed,heading,width,shift)
                            bound=independent_minimum_cross_sector_distance(ref,jitter)
                            out=native_follow(native,ref,columns,jitter=jitter)
                            result["trials"]+=1
                            result["model_unique"]+=int(out["status"]=="MODEL_UNIQUE")
                            result["model_unknown"]+=int(out["status"]=="UNKNOWN_OBSTRUCTION")
                            result["model_false_unique"]+=int(
                                out["status"]=="MODEL_UNIQUE" and out["accepted_bin"]!=heading)
                            result["camera_attempts"]+=out["attempts"]
                            result["center_pair_separation_warranted"]+=int(bound>4)
                            if seed==0 and heading==0 and shift in (0,jitter):
                                examples.append({
                                    "seed":seed,"true_heading_grader_only":heading,
                                    "actual_source_phase_shift_grader_only":shift,
                                    "min_reference_hamming_across_jitter":bound,
                                    "decision":out})
                result["representative_traces"]=examples
                rows.append(result)
    return {
        "boundary":BOUNDARY,
        "source_authority":"MODEL_ONLY_NOT_MEASURED",
        "sensor_power_measured":False,
        "hardware_acquisitions":0,
        "physical_heading_correction_authorized":False,
        "error_model":"<=1 firstturn bit and <=1 observed bit; supplied phase shift within +/- j bins",
        "one_angular_bin_degrees":360/BINS,
        "fiducial_marker_pattern":list(MARKERS),
        "center_bin":CENTER,
        "all_conditions":rows,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",type=int,default=16)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    r=experiment(args.seeds)
    Path(args.output).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    for row in r["all_conditions"]:
        print("ROBUST_LANDMARK",row["landmark_width_bins"],row["phase_error_radius_bins"],
              row["model_unique"],"/",row["trials"],
              "unknown",row["model_unknown"],"wrong",row["model_false_unique"],
              "camera_reads",row["camera_attempts"])
    print("NO_PHYSICAL_BENCH_RESULT")

if __name__=="__main__":
    main()
