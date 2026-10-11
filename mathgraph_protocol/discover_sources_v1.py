"""Exact local-byte adapter for one historical evidence pack; no replay or network."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .json_strict import strict_json_loads


PACK_ID = "recursive_residual_transfer_v1_20260523"
MANIFEST_SHA256 = "449e9f9378a90ffb975f21cd5d534455f0d03bc393bf821daefdc000950509c5"
METRICS_SHA256 = "83c9a568d2fc3f9c06bd4487c51a7a6af1ba44323a33e6b3e3b86e23d1bf0b2c"


def _checked(path: Path, digest: str, size: int | None = None) -> bytes:
    payload = path.read_bytes()
    if size is not None and len(payload) != size:
        raise ValueError(f"SOURCE_SIZE_MISMATCH: {path.name}")
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"SOURCE_DIGEST_MISMATCH: {path.name}")
    return payload


def request_from_recursive_transfer(pack_dir: str | Path) -> dict[str, Any]:
    """Check available exact bytes and produce a portable advisory request.

    Manifest and metric pins identify this example, not an authenticated producer.
    Absent artifact references remain explicit; required derivation inputs fail
    operationally if unavailable. Every present manifest artifact is checked.
    """
    directory = Path(pack_dir)
    manifest_bytes = _checked(directory / "manifest.json", MANIFEST_SHA256)
    metrics_bytes = _checked(directory / "metrics.json", METRICS_SHA256)
    manifest = strict_json_loads(manifest_bytes)
    metrics = strict_json_loads(metrics_bytes)
    base = f"examples/evidence_packs/{PACK_ID}"
    sources = []
    for name, payload, digest in (("manifest", manifest_bytes, MANIFEST_SHA256),
                                  ("metrics", metrics_bytes, METRICS_SHA256)):
        sources.append({
            "source_id": name, "locator": f"{base}/{name}.json", "repo_path": f"{base}/{name}.json",
            "bundle": None, "bundle_relative_path": None, "sha256": digest,
            "size_bytes": len(payload), "availability": "PRESENT", "integrity_check": "MATCHED",
            "required_for_full_replay": False,
        })
    diagnostics = ["HISTORICAL_RESULTS_ADVISORY: experiment not rerun or authenticated; local hashes establish byte identity only."]
    for artifact in manifest["artifacts"]:
        path = directory / "source_artifacts" / artifact["filename"]
        present = path.is_file()
        if present:
            _checked(path, artifact["sha256"], artifact["size_bytes"])
        else:
            diagnostics.append(f"MISSING_LOCAL_ARTIFACT: {artifact['role']}")
            if artifact["required_for_full_replay"]:
                diagnostics.append(f"FULL_REPLAY_UNAVAILABLE: {artifact['role']}")
        sources.append({
            "source_id": artifact["role"], "locator": artifact["source_path"],
            "repo_path": artifact["repo_path"], "bundle": artifact["bundle"],
            "bundle_relative_path": artifact["bundle_relative_path"],
            "sha256": artifact["sha256"], "size_bytes": artifact["size_bytes"],
            "availability": "PRESENT" if present else "MISSING",
            "integrity_check": "MATCHED" if present else "NOT_CHECKED",
            "required_for_full_replay": artifact["required_for_full_replay"],
        })
    diagnostics.extend(f"MISSING_EXPECTED_ARTIFACT: {name}" for name in manifest["missing_expected_artifacts"])
    diagnostics.append("FULL_REPLAY_NOT_PERFORMED: original equations, matrix, toolchain and replay inputs are not qualified by this adapter.")
    # This is the existing route-memory heuristic, applied to pinned, reported
    # metrics. It is a candidate feature, not a probability of mathematical truth.
    gain = metrics["compact_transfer_gain_vs_generic_positive"]
    candidate = {
        "candidate_id": "recursive_transfer_replay_candidate", "candidate_type": "recursive_transfer_replay_candidate",
        "title": "Recursive residual transfer replay validation",
        "description": "Use reported compact route-memory results to propose a bounded replay comparison.",
        "source_ids": ["metrics", "source_summary", "report"],
        "suggested_route": "frozen evidence replay and route-memory comparison", "descension_target": "replay_validation",
        "advisory_only": True, "can_promote_truth": False,
        "expected_certificate_value": 0.25, "expected_obstruction_value": 0.35,
        "expected_residual_compression": 0.75, "expected_constructor_reuse": min(0.95, 0.45 + gain / 500.0),
        "expected_bridge_value": 0.35, "novelty_score": 0.35,
        "verification_cost": 0.25, "duplicate_risk": 0.25,
        "notes": "Reported historical metrics and route scores are advisory only; not terminal truth, not a certificate, and cannot promote VERIFIED_PROOF.",
    }
    metric_names = ("compact_transfer_gain_vs_generic_positive", "compact_retains_recursive_gain",
                    "compact_prunes_recursive_memory", "generic_mean_recoveries", "true_contamination_max",
                    "all_gates_pass", "advisory_boundary_ok")
    return {
        "schema_version": "mathgraph.discover-request.v1", "request_id": f"{PACK_ID}:discover-v1",
        "policy": {"mode": "balanced", "beta": 1.0}, "top_k": 1, "candidates": [candidate],
        "sources": sources, "source_diagnostics": diagnostics,
        "reported_metrics": [{"name": name, "value": metrics[name], "source_id": "metrics"} for name in metric_names],
    }
