"""Post-approval frozen-lock verifier for ABGP.

This module binds the exact FROZEN normative package and executed DEV
implementation. It deliberately keeps confirmation disabled; unlocking and the
one-shot confirmatory execution are separate operations.
"""
from __future__ import annotations

from hashlib import sha256
import json
import platform
import sys
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
    "mathgraph/abgp/exchangeability.py",
    "mathgraph/abgp/p_structural_acquisition_worker.py",
    "mathgraph/abgp/p_structural_invocation_worker.py",
    "mathgraph/abgp/p_structural_posterior_worker.py",
    "mathgraph/abgp/sandbox_runtime.py",
)

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _file_hash(path: str) -> str:
    return sha256((_ROOT / path).read_bytes()).hexdigest()

def _hashes() -> dict[str, str]:
    return {path: _file_hash(path) for path in _BOUND_FILES}

def build_frozen_lock(
    *,
    repository_tree_hash: str,
    repository_commit: str,
    a_count: int = 12,
    b_worlds_per_direction: int = 3,
    g_worlds: int = 6,
    p_count: int = 4,
) -> dict[str, Any]:
    design = load_design_manifest(_ROOT / "preregistration" / "abgp-design-manifest-v1.json")
    plan = load_analysis_plan(_ROOT / "preregistration" / "abgp-analysis-plan-v1.json")
    if design.status != "FROZEN" or plan.status != "FROZEN":
        raise ValueError("frozen lock requires FROZEN design and analysis plan")
    if design.confirmatory_execution_enabled:
        raise ValueError("freeze verification requires confirmation to remain disabled")

    approval = design.raw.get("final_lock_approval", {})
    plan_approval = plan.raw.get("joint_approval", {})
    if approval.get("status") != "APPROVED" or plan_approval.get("status") != "APPROVED":
        raise ValueError("joint approval is not bound into both normative files")
    if approval.get("approved_candidate_digest") != "771793f52cc8228c54bf2ac8ab46ebbcb0c7a99284d94e3042951a7976921e04":
        raise ValueError("approved candidate digest mismatch")

    implementation = run_implementation_qualification(
        a_count=a_count,
        b_worlds_per_direction=b_worlds_per_direction,
        g_worlds=g_worlds,
        p_count=p_count,
    )
    planning = build_planning_proposal(plan)
    if not implementation["implementation_qualified"]:
        raise ValueError("frozen implementation qualification failed")
    if planning["status"] != "FROZEN_APPROVED":
        raise ValueError("planning is not frozen-approved")
    if not planning["approved_by_collaborators"] or not planning["complete_pass_power_qualified"]:
        raise ValueError("approved complete-PASS planning is not qualified")

    hashes = _hashes()
    lock: dict[str, Any] = {
        "schema": "abgp.frozen-lock.v1",
        "status": "FROZEN",
        "freeze_authorized": True,
        "joint_review_complete": True,
        "confirmatory_execution_enabled": False,
        "confirmatory_namespace_used": False,
        "confirmatory_namespace_identifier": design.confirmatory_namespace,
        "one_shot_execution_marker_policy": "exactly one completion marker is permitted after a separate unlock change",
        "repository_commit": repository_commit,
        "repository_tree_hash": repository_tree_hash,
        "approved_candidate_head": approval["approved_candidate_head"],
        "approved_candidate_digest": approval["approved_candidate_digest"],
        "approval_review_commit": approval["review_commit"],
        "approval_text": approval["approval_text"],
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": plan.digest,
        "bound_file_hashes": hashes,
        "arm_generator_code_hashes": {
            "A": hashes["mathgraph/abgp/executed_a.py"],
            "B": hashes["mathgraph/abgp/executed_b.py"],
            "G": hashes["mathgraph/abgp/executed_g.py"],
            "P": hashes["mathgraph/abgp/executed_p_structural.py"],
        },
        "verifier_implementation_hash": hashes["mathgraph/abgp/executed_a.py"],
        "protected_evaluator_hash": hashes["mathgraph/abgp/executed_g.py"],
        "analysis_implementation_hash": hashes["mathgraph/abgp/analysis.py"],
        "grammar_family_generator_hashes": {
            family: hashes["mathgraph/abgp/executed_b.py"]
            for family in ("extensional", "compositional", "reachability", "constraint_order")
        },
        "sham_object_construction_hash": hashes["mathgraph/abgp/executed_p_structural.py"],
        "wrong_class_construction_hash": hashes["mathgraph/abgp/executed_b.py"],
        "corruption_implementation_hash": hashes["mathgraph/abgp/executed_g.py"],
        "ablation_implementation_hash": hashes["mathgraph/abgp/p_structural_invocation_worker.py"],
        "ordinary_explanation_oracle_hashes": {
            "A": hashes["mathgraph/abgp/executed_a.py"],
            "B": hashes["mathgraph/abgp/executed_b.py"],
            "P": hashes["mathgraph/abgp/p_structural_posterior_worker.py"],
        },
        "bisimulation_canonicalizer_hashes": {
            "B": hashes["mathgraph/abgp/executed_b.py"],
            "P": hashes["mathgraph/abgp/p_structural_posterior_worker.py"],
        },
        "inferential_unit_audit_hashes": {
            arm: hashes["mathgraph/abgp/executed_matrix.py"] for arm in ("A", "B", "G", "P")
        },
        "qualification_status": implementation["status"],
        "qualification_evidence_digest": implementation["artifact_digest"],
        "planning_status": planning["status"],
        "planning_proposal_digest": sha256(_canonical(planning).encode("ascii")).hexdigest(),
        "approved_planning": plan.raw["qualification"]["approved_planning"],
        "model_and_runtime_versions": {
            "python": platform.python_version(),
            "implementation": sys.implementation.name,
            "platform": platform.platform(),
        },
        "dependency_environment_hash": sha256(
            ("python-stdlib|" + platform.python_version()).encode("ascii")
        ).hexdigest(),
        "resource_budgets": {
            "qualification_counts": {
                "A": a_count,
                "B_worlds_per_direction": b_worlds_per_direction,
                "G": g_worlds,
                "P": p_count,
            },
            "confirmatory_counts": plan.raw["qualification"]["approved_planning"]["counts"],
        },
        "scientific_pass_criteria_changed": False,
        "sample_counts_changed_from_approved_candidate": False,
        "scientific_interpretation": "FROZEN_NORMATIVE_PACKAGE_CONFIRMATION_STILL_LOCKED",
    }
    material = dict(lock)
    lock["lock_digest"] = sha256(_canonical(material).encode("ascii")).hexdigest()
    return json.loads(_canonical(lock))

def write_frozen_lock(path: str | Path, lock: dict[str, Any]) -> None:
    Path(path).write_text(_canonical(lock) + "\n", encoding="utf-8")
