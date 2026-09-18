"""One-shot ABGP confirmatory execution plumbing for MathGraph.

Scientific generators and analysis are unchanged. This module only:
- binds the approved frozen counts and tree hash,
- authorizes ABGP-CONFIRM-v1 in-process,
- supports deterministic P sharding by disjoint episode index ranges,
- aggregates raw arm outputs through the already-frozen analysis.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from .analysis import analyze_matrix
from .executed_a import run_a_batch
from .executed_b import run_b_batch
from .executed_g import run_structural_g_batch
from .executed_matrix import _ancestry_audits, _b_analysis_input
from .executed_p_structural import run_structural_p_batch, summarize_structural_p_episodes
from .manifest import (
    activate_confirmatory_namespace,
    load_analysis_plan,
    load_design_manifest,
    reset_development_namespace,
)

_ROOT = Path(__file__).resolve().parents[2]
_DESIGN = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_PLAN = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
_NAMESPACE = "ABGP-CONFIRM-v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("ascii")).hexdigest()


def build_execution_lock(repository_tree_hash: str) -> dict[str, Any]:
    if not isinstance(repository_tree_hash, str) or len(repository_tree_hash) != 40:
        raise ValueError("repository_tree_hash must be a git SHA-1 tree id")
    design = load_design_manifest(_DESIGN)
    plan = load_analysis_plan(_PLAN)
    if design.status != "FROZEN" or plan.status != "FROZEN":
        raise ValueError("confirmatory execution requires FROZEN design and analysis")
    approval = design.raw.get("final_lock_approval", {})
    joint = plan.raw.get("joint_approval", {})
    approved = plan.raw.get("qualification", {}).get("approved_planning", {})
    if approval.get("status") != "APPROVED" or joint.get("status") != "APPROVED":
        raise ValueError("joint approval is not frozen into the normative package")
    if not approved.get("approved"):
        raise ValueError("approved planning is not frozen")
    counts = approved.get("counts", {})
    expected_counts = {
        "A": int(plan.arms["A"]["n"]),
        "B_worlds_per_direction": int(plan.arms["B"]["worlds_per_direction"]),
        "B_total_worlds": int(plan.arms["B"]["n_units"]),
        "G": int(plan.arms["G"]["n_worlds"]),
        "P": int(plan.arms["P"]["n"]),
    }
    if counts != expected_counts:
        raise ValueError("approved counts do not match frozen analysis plan")
    material = {
        "schema": "mathgraph.abgp.execution-lock.v1",
        "status": "FROZEN",
        "confirmatory_execution_enabled": True,
        "confirmatory_namespace_identifier": _NAMESPACE,
        "repository_tree_hash": repository_tree_hash,
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": plan.digest,
        "approved_candidate_digest": approval.get("approved_candidate_digest"),
        "approved_planning": approved,
        "one_shot_execution_marker_policy": (
            "STARTED marker must be atomically created before any confirmatory seed is derived; "
            "any existing STARTED or COMPLETED marker permanently blocks another run in this namespace"
        ),
        "scientific_code_change": False,
        "execution_plumbing_only": True,
    }
    lock = dict(material)
    lock["lock_digest"] = _digest(material)
    return json.loads(_canonical(lock))


def _activate(lock: dict[str, Any]) -> None:
    activate_confirmatory_namespace(_NAMESPACE, lock)


def run_confirmatory_a(lock: dict[str, Any]) -> dict[str, Any]:
    _activate(lock)
    plan = load_analysis_plan(_PLAN)
    result = run_a_batch(int(plan.arms["A"]["n"]))
    if not result["confirmatory_namespace_used"]:
        raise AssertionError("A did not record confirmatory namespace use")
    return result


def run_confirmatory_b(lock: dict[str, Any]) -> list[dict[str, Any]]:
    _activate(lock)
    plan = load_analysis_plan(_PLAN)
    records = run_b_batch(int(plan.arms["B"]["worlds_per_direction"]))
    if not records or not all(record["confirmatory_namespace_used"] for record in records):
        raise AssertionError("B did not record confirmatory namespace use")
    return records


def run_confirmatory_g(lock: dict[str, Any]) -> dict[str, Any]:
    _activate(lock)
    plan = load_analysis_plan(_PLAN)
    result = run_structural_g_batch(int(plan.arms["G"]["n_worlds"]))
    if not result["confirmatory_namespace_used"]:
        raise AssertionError("G did not record confirmatory namespace use")
    return result


def run_confirmatory_p_shard(
    lock: dict[str, Any], *, start_index: int, episode_count: int
) -> dict[str, Any]:
    _activate(lock)
    plan = load_analysis_plan(_PLAN)
    total = int(plan.arms["P"]["n"])
    if start_index < 0 or episode_count <= 0 or start_index + episode_count > total:
        raise ValueError("P shard lies outside frozen episode range")
    result = run_structural_p_batch(
        episode_count,
        namespace=_NAMESPACE,
        start_index=start_index,
    )
    if not result["confirmatory_namespace_used"]:
        raise AssertionError("P shard did not record confirmatory namespace use")
    return result


def aggregate_confirmatory(
    lock: dict[str, Any],
    *,
    a: dict[str, Any],
    b_records: list[dict[str, Any]],
    g: dict[str, Any],
    p_shards: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    _activate(lock)
    plan = load_analysis_plan(_PLAN)
    p_episodes = [
        episode
        for shard in p_shards
        for episode in shard.get("episodes", [])
    ]
    p = summarize_structural_p_episodes(p_episodes)

    if len(a.get("episodes", [])) != int(plan.arms["A"]["n"]):
        raise ValueError("A confirmatory count mismatch")
    expected_b = int(plan.arms["B"]["n_units"])
    if len(b_records) != expected_b:
        raise ValueError("B confirmatory count mismatch")
    if len(g.get("worlds", [])) != int(plan.arms["G"]["n_worlds"]):
        raise ValueError("G confirmatory count mismatch")
    if len(p.get("episodes", [])) != int(plan.arms["P"]["n"]):
        raise ValueError("P confirmatory count mismatch")
    p_indices = [int(row["episode_index"]) for row in p["episodes"]]
    if p_indices != list(range(int(plan.arms["P"]["n"]))):
        raise ValueError("P shards do not exactly partition the frozen episode range")

    raw = {
        "A": a["analysis_input"],
        "B": _b_analysis_input(b_records),
        "G": g["analysis_input"],
        "P": p["analysis_input"],
    }
    analysis = analyze_matrix(raw)
    ancestry = _ancestry_audits(a, b_records, g, p)
    result = {
        "schema": "mathgraph.abgp.confirmatory-result.v1",
        "mode": "CONFIRMATORY",
        "namespace": _NAMESPACE,
        "confirmatory_namespace_used": True,
        "execution_lock": lock,
        "counts": {
            "A": len(a["episodes"]),
            "B_worlds": len(b_records),
            "B_worlds_per_direction": int(plan.arms["B"]["worlds_per_direction"]),
            "G": len(g["worlds"]),
            "P": len(p["episodes"]),
        },
        "raw_input_digests": {arm: _digest(raw[arm]) for arm in ("A", "B", "G", "P")},
        "inferential_ancestry_audit": ancestry,
        "analysis": analysis,
        "combined_verdict": analysis["combined_verdict"],
        "claim_boundary": load_design_manifest(_DESIGN).raw["claim_boundary"],
    }
    result["result_digest"] = _digest(result)
    return json.loads(_canonical(result))


def reset_after_test_only() -> None:
    reset_development_namespace()
