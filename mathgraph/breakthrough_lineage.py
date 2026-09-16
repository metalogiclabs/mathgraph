"""Immutable evidence-lineage metadata for the V81 breakthrough demo.

This module distinguishes historical authoritative evidence, post-hoc
calibration, and prospective experiments. It validates repository-local
references without pretending that remote GitHub artifacts were replayed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


V72_DEVELOPER_SHA256 = "82a884cf7b233b305f5fe3f7ec7f79e652cfd63ea0ad9e370bf0f53acbf92eed"
V80_PROTOCOL_SHA256 = "9eb6155def95e3a6cedc324ed31decc49434e1956fe54da730703c36d2b3be2e"


def historical_lineage_manifest() -> dict[str, Any]:
    stages = [
        {
            "stage": "trust_boundary",
            "freshness": "repo_contract",
            "verdict": "CANONICAL_TERMINAL_CONTRACT",
            "claim": "advisory state cannot promote truth without verifier-backed terminal evidence",
            "local_paths": ("docs/canonical_pipeline.md", "mathgraph/evidence_manifest.py"),
        },
        {
            "stage": "sair_official_pack",
            "freshness": "authoritative_historical",
            "verdict": "verified_memory_compounding_breakthrough",
            "claim": "bounded real-corpus FALSE-side finite-countermodel and held-out memory evidence",
            "local_paths": (
                "SAIR_STAGE2_EVIDENCE.md",
                "docs/evidence/official_sair_stage2_breakthrough_20260526.md",
                "scripts/replay_official_sair_stage2_breakthrough.py",
            ),
        },
        {
            "stage": "v66",
            "freshness": "prospective_historical",
            "run_id": 34970731077,
            "commit_sha": "35bb4c57a93edd1cb2032f385a4711d2935d225e",
            "verdict": "PASS_FRESH_EXTERNAL_RECURRENCE_CAPABILITY_COMPOUNDING_V66",
            "claim": "persistent acquired capability recurred causally on later external tasks",
            "local_paths": (),
        },
        {
            "stage": "v72",
            "freshness": "heldout_historical",
            "run_id": 35010530712,
            "developer_sha256": V72_DEVELOPER_SHA256,
            "verdict": "CALIBRATION_PASS_VERIFIER_GATED_RECURSIVE_GRAPH_DEVELOPMENT_V72",
            "claim": "learned proposal ordering reduced verifier work while exact verification controlled admission",
            "local_paths": ("experiments/verifier_gated_graph_hillclimb_v72/run.py",),
        },
        {
            "stage": "v73",
            "freshness": "prospective_historical",
            "run_id": 35010801321,
            "verdict": "PASS_PROSPECTIVE_SIX_OP_VERIFIER_GATED_GRAPH_DEVELOPMENT_V73",
            "claim": "frozen proposer and verifier transferred prospectively to six-operation sources",
            "local_paths": ("experiments/prospective_six_op_graph_development_v73/run.py",),
        },
        {
            "stage": "v74",
            "freshness": "posthoc_exact_audit",
            "run_id": 35011144153,
            "verdict": "PASS_GLOBAL_FIXED_BUDGET_FRONTIER_OPTIMALITY_V74",
            "claim": "V73 endpoints were exact global optima for the frozen depth-2 fixed-budget objective",
            "local_paths": ("experiments/global_frontier_optimality_audit_v74/run.py",),
        },
        {
            "stage": "v75",
            "freshness": "posthoc_exact_audit",
            "run_id": 35011310866,
            "verdict": "PASS_CERTIFIED_DEPTH3_EXPANSION_OBSTRUCTION_V75",
            "claim": "lawful depth-3 expansion exposed exact residuals from previously depth-2-global states",
            "local_paths": ("experiments/deep_closure_optimality_audit_v75/run.py",),
        },
        {
            "stage": "v76",
            "freshness": "posthoc_repair",
            "run_id": 35011727011,
            "artifact_id": 10413966395,
            "verdict": "PASS_MINIMAL_DEPTH3_VERIFIER_EXPANSION_REPAIR_V76",
            "claim": "changing verifier horizon alone repaired all audited depth-3 residuals to global optima",
            "local_paths": ("experiments/depth3_verifier_gated_repair_v76/run.py",),
        },
        {
            "stage": "v77",
            "freshness": "prospective",
            "run_id": 35052024868,
            "artifact_id": 10429163134,
            "verdict": "PASS_PROSPECTIVE_DEVELOPMENTAL_CYCLE_TRANSFER_V77",
            "claim": "prospective sufficiency-obstruction-minimal-repair-sufficiency cycle on seven-operation sources",
            "local_paths": ("experiments/prospective_developmental_cycle_v77/run.py",),
        },
        {
            "stage": "v78",
            "freshness": "prospective",
            "run_id": 35053589172,
            "artifact_id": 10429139836,
            "verdict": "PASS_PROSPECTIVE_AUTONOMOUS_HORIZON_CONTROLLER_V78",
            "claim": "controller autonomously selected reuse versus verifier-only expansion through horizon 4",
            "local_paths": ("experiments/autonomous_horizon_controller_v78/run.py",),
        },
        {
            "stage": "v79",
            "freshness": "posthoc_calibration",
            "run_id": 35054597764,
            "artifact_id": 10430114950,
            "verdict": "NO_CERTIFIED_ACTION_LANGUAGE_OBSTRUCTION_V79",
            "claim": "no one-swap local trap found in selected bounded depth-5 calibration",
            "local_paths": ("experiments/action_language_obstruction_v79/run.py",),
        },
        {
            "stage": "v80",
            "freshness": "prospective",
            "run_id": 35058339100,
            "commit_sha": "6cf0db1455e517899fc76dbb4bde6087f8ca1204",
            "artifact_id": 10432568044,
            "artifact_digest": "sha256:36d4035d6c51bf2661548e3a691dade5991da57dc39691c8c06a43dcfc72eca7",
            "protocol_sha256": V80_PROTOCOL_SHA256,
            "developer_sha256": V72_DEVELOPER_SHA256,
            "verdict": "PASS_PROSPECTIVE_DEEP_HORIZON_ACTION_INVARIANCE_V80",
            "claim": "six fresh nine-operation sources reached exact global endpoints through horizons 2..6 with zero action-language expansions",
            "metrics": {
                "sources": 6,
                "total_states_enumerated": 18205,
                "total_obstruction": 345,
                "total_recovered": 345,
                "reuse_decisions": 8,
                "verifier_expansion_decisions": 16,
                "action_language_expansion_required_count": 0,
                "causal_new_reach_examples": 28,
                "learned_total_checks": 851,
                "generic_total_checks": 1054,
            },
            "local_paths": ("experiments/prospective_deep_horizon_controller_v80/run.py",),
        },
    ]
    return {
        "schema": "mathgraph.breakthrough-lineage.v81",
        "stages": stages,
        "historical_claim_policy": "validate immutable identifiers and local replay contracts; do not relabel as fresh",
    }


def validate_historical_lineage(repo_root: Path) -> dict[str, Any]:
    manifest = historical_lineage_manifest()
    missing_local: list[str] = []
    for stage in manifest["stages"]:
        for rel in stage.get("local_paths", ()):  # exact repository-local contracts
            if not (repo_root / rel).exists():
                missing_local.append(rel)

    repo_local_ok = not missing_local
    return {
        "schema": "mathgraph.breakthrough-lineage-validation.v81",
        "repo_local_files_ok": repo_local_ok,
        "missing_local_paths": sorted(set(missing_local)),
        "historical_status": (
            "HISTORICAL_LINEAGE_VALIDATED" if repo_local_ok else "UNVERIFIED_IN_THIS_RUN"
        ),
        "missing_external_artifact_policy": "UNVERIFIED_IN_THIS_RUN",
        "external_artifacts_replayed": False,
        "stages": manifest["stages"],
    }
