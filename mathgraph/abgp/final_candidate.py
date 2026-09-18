"""Review-only ABGP final-lock candidate.

This package is the object for collaborator text-implementation review. It
combines executed implementation qualification, the separately reviewable
complete-PASS planning proposal, and exact file hashes. It cannot freeze or
enable the confirmatory namespace.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .implementation_qualification import run_implementation_qualification
from .manifest import load_analysis_plan, load_design_manifest
from .planning_review import build_planning_proposal


_ROOT = Path(__file__).resolve().parents[2]
_BOUND_FILES = (
    "preregistration/abgp-design-manifest-v1.json",
    "preregistration/abgp-analysis-plan-v1.json",
    "mathgraph/abgp/analysis.py",
    "mathgraph/abgp/validity.py",
    "mathgraph/abgp/executed_a.py",
    "mathgraph/abgp/executed_b.py",
    "mathgraph/abgp/executed_g.py",
    "mathgraph/abgp/executed_p.py",
    "mathgraph/abgp/executed_p_structural.py",
    "mathgraph/abgp/executed_matrix.py",
    "mathgraph/abgp/implementation_qualification.py",
    "mathgraph/abgp/planning_review.py",
    "mathgraph/abgp/final_candidate.py",
    "mathgraph/abgp/exchangeability.py",
    "mathgraph/abgp/p_structural_acquisition_worker.py",
    "mathgraph/abgp/p_structural_invocation_worker.py",
    "mathgraph/abgp/p_structural_posterior_worker.py",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_files() -> dict[str, str]:
    return {path: sha256((_ROOT / path).read_bytes()).hexdigest() for path in _BOUND_FILES}


def build_final_lock_candidate(
    *,
    a_count: int = 32,
    b_worlds_per_direction: int = 8,
    g_worlds: int = 16,
    p_count: int = 8,
    namespace: str = "ABGP-DEV-v1",
) -> dict[str, Any]:
    if namespace != "ABGP-DEV-v1":
        raise ValueError("final-lock candidate builder accepts only ABGP-DEV-v1")

    design = load_design_manifest(_ROOT / "preregistration" / "abgp-design-manifest-v1.json")
    plan = load_analysis_plan(_ROOT / "preregistration" / "abgp-analysis-plan-v1.json")
    if design.status != "REVIEW_PENDING" or design.confirmatory_execution_enabled:
        raise ValueError("candidate requires locked REVIEW_PENDING design")
    if plan.status != "REVIEW_PENDING":
        raise ValueError("candidate requires REVIEW_PENDING analysis plan")

    implementation = run_implementation_qualification(
        a_count=a_count,
        b_worlds_per_direction=b_worlds_per_direction,
        g_worlds=g_worlds,
        p_count=p_count,
        namespace=namespace,
    )
    if not implementation["implementation_qualified"]:
        raise ValueError("cannot build final-lock candidate from unqualified implementation")

    planning = build_planning_proposal(plan)
    counts_unchanged = (
        planning["arms"]["A"]["proposed_n"] == int(plan.arms["A"]["n"])
        and planning["arms"]["B"]["proposed_worlds_per_direction"]
            == int(plan.arms["B"]["worlds_per_direction"])
        and planning["arms"]["G"]["proposed_n"] == int(plan.arms["G"]["n_worlds"])
        and planning["arms"]["P"]["proposed_n"] == int(plan.arms["P"]["n"])
    )

    candidate: dict[str, Any] = {
        "schema": "abgp.final-lock-candidate.v1",
        "status": "REVIEW_PENDING",
        "review_only": True,
        "builder_can_freeze": False,
        "freeze_authorized": False,
        "confirmatory_execution_enabled": False,
        "confirmatory_namespace_used": False,
        "confirmatory_namespace_identifier": design.confirmatory_namespace,
        "design_version": design.design_version,
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": plan.digest,
        "implementation_qualification": implementation,
        "implementation_qualification_digest": implementation["artifact_digest"],
        "planning_proposal": planning,
        "planning_proposal_digest": sha256(_canonical(planning).encode("ascii")).hexdigest(),
        "scientific_pass_criteria_changed": False,
        "sample_counts_changed": not counts_unchanged,
        "bound_file_hashes": _hash_files(),
        "joint_review_required": True,
        "joint_decisions_requested": [
            "approve_or_revise_planning_alternatives",
            "approve_B_world_all_four_planning_agreement",
            "approve_P_deletion_closeness_as_mechanical_gate",
            "confirm_text_implementation_consistency",
        ],
        "post_review_rule": (
            "Only after explicit joint approval may a separate change update the normative "
            "planning assumptions, hash the resulting exact tree, mark a lock FROZEN, and "
            "make ABGP-CONFIRM-v1 executable exactly once."
        ),
        "scientific_interpretation": (
            "FINAL_PRE_FREEZE_REVIEW_CANDIDATE_NOT_CONFIRMATORY_EVIDENCE"
        ),
    }
    material = dict(candidate)
    candidate["candidate_digest"] = sha256(_canonical(material).encode("ascii")).hexdigest()
    return json.loads(_canonical(candidate))


def write_final_lock_candidate(path: str | Path, candidate: dict[str, Any]) -> None:
    Path(path).write_text(_canonical(candidate) + "\n", encoding="utf-8")
