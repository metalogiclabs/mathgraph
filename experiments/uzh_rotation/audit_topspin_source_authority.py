"""TOPSPIN source-authority guard (v2) for short-lag persistence aliases.

The conventional real-event matcher from v1 is strictly unchanged.
Only the semantic *authorization* policy is new. This code cannot infer an
object revolution, physical camera spin, heading, calibrated gyro, or
navigation correction from a stationary event camera's temporal recurrence.
"""
import argparse
import json
from pathlib import Path

from audit_topspin_recurrence import audit as v1_audit, MIN_LAG, MAX_LAG

V1_MATCHER_BLOB = "e3f49a33fa0e0c3e4a93a939f272337af2a128a2"
V1_PROTOCOL_COMMIT = "6e193dbae68d3f7fc5f3991c74a52d01acc18712"


def assess_v1_result(prior):
    """Uses only training evidence to gate the original v1 recurrence claim."""
    exp=prior["experiment"]
    full=exp["conventional_full_column_descriptor_training"]
    rate=exp["event_rate_only_baseline_training"]
    heldout=exp["conventional_full_column_descriptor_later"]

    if full["decision"]!="CANDIDATE_TRAINING_DISTINCT_TEMPORAL_RECURRENCE":
        state="UNKNOWN_OR_REJECTED_BY_ORIGINAL_TRAINING_TEST"
        reason="Original training evidence does not distinguish allowed recurrence lags"
    elif full["best_lag_bins"]==MIN_LAG:
        state="UNKNOWN_MINIMUM_LAG_PERSISTENCE_CONFOUNDED"
        reason="Peak is at search minimum; short-term persistence is not separated from periodic return"
    elif full["best_lag_bins"]==MAX_LAG:
        state="UNKNOWN_MAXIMUM_LAG_GRAMMAR_BOUNDARY"
        reason="Peak is at search maximum; longer periods have not been tested"
    else:
        state="CANDIDATE_NONBOUNDARY_TEMPORAL_RECURRENCE_ONLY"
        reason="Interior training peak; still no independent object period or camera heading witness"
    result={
        "original_v1_source_sha256":prior["original_sha256"],
        "original_v1_protocol_commit":V1_PROTOCOL_COMMIT,
        "original_matcher_git_blob":V1_MATCHER_BLOB,
        "source_appearance_type":"STATIONARY CAMERA OBSERVING ROTATING OBJECT",
        "training_only_gate_state":state,
        "training_only_gate_reason":reason,
        "training_best_lag_bins":full["best_lag_bins"],
        "training_second_lag_bins":full["second_lag_bins"],
        "training_margin":full["margin"],
        "training_period_candidate_count":full.get("candidate_lags_evaluated"),
        "conventional_event_rate_baseline_best_lag_bins":rate["best_lag_bins"],
        "full_descriptor_vs_scalar_baseline_unique_advantage":"UNKNOWN",
        "validation_rank_offline_only":heldout["heldout_rank"],
        "validation_score_offline_only":heldout["frozen_lag_score"],
        "validation_cannot_upgrade_training_authority":True,
        "source_proves_real_periodic_return":False,
        "source_proves_full_physical_turns":False,
        "source_is_spinning_aircraft":False,
        "independent_external_heading_truth":False,
        "raw_camera_gyro_alignment":False,
        "navigation_heading_correction_authorized":False,
        "special_mathgraph_reliability_advantage":"UNKNOWN",
    }
    return result


def run(archive,sha=None):
    base=v1_audit(archive,sha)
    return {
        "source":base["original_archive"],
        "source_sha256":base["original_sha256"],
        "source_md5":base["original_author_md5"],
        "source_event_metrics":base["raw_observation"],
        "unchanged_v1_temporal_matcher":base["experiment"],
        "source_authority_v2":assess_v1_result(base),
        "comparison":"Equally informed conventional 48-feature matcher can apply same boundary rule",
        "verification_scope":"Causal within-source temporal matching and ambiguity audit; not a compass",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--sha256")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    report=run(args.archive,args.sha256)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("TOPSPIN_SOURCE_AUTHORITY_V2",json.dumps({
        "source":report["source"],"source_sha256":report["source_sha256"],
        "authority":report["source_authority_v2"]},sort_keys=True))

if __name__=="__main__":
    main()
