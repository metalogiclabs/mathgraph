from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .manifest import ABGPAnalysisPlan, ABGPDesign, load_analysis_plan, load_design_manifest


_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_PATH = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"

_ARM_PATHS = {
    "A": "mathgraph/abgp/arm_a.py",
    "B": "mathgraph/abgp/arm_b.py",
    "G": "mathgraph/abgp/arm_g.py",
    "P": "mathgraph/abgp/arm_p.py",
}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha_text(value: str | bytes) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return sha256(payload).hexdigest()


def _lock_digest(lock_without_digest: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(lock_without_digest).encode("utf-8")).hexdigest()


def _is_hex_digest(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def build_review_lock(
    repo_file_map: Mapping[str, str | bytes],
    runtime_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct a review-only lock candidate.

    This function deliberately cannot freeze or enable confirmation. A future,
    separately reviewed step must create any FROZEN lock from the reviewed candidate.
    """

    design = load_design_manifest(_DESIGN_PATH)
    analysis = load_analysis_plan(_ANALYSIS_PATH)

    missing_arm_files = [path for path in _ARM_PATHS.values() if path not in repo_file_map]
    if missing_arm_files:
        raise ValueError(f"missing arm generator files: {missing_arm_files}")
    if "mathgraph/abgp/analysis.py" not in repo_file_map:
        raise ValueError("missing frozen analysis implementation")

    scientific_code_hashes = {
        path: _sha_text(repo_file_map[path]) for path in sorted(repo_file_map)
    }
    arm_generator_code_hashes = {
        arm: scientific_code_hashes[path] for arm, path in _ARM_PATHS.items()
    }

    required_runtime = {
        field
        for field in design.raw["final_lock_requirements"]
        if field
        not in {
            "design_manifest_digest",
            "analysis_plan_digest",
            "arm_generator_code_hashes",
            "analysis_implementation_hash",
        }
    }
    missing_runtime = sorted(field for field in required_runtime if field not in runtime_metadata)
    if missing_runtime:
        raise ValueError(f"missing final-lock runtime metadata: {missing_runtime}")

    lock: dict[str, Any] = {
        "schema": "mathgraph.abgp.final-lock-review.v1",
        "status": "REVIEW_PENDING",
        "confirmatory_execution_enabled": False,
        "design_version": design.design_version,
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": analysis.digest,
        "scientific_code_hashes": scientific_code_hashes,
        "arm_generator_code_hashes": arm_generator_code_hashes,
        "analysis_implementation_hash": scientific_code_hashes[
            "mathgraph/abgp/analysis.py"
        ],
    }
    for field in sorted(required_runtime):
        lock[field] = runtime_metadata[field]

    lock["review_only"] = True
    lock["builder_can_freeze"] = False
    lock["lock_digest"] = _lock_digest(lock)
    return lock


def validate_final_lock(
    lock: Mapping[str, Any],
    design: ABGPDesign,
    analysis: ABGPAnalysisPlan,
    *,
    expected_tree_hash: str | None = None,
    qualification_artifact: Mapping[str, Any] | None = None,
) -> None:
    """Validate a separately produced frozen lock.

    Validation is intentionally separate from construction. A successful DEV/QUAL
    artifact is a prerequisite but never itself authorizes confirmatory execution.
    """

    if lock.get("status") != "FROZEN":
        raise ValueError("final lock is not FROZEN")
    if lock.get("confirmatory_execution_enabled") is not True:
        raise ValueError("frozen final lock does not enable confirmatory execution")
    if lock.get("design_manifest_digest") != design.digest:
        raise ValueError("final lock design-manifest digest mismatch")
    if lock.get("analysis_plan_digest") != analysis.digest:
        raise ValueError("final lock analysis-plan digest mismatch")

    for field in design.raw["final_lock_requirements"]:
        if field not in lock or lock[field] in (None, "", {}, []):
            raise ValueError(f"final lock missing required field: {field}")

    if lock.get("qualification_status") != "QUALIFIED":
        raise ValueError("final lock is not bound to QUALIFIED test mechanics")
    qualification_digest = lock.get("qualification_evidence_digest")
    if not _is_hex_digest(qualification_digest):
        raise ValueError("final lock qualification evidence digest is malformed")

    if qualification_artifact is None:
        raise ValueError("final lock validation requires the bound qualification artifact")
    if qualification_artifact.get("schema") != "mathgraph.abgp.qualification.v1":
        raise ValueError("qualification artifact schema mismatch")
    if qualification_artifact.get("verdict") != "QUALIFIED":
        raise ValueError("qualification artifact is not QUALIFIED")
    if qualification_artifact.get("qualification_digest") != qualification_digest:
        raise ValueError("qualification artifact digest does not match final lock")
    if qualification_artifact.get("design_manifest_digest") != design.digest:
        raise ValueError("qualification artifact design-manifest digest mismatch")
    if qualification_artifact.get("analysis_plan_digest") != analysis.digest:
        raise ValueError("qualification artifact analysis-plan digest mismatch")

    if expected_tree_hash is not None and lock.get("repository_tree_hash") != expected_tree_hash:
        raise ValueError("final lock repository tree mismatch")

    arm_hashes = lock.get("arm_generator_code_hashes")
    if not isinstance(arm_hashes, Mapping) or set(arm_hashes) != {"A", "B", "G", "P"}:
        raise ValueError("final lock arm-generator hashes are incomplete")

    scientific = lock.get("scientific_code_hashes")
    if not isinstance(scientific, Mapping) or not scientific:
        raise ValueError("final lock scientific-code hash map is missing")
    if lock.get("analysis_implementation_hash") != scientific.get(
        "mathgraph/abgp/analysis.py"
    ):
        raise ValueError("final lock analysis hash is not bound to scientific code map")

    qualified_scientific = qualification_artifact.get("scientific_code_hashes")
    if qualified_scientific is not None:
        if not isinstance(qualified_scientific, Mapping):
            raise ValueError("qualification scientific-code hash map is malformed")
        for path, digest in qualified_scientific.items():
            if path in scientific and scientific[path] != digest:
                raise ValueError("final lock scientific code differs from qualified code")

    namespace = lock.get("confirmatory_namespace_identifier")
    if namespace != design.confirmatory_namespace:
        raise ValueError("final lock confirmatory namespace mismatch")

    supplied_digest = lock.get("lock_digest")
    if not _is_hex_digest(supplied_digest):
        raise ValueError("final lock digest is missing or malformed")
    material = dict(lock)
    del material["lock_digest"]
    if _lock_digest(material) != supplied_digest:
        raise ValueError("final lock digest does not match its contents")
