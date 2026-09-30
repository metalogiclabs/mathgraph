"""DiscoveryScheduler v0: deterministic taste policy ledger.

The scheduler ranks testable continuation candidates and allocates advisory
attention.  It does not prove, certify, or promote truth.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ALLOWED_DESCENSION_TARGETS = {
    "finite_countermodel_attempt",
    "verifier_contact",
    "lean_verifier_contact_candidate",
    "lean_digest_repair",
    "obstruction_naming_attempt",
    "obstruction_naming",
    "constructor_synthesis_attempt",
    "constructor_synthesis",
    "projection_test",
    "representation_repair",
    "evidence_replay",
    "replay_validation",
    "lawbook_ingestion",
    "reason_atlas_route_test",
    "trust_audit",
}


@dataclass(frozen=True)
class DiscoveryCandidate:
    candidate_id: str
    candidate_type: str
    source: str
    source_kind: str = ""
    source_ref: str = ""
    title: str = ""
    description: str = ""
    mode_hint: str = ""
    residual_cluster: str = ""
    basin: str = ""
    micro_basin: str = ""
    suggested_route: str = ""
    descension_target: str = ""
    expected_certificate_value: float = 0.0
    expected_obstruction_value: float = 0.0
    expected_residual_compression: float = 0.0
    expected_projection_gain: float = 0.0
    expected_reuse: float = 0.0
    expected_constructor_reuse: float = 0.0
    expected_bridge_value: float = 0.0
    novelty_score: float = 0.0
    verification_cost: float = 0.0
    duplicate_risk: float = 0.0
    overfit_risk: float = 0.0
    foreign_moisture_risk: float = 0.0
    trust_status: str = ""
    taste_score: float = 0.0
    attention_probability: float = 0.0
    chosen: bool = False
    advisory_only: bool = True
    can_promote_truth: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class TastePolicy:
    policy_id: str
    beta: float
    mode: str
    weights: dict[str, float]
    created_at: str
    advisory_only: bool = True
    can_promote_truth: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DiscoveryOutcome:
    candidate_id: str
    outcome_status: str
    verifier_contacted: bool = False
    terminal_form_observed: str = ""
    verified_gain: float = 0.0
    residual_delta: float = 0.0
    lawbook_delta: float = 0.0
    obstruction_created: bool = False
    certificate_created: bool = False
    projection_created: bool = False
    cost_observed: float = 0.0
    trust_boundary_violation: bool = False
    notes: str = ""


@dataclass(frozen=True)
class DiscoveryRunResult:
    run_id: str
    policy_id: str
    candidate_count: int
    eligible_count: int
    chosen_count: int
    advisory_boundary_ok: bool
    can_promote_truth_count: int
    outputs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def default_weights(mode: str) -> dict[str, float]:
    modes = {
        "harvest": {
            "certificate": 2.0,
            "obstruction": 0.8,
            "compression": 1.0,
            "projection": 0.6,
            "reuse": 1.6,
            "novelty": 0.4,
            "cost": 1.2,
            "duplicate": 1.0,
            "overfit": 0.8,
            "foreign": 1.0,
        },
        "frontier": {
            "certificate": 0.8,
            "obstruction": 1.8,
            "compression": 1.8,
            "projection": 1.0,
            "reuse": 0.8,
            "novelty": 1.5,
            "cost": 0.8,
            "duplicate": 0.7,
            "overfit": 0.9,
            "foreign": 0.8,
        },
        "architectonic": {
            "certificate": 0.6,
            "obstruction": 1.0,
            "compression": 1.7,
            "projection": 2.0,
            "reuse": 1.5,
            "novelty": 1.2,
            "cost": 0.6,
            "duplicate": 0.8,
            "overfit": 0.8,
            "foreign": 0.7,
        },
        "balanced": {
            "certificate": 1.2,
            "obstruction": 1.2,
            "compression": 1.3,
            "projection": 1.1,
            "reuse": 1.1,
            "novelty": 0.9,
            "cost": 0.9,
            "duplicate": 0.8,
            "overfit": 0.8,
            "foreign": 0.8,
        },
    }
    if mode not in modes:
        raise ValueError(f"Unknown taste policy mode: {mode}")
    return modes[mode]


def make_policy(mode: str = "balanced", beta: float = 1.0) -> TastePolicy:
    return TastePolicy(
        policy_id=f"taste_policy_{mode}_v0",
        beta=float(beta),
        mode=mode,
        weights=default_weights(mode),
        created_at=_now(),
    )


def load_candidates_jsonl(path: Path) -> list[DiscoveryCandidate]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(candidate_from_dict(json.loads(line)))
    return rows


def candidate_from_dict(data: Mapping[str, Any]) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id=str(data.get("candidate_id", "")),
        candidate_type=str(data.get("candidate_type", "")),
        source=str(data.get("source", "")),
        source_kind=str(data.get("source_kind", "")),
        source_ref=str(data.get("source_ref", "")),
        title=str(data.get("title", "")),
        description=str(data.get("description", "")),
        mode_hint=str(data.get("mode_hint", "")),
        residual_cluster=str(data.get("residual_cluster", "")),
        basin=str(data.get("basin", "")),
        micro_basin=str(data.get("micro_basin", "")),
        suggested_route=str(data.get("suggested_route", "")),
        descension_target=str(data.get("descension_target", "")),
        expected_certificate_value=_float(data.get("expected_certificate_value")),
        expected_obstruction_value=_float(data.get("expected_obstruction_value")),
        expected_residual_compression=_float(data.get("expected_residual_compression")),
        expected_projection_gain=_float(data.get("expected_projection_gain")),
        expected_reuse=_float(data.get("expected_reuse")),
        expected_constructor_reuse=_float(data.get("expected_constructor_reuse")),
        expected_bridge_value=_float(data.get("expected_bridge_value")),
        novelty_score=_float(data.get("novelty_score")),
        verification_cost=_float(data.get("verification_cost")),
        duplicate_risk=_float(data.get("duplicate_risk")),
        overfit_risk=_float(data.get("overfit_risk")),
        foreign_moisture_risk=_float(data.get("foreign_moisture_risk")),
        trust_status=str(data.get("trust_status", "")),
        advisory_only=_truthy(data.get("advisory_only", True)),
        can_promote_truth=_truthy(data.get("can_promote_truth", False)),
        notes=str(data.get("notes", "")),
    )


def fallback_demo_candidates() -> list[DiscoveryCandidate]:
    return [
        DiscoveryCandidate(
            candidate_id="sair_residual_countermodel",
            candidate_type="finite_countermodel",
            source="sair_stage2",
            title="SAIR residual finite countermodel attempt",
            residual_cluster="sair_false_frontier",
            basin="finite_witness_gap",
            suggested_route="finite checker replay",
            descension_target="finite_countermodel_attempt",
            expected_certificate_value=0.95,
            expected_residual_compression=0.55,
            expected_reuse=0.7,
            verification_cost=0.25,
            duplicate_risk=0.1,
        ),
        DiscoveryCandidate(
            candidate_id="lean_sorry_repair",
            candidate_type="lean_digest",
            source="lean_project_digest",
            title="Lean digest sorry repair candidate",
            residual_cluster="incomplete_proof",
            suggested_route="Lean verifier contact",
            descension_target="lean_verifier_contact_candidate",
            expected_certificate_value=0.55,
            expected_projection_gain=0.25,
            expected_reuse=0.45,
            novelty_score=0.25,
            verification_cost=0.4,
            overfit_risk=0.1,
        ),
        DiscoveryCandidate(
            candidate_id="crossworld_projection_test",
            candidate_type="projection",
            source="cross_world_semantic_residual_invariant",
            title="CrossWorld semantic invariant projection test",
            residual_cluster="semantic_residual_rank",
            suggested_route="projection replay",
            descension_target="projection_test",
            expected_obstruction_value=0.55,
            expected_residual_compression=0.75,
            expected_projection_gain=0.95,
            expected_reuse=0.75,
            novelty_score=0.7,
            verification_cost=0.35,
        ),
        DiscoveryCandidate(
            candidate_id="collatz_obstruction_name",
            candidate_type="obstruction",
            source="collatz_primitive_divisor_v12_2",
            title="Collatz primitive divisor obstruction naming",
            residual_cluster="not_a_proof",
            basin="primitive_divisor_growth",
            suggested_route="obstruction law candidate",
            descension_target="obstruction_naming_attempt",
            expected_obstruction_value=0.9,
            expected_residual_compression=0.65,
            expected_projection_gain=0.35,
            novelty_score=0.6,
            verification_cost=0.3,
            notes="not_a_proof; advisory obstruction candidate",
        ),
        DiscoveryCandidate(
            candidate_id="fantasy_without_descension",
            candidate_type="fantasy",
            source="invalid_demo",
            title="Invalid no-descension idea",
            expected_projection_gain=1.0,
            novelty_score=1.0,
            verification_cost=0.0,
            notes="No descension target, no attention.",
        ),
        DiscoveryCandidate(
            candidate_id="truth_promotion_attempt",
            candidate_type="invalid_boundary",
            source="invalid_demo",
            title="Invalid truth promotion attempt",
            descension_target="reason_atlas_route_test",
            expected_certificate_value=1.0,
            can_promote_truth=True,
            notes="Malformed candidate attempting truth promotion.",
        ),
    ]


def validate_candidate(candidate: DiscoveryCandidate) -> tuple[bool, list[str]]:
    violations = []
    if not candidate.candidate_id:
        violations.append("missing_candidate_id")
    if candidate.descension_target not in ALLOWED_DESCENSION_TARGETS:
        violations.append("invalid_or_missing_descension_target")
    if not candidate.advisory_only:
        violations.append("non_advisory_candidate")
    if candidate.can_promote_truth:
        violations.append("can_promote_truth_true")
    if candidate.verification_cost < 0:
        violations.append("negative_verification_cost")
    forbidden = f"{candidate.suggested_route} {candidate.notes}".lower()
    if "verified_proof" in forbidden or "route_score_to_truth" in forbidden or "failed_search_to_true" in forbidden:
        violations.append("trust_boundary_violation_field")
    return not violations, violations


def score_candidate(candidate: DiscoveryCandidate, policy: TastePolicy) -> float:
    w = policy.weights
    projection_value = candidate.expected_projection_gain + candidate.expected_bridge_value
    reuse_value = candidate.expected_reuse + candidate.expected_constructor_reuse
    return (
        w["certificate"] * candidate.expected_certificate_value
        + w["obstruction"] * candidate.expected_obstruction_value
        + w["compression"] * candidate.expected_residual_compression
        + w["projection"] * projection_value
        + w["reuse"] * reuse_value
        + w["novelty"] * candidate.novelty_score
        - w["cost"] * candidate.verification_cost
        - w["duplicate"] * candidate.duplicate_risk
        - w["overfit"] * candidate.overfit_risk
        - w["foreign"] * candidate.foreign_moisture_risk
    )


def allocate_attention(candidates: Sequence[DiscoveryCandidate], policy: TastePolicy, top_k: int) -> tuple[list[DiscoveryCandidate], list[DiscoveryCandidate], list[dict[str, Any]]]:
    eligible: list[DiscoveryCandidate] = []
    invalid_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        ok, violations = validate_candidate(candidate)
        if ok:
            eligible.append(candidate)
        else:
            row = candidate.to_dict()
            row["violations"] = "|".join(violations)
            eligible_flag = False
            row["eligible"] = eligible_flag
            invalid_rows.append(row)
    if not eligible:
        return [], [], invalid_rows
    scores = [score_candidate(candidate, policy) for candidate in eligible]
    probs = _softmax(scores, beta=policy.beta)
    ranked = [
        _replace(candidate, taste_score=score, attention_probability=prob)
        for candidate, score, prob in zip(eligible, scores, probs)
    ]
    ranked.sort(key=lambda c: (-c.attention_probability, -c.taste_score, c.candidate_id))
    selected_ids = {candidate.candidate_id for candidate in ranked[: max(0, top_k)]}
    ranked = [_replace(candidate, chosen=candidate.candidate_id in selected_ids) for candidate in ranked]
    selected = [candidate for candidate in ranked if candidate.chosen]
    return ranked, selected, invalid_rows


def run_discovery_scheduler(
    out_dir: str | Path,
    *,
    candidates: Sequence[DiscoveryCandidate] | None = None,
    candidates_jsonl: str | Path | None = None,
    fallback_demo: bool = False,
    mode: str = "balanced",
    beta: float = 1.0,
    top_k: int = 5,
) -> DiscoveryRunResult:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    if candidates is not None:
        candidate_list = list(candidates)
    elif candidates_jsonl:
        candidate_list = load_candidates_jsonl(Path(candidates_jsonl))
    elif fallback_demo:
        candidate_list = fallback_demo_candidates()
    else:
        candidate_list = []
    policy = make_policy(mode=mode, beta=beta)
    ranked, selected, invalid_rows = allocate_attention(candidate_list, policy, top_k=top_k)
    all_rows = [candidate.to_dict() for candidate in candidate_list]
    ranked_rows = [candidate.to_dict() for candidate in ranked]
    selected_rows = [candidate.to_dict() for candidate in selected]
    audit = build_trust_boundary_audit(candidate_list, invalid_rows)
    run_id = f"discovery_scheduler_{mode}_{_now_compact()}"
    outputs = {
        "discovery_candidates": str(output / "discovery_candidates.csv"),
        "ranked_attention": str(output / "ranked_attention.csv"),
        "selected_attention": str(output / "selected_attention.csv"),
        "invalid_candidates": str(output / "invalid_candidates.csv"),
        "taste_policy": str(output / "taste_policy.json"),
        "trust_boundary_audit": str(output / "trust_boundary_audit.json"),
        "summary": str(output / "discovery_scheduler_summary.json"),
        "report": str(output / "discovery_scheduler_report.md"),
    }
    summary = {
        "run_id": run_id,
        "mode": mode,
        "beta": beta,
        "candidate_count": len(candidate_list),
        "eligible_count": len(ranked),
        "invalid_count": len(invalid_rows),
        "chosen_count": len(selected),
        "advisory_boundary_ok": audit["advisory_boundary_ok"],
        "can_promote_truth_count": audit["can_promote_truth_count"],
        "invalid_descension_count": audit["invalid_descension_count"],
        "top_candidate_id": ranked[0].candidate_id if ranked else "",
        "top_candidate_descension_target": ranked[0].descension_target if ranked else "",
        "total_attention_probability": sum(candidate.attention_probability for candidate in ranked),
        "outputs": outputs,
    }
    _write_csv(output / "discovery_candidates.csv", all_rows)
    _write_csv(output / "ranked_attention.csv", ranked_rows)
    _write_csv(output / "selected_attention.csv", selected_rows)
    _write_csv(output / "invalid_candidates.csv", invalid_rows)
    (output / "taste_policy.json").write_text(json.dumps(policy.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    (output / "trust_boundary_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    (output / "discovery_scheduler_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (output / "discovery_scheduler_report.md").write_text(_markdown(summary, ranked, selected, invalid_rows, audit), encoding="utf-8")
    return DiscoveryRunResult(
        run_id=run_id,
        policy_id=policy.policy_id,
        candidate_count=len(candidate_list),
        eligible_count=len(ranked),
        chosen_count=len(selected),
        advisory_boundary_ok=bool(audit["advisory_boundary_ok"]),
        can_promote_truth_count=int(audit["can_promote_truth_count"]),
        outputs=outputs,
    )


def build_trust_boundary_audit(candidates: Sequence[DiscoveryCandidate], invalid_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    violations = []
    for row in invalid_rows:
        for reason in str(row.get("violations", "")).split("|"):
            if reason:
                violations.append({"candidate_id": row.get("candidate_id", ""), "reason": reason})
    can_promote = sum(1 for candidate in candidates if candidate.can_promote_truth)
    non_advisory = sum(1 for candidate in candidates if not candidate.advisory_only)
    invalid_descension = sum(1 for candidate in candidates if candidate.descension_target not in ALLOWED_DESCENSION_TARGETS)
    return {
        "advisory_boundary_ok": can_promote == 0 and non_advisory == 0,
        "can_promote_truth_count": can_promote,
        "invalid_descension_count": invalid_descension,
        "non_advisory_count": non_advisory,
        "violations": violations,
        "statement": "DiscoveryScheduler is advisory only. It allocates attention to testable continuation candidates but cannot promote truth.",
    }


def _softmax(scores: Sequence[float], beta: float) -> list[float]:
    if not scores:
        return []
    scaled = [float(beta) * score for score in scores]
    shift = max(scaled)
    exps = [math.exp(value - shift) for value in scaled]
    total = sum(exps)
    if total <= 0:
        return [1.0 / len(scores) for _ in scores]
    return [value / total for value in exps]


def _replace(candidate: DiscoveryCandidate, **updates: Any) -> DiscoveryCandidate:
    data = candidate.to_dict()
    data.update(updates)
    return DiscoveryCandidate(**data)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in keys})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, sort_keys=True)
    return value


def _float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _markdown(
    summary: Mapping[str, Any],
    ranked: Sequence[DiscoveryCandidate],
    selected: Sequence[DiscoveryCandidate],
    invalid_rows: Sequence[Mapping[str, Any]],
    audit: Mapping[str, Any],
) -> str:
    lines = [
        "# DiscoveryScheduler v0: Taste Policy Ledger",
        "",
        "Curiosity finds pressure. Taste chooses continuation. Attention spends verification. Discovery compresses the residual.",
        "",
        "This scheduler ranks testable continuation candidates and allocates advisory attention. It is not H-tilt math, theorem proving, proof synthesis, or an autonomous discovery engine.",
        "",
        "No descension target, no attention.",
        "",
        f"- mode: `{summary.get('mode')}`",
        f"- beta: `{summary.get('beta')}`",
        f"- candidate_count: `{summary.get('candidate_count')}`",
        f"- eligible_count: `{summary.get('eligible_count')}`",
        f"- invalid_count: `{summary.get('invalid_count')}`",
        f"- chosen_count: `{summary.get('chosen_count')}`",
        f"- advisory_boundary_ok: `{summary.get('advisory_boundary_ok')}`",
        "",
        "## Top Candidates",
    ]
    for candidate in ranked[:5]:
        lines.append(
            f"- `{candidate.candidate_id}` score `{candidate.taste_score:.3f}` "
            f"p `{candidate.attention_probability:.3f}` target `{candidate.descension_target}`"
        )
    lines.extend(["", "## Invalid Candidates"])
    for row in invalid_rows:
        lines.append(f"- `{row.get('candidate_id')}`: `{row.get('violations')}`")
    if not invalid_rows:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Trust Boundary",
            "",
            str(audit.get("statement")),
            "The scheduler cannot promote TRUE/FALSE, cannot produce VERIFIED_PROOF, cannot turn failed search into TRUE, and cannot turn route scores into certificates.",
            "",
            "## Next Verifier-Contact Actions",
        ]
    )
    for candidate in selected:
        lines.append(f"- `{candidate.candidate_id}` -> `{candidate.descension_target}` via `{candidate.suggested_route}`")
    if not selected:
        lines.append("- none")
    return "\n".join(lines) + "\n"
