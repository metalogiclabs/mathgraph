"""Evidence-derived candidate generation for DiscoveryScheduler v1.

This module converts repo-native evidence packs and optional Lean digest outputs
into advisory continuation candidates.  It does not prove, certify, or promote
truth; it only creates testable descension targets for the scheduler.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.core_v0 import CoreGraph, Relation, Status
from mathgraph.discovery_scheduler import DiscoveryCandidate, validate_candidate
from mathgraph.evidence_packs import EvidencePackError, load_evidence_pack


CANONICAL_EVIDENCE_PACKS = (
    "sair_stage2_breakthrough_20260526",
    "recursive_residual_transfer_v1_20260523",
    "cross_world_semantic_residual_invariant",
    "residual_obstruction_atlas_v8_4",
    "root_node_persistent_filtration_v16_3",
    "collatz_primitive_divisor_v12_2",
)


@dataclass(frozen=True)
class CandidateSourceResult:
    candidates: tuple[DiscoveryCandidate, ...]
    rejected_rows: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    source_counts: dict[str, int] = field(default_factory=dict)

    @property
    def valid_candidates(self) -> tuple[DiscoveryCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if validate_candidate(candidate)[0])


def collect_discovery_candidates_from_sources(
    *,
    evidence_root: str | Path,
    lean_digest_dir: str | Path | None = None,
    lean_lawbook_dir: str | Path | None = None,
    lean_attention_dir: str | Path | None = None,
) -> CandidateSourceResult:
    """Collect advisory candidates from evidence packs and optional Lean outputs."""

    candidates: list[DiscoveryCandidate] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[str] = []
    counts: dict[str, int] = {}

    evidence_candidates, evidence_rejected, evidence_warnings = candidates_from_evidence_packs(evidence_root)
    candidates.extend(evidence_candidates)
    rejected.extend(evidence_rejected)
    warnings.extend(evidence_warnings)
    _count_by_source_kind(counts, evidence_candidates)

    for label, directory, loader in (
        ("lean_digest", lean_digest_dir, candidates_from_lean_digest_dir),
        ("lean_lawbook", lean_lawbook_dir, candidates_from_lean_lawbook_dir),
        ("lean_attention", lean_attention_dir, candidates_from_lean_attention_dir),
    ):
        if directory is None:
            continue
        try:
            rows = loader(Path(directory))
            candidates.extend(rows)
            counts[label] = counts.get(label, 0) + len(rows)
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"{label}: {exc}")
            rejected.append(_rejected_source_row(label, str(directory), str(exc)))

    normalized = tuple(_force_boundary(candidate) for candidate in candidates)
    invalid_rows = list(rejected)
    for candidate in normalized:
        ok, violations = validate_candidate(candidate)
        if not ok:
            row = candidate.to_dict()
            row["violations"] = "|".join(violations)
            row["eligible"] = False
            invalid_rows.append(row)
    return CandidateSourceResult(
        candidates=normalized,
        rejected_rows=tuple(invalid_rows),
        warnings=tuple(warnings),
        source_counts=counts,
    )



def candidates_from_core_v0_graph(
    graph: CoreGraph,
    *,
    source_ref: str = "mathgraph-core-v0",
) -> list[DiscoveryCandidate]:
    """Emit advisory scheduler candidates from an exact closed Core V0 snapshot.

    The adapter closes a round-tripped copy, so it never mutates the caller's
    graph. Subjects already resolved as WARRANTED, REJECTED, or SUPERSEDED are
    omitted. The remaining frontier is bound to the SHA-256 digest of the
    closed .mg snapshot that produced it.

    This is routing only: it cannot create warrants or promote truth.
    """

    if not isinstance(graph, CoreGraph):
        raise TypeError("graph must be a CoreGraph")

    closed = CoreGraph.from_mg(graph.to_mg())
    closed.close()
    snapshot = closed.to_mg()
    snapshot_ref = f"{source_ref}@sha256:{hashlib.sha256(snapshot).hexdigest()}"

    subjects: list[tuple[str, str, object]] = []
    subjects.extend(("object", subject_id, subject) for subject_id, subject in closed.objects.items())
    subjects.extend(("relation", subject_id, subject) for subject_id, subject in closed.relations.items())
    subjects.extend(("unknown", subject_id, subject) for subject_id, subject in closed.unknowns.items())

    candidates: list[DiscoveryCandidate] = []
    resolved = {Status.WARRANTED, Status.REJECTED, Status.SUPERSEDED}
    for subject_kind, subject_id, subject in sorted(subjects, key=lambda row: (row[0], row[1])):
        status = closed.status_of(subject_id)
        if status in resolved:
            continue

        if status is Status.CONFLICTED:
            descension_target = "trust_audit"
            suggested_route = "inspect conflicting active warrants and support lineage"
            candidate_type = "core_v0_conflict_candidate"
        elif status is Status.REVOKED:
            descension_target = "evidence_replay"
            suggested_route = "replay or replace revoked support"
            candidate_type = "core_v0_revoked_candidate"
        elif subject_kind == "unknown":
            descension_target = "representation_repair"
            suggested_route = "expand or repair the normalization grammar, or contact an external verifier"
            candidate_type = "core_v0_unknown_grammar_candidate"
        else:
            descension_target = "verifier_contact"
            suggested_route = "contact an external verifier through an explicit adapter boundary"
            if subject_kind == "relation" and isinstance(subject, Relation):
                candidate_type = f"core_v0_{subject.kind.value.lower()}_candidate"
            else:
                candidate_type = "core_v0_object_candidate"

        candidates.append(
            DiscoveryCandidate(
                candidate_id=f"core_v0_{subject_kind}_{subject_id.replace(':', '_')}",
                candidate_type=candidate_type,
                source="mathgraph_core_v0",
                source_kind="core_v0_graph",
                source_ref=snapshot_ref,
                title=f"Core V0 {subject_kind} residual",
                description=(
                    f"{subject_kind} {subject_id} remains {status.value} after deterministic "
                    "Core V0 closure."
                ),
                mode_hint="frontier",
                residual_cluster=subject_id,
                basin=subject_kind,
                suggested_route=suggested_route,
                descension_target=descension_target,
                trust_status=f"core_v0_{status.value.lower()}",
                notes=(
                    "Derived from an exact content-addressed Core V0 snapshot. "
                    "Advisory routing only; verification must return through an explicit "
                    "verifier boundary before MathGraph can admit a warrant."
                ),
                advisory_only=True,
                can_promote_truth=False,
            )
        )
    return candidates


def candidates_from_evidence_packs(evidence_root: str | Path) -> tuple[list[DiscoveryCandidate], list[dict[str, Any]], list[str]]:
    candidates: list[DiscoveryCandidate] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[str] = []
    root = Path(evidence_root)
    for pack_id in CANONICAL_EVIDENCE_PACKS:
        pack_dir = root / pack_id
        if not pack_dir.exists():
            message = f"missing evidence pack: {pack_id}"
            warnings.append(message)
            rejected.append(_rejected_source_row("evidence_pack", pack_id, message))
            continue
        try:
            pack = load_evidence_pack(pack_dir)
        except (FileNotFoundError, EvidencePackError, json.JSONDecodeError) as exc:
            message = f"malformed evidence pack {pack_id}: {exc}"
            warnings.append(message)
            rejected.append(_rejected_source_row("evidence_pack", pack_id, message))
            continue
        candidates.append(_candidate_from_pack(pack_id, pack.metrics, pack.manifest))
    return candidates, rejected, warnings


def candidates_from_lean_digest_dir(digest_dir: Path) -> list[DiscoveryCandidate]:
    rows = _read_csv_optional(digest_dir / "declaration_inventory.csv")
    routes = _read_csv_optional(digest_dir / "reason_atlas_routes.csv")
    return _candidates_from_lean_declarations(rows, digest_dir, "lean_digest") + _candidates_from_lean_routes(routes, digest_dir, "lean_digest")


def candidates_from_lean_lawbook_dir(lawbook_dir: Path) -> list[DiscoveryCandidate]:
    rows = _read_csv_optional(lawbook_dir / "imported_declarations.csv")
    routes = _read_csv_optional(lawbook_dir / "imported_reason_routes.csv")
    return _candidates_from_lean_declarations(rows, lawbook_dir, "lean_lawbook") + _candidates_from_lean_routes(routes, lawbook_dir, "lean_lawbook")


def candidates_from_lean_attention_dir(attention_dir: Path) -> list[DiscoveryCandidate]:
    rows = _read_csv_optional(attention_dir / "attention_results.csv")
    candidates: list[DiscoveryCandidate] = []
    for row in rows:
        score = _float(row.get("attention_score"))
        route = str(row.get("route_suggestion") or "textual_digest_review_route")
        name = str(row.get("name") or row.get("declaration_id") or "lean_attention_result")
        candidates.append(
            DiscoveryCandidate(
                candidate_id=_candidate_id("lean_attention_route_candidate", name, row.get("query_id", "")),
                candidate_type="lean_attention_route_candidate",
                source="lean_lawbook_attention",
                source_kind="lean_attention",
                source_ref=str(attention_dir),
                title=f"Lean attention route test: {name}",
                description="Convert a high-scoring textual Lean attention result into a verifier-contact route test.",
                mode_hint="harvest",
                suggested_route=route,
                descension_target="reason_atlas_route_test",
                expected_certificate_value=0.25 if "sorry" not in route else 0.45,
                expected_obstruction_value=0.35 if "axiom" in route or "unsafe" in route else 0.15,
                expected_residual_compression=min(0.6, 0.2 + score / 5.0),
                expected_constructor_reuse=min(0.7, score / 5.0),
                expected_bridge_value=0.35,
                novelty_score=0.2,
                verification_cost=0.35,
                duplicate_risk=0.2,
                overfit_risk=0.1,
                trust_status=str(row.get("trust_status", "textual_digest_attention")),
                notes="Textual Lean attention is advisory routing only; it cannot become VERIFIED_PROOF.",
            )
        )
    return candidates


def split_valid_candidates(candidates: Sequence[DiscoveryCandidate]) -> tuple[list[DiscoveryCandidate], list[dict[str, Any]]]:
    valid: list[DiscoveryCandidate] = []
    rejected: list[dict[str, Any]] = []
    for candidate in candidates:
        ok, violations = validate_candidate(candidate)
        if ok:
            valid.append(candidate)
        else:
            row = candidate.to_dict()
            row["violations"] = "|".join(violations)
            row["eligible"] = False
            rejected.append(row)
    return valid, rejected


def _candidate_from_pack(pack_id: str, metrics: Mapping[str, Any], manifest: Mapping[str, Any]) -> DiscoveryCandidate:
    common = {
        "source": pack_id,
        "source_kind": "evidence_pack",
        "source_ref": pack_id,
        "advisory_only": True,
        "can_promote_truth": False,
    }
    if pack_id == "sair_stage2_breakthrough_20260526":
        return DiscoveryCandidate(
            candidate_id="sair_countermodel_frontier_candidate",
            candidate_type="sair_countermodel_frontier_candidate",
            title="SAIR finite-countermodel frontier replay",
            description="Use official finite-checked FALSE certificate evidence to focus a bounded countermodel attempt.",
            mode_hint="harvest",
            residual_cluster="sair_finite_countermodel_frontier",
            basin="accepted_false_certificates",
            suggested_route="finite checker replay and nearby frontier sampling",
            descension_target="finite_countermodel_attempt",
            expected_certificate_value=0.9,
            expected_obstruction_value=0.4,
            expected_residual_compression=0.45,
            expected_constructor_reuse=0.65,
            verification_cost=0.35,
            duplicate_risk=0.15,
            trust_status="finite_checked_false_certificate_pack",
            notes="Finite-checked FALSE certificates are terminal only for checked witnesses; advisory routes stay separate.",
            **common,
        )
    if pack_id == "recursive_residual_transfer_v1_20260523":
        gain = _float(metrics.get("compact_transfer_gain_vs_generic_positive"))
        return DiscoveryCandidate(
            candidate_id="recursive_transfer_replay_candidate",
            candidate_type="recursive_transfer_replay_candidate",
            title="Recursive residual transfer replay validation",
            description="Replay transferable constructor-memory evidence against a small bounded benchmark slice.",
            mode_hint="harvest",
            residual_cluster="transferable_constructor_memory",
            basin="compact_atlas",
            suggested_route="frozen evidence replay and route-memory comparison",
            descension_target="replay_validation",
            expected_certificate_value=0.25,
            expected_obstruction_value=0.35,
            expected_residual_compression=0.75,
            expected_constructor_reuse=min(0.95, 0.45 + gain / 500.0),
            expected_bridge_value=0.35,
            novelty_score=0.35,
            verification_cost=0.25,
            duplicate_risk=0.25,
            trust_status="advisory_route_memory",
            notes="Transferable, compressible advisory route memory; not terminal truth and not a certificate.",
            **common,
        )
    if pack_id == "cross_world_semantic_residual_invariant":
        return DiscoveryCandidate(
            candidate_id="crossworld_projection_test_candidate",
            candidate_type="crossworld_projection_test_candidate",
            title="CrossWorld semantic residual projection test",
            description="Project the empirical semantic residual invariant into a new bounded verifier-contact task.",
            mode_hint="architectonic",
            residual_cluster="semantic_residual_independence_after_source_closure",
            basin="cross_world_projection",
            suggested_route="semantic residual projection test",
            descension_target="projection_test",
            expected_certificate_value=0.25,
            expected_obstruction_value=0.65,
            expected_residual_compression=0.7,
            expected_projection_gain=0.8,
            expected_bridge_value=0.9,
            expected_constructor_reuse=0.45,
            novelty_score=0.7,
            verification_cost=0.45,
            duplicate_risk=0.1,
            overfit_risk=0.2,
            trust_status="empirical_cross_world_invariant_candidate",
            notes="Empirical invariant candidate, not a formal theorem and not a truth oracle; absorbed/rank-zero remains a proof-route candidate only unless verified.",
            **common,
        )
    if pack_id == "residual_obstruction_atlas_v8_4":
        return DiscoveryCandidate(
            candidate_id="residual_obstruction_split_candidate",
            candidate_type="residual_obstruction_split_candidate",
            title="Residual obstruction frontier split",
            description="Use the v8.4 residual atlas to split remaining frontier into obstruction-naming and witness-universe expansion tests.",
            mode_hint="frontier",
            residual_cluster="residual_zero_incomplete_witness_universe",
            basin="remaining_false_frontier",
            suggested_route="semantic universe expansion and minimum-carrier search",
            descension_target="obstruction_naming_attempt",
            expected_certificate_value=0.35,
            expected_obstruction_value=0.9,
            expected_residual_compression=0.85,
            expected_projection_gain=0.45,
            expected_bridge_value=0.55,
            novelty_score=0.55,
            verification_cost=0.4,
            duplicate_risk=0.15,
            trust_status="residual_obstruction_frontier",
            notes="Residual-zero means incomplete witness universe, not failed invariant and not TRUE.",
            **common,
        )
    if pack_id == "root_node_persistent_filtration_v16_3":
        return DiscoveryCandidate(
            candidate_id="root_node_projection_candidate",
            candidate_type="root_node_projection_candidate",
            title="Persistent root-node projection test",
            description="Project persistent load-bearing root-node evidence into a constructor/yield continuation test.",
            mode_hint="architectonic",
            residual_cluster="persistent_load_bearing_root",
            basin="root_node_filtration",
            suggested_route="root-node projection and constructor-yield test",
            descension_target="projection_test",
            expected_certificate_value=0.3,
            expected_obstruction_value=0.55,
            expected_residual_compression=0.75,
            expected_projection_gain=0.75,
            expected_constructor_reuse=0.8,
            expected_bridge_value=0.8,
            novelty_score=0.45,
            verification_cost=0.35,
            duplicate_risk=0.25,
            trust_status="persistent_load_bearing_candidate",
            notes="Root nodes are persistence/load-bearing/null-resistance candidates, not clusters promoted to truth.",
            **common,
        )
    if pack_id == "collatz_primitive_divisor_v12_2":
        return DiscoveryCandidate(
            candidate_id="collatz_obstruction_naming_candidate",
            candidate_type="collatz_obstruction_naming_candidate",
            title="Collatz primitive-divisor obstruction naming",
            description="Convert v12.2 primitive-divisor growth evidence into a proof-template/obstruction-law obligation.",
            mode_hint="frontier",
            residual_cluster="UNCANCELLED_PRIMITIVE_DIVISOR_GROWTH",
            basin="primitive_divisor_growth",
            suggested_route="obstruction naming and exact lemma extraction",
            descension_target="obstruction_naming_attempt",
            expected_certificate_value=0.05,
            expected_obstruction_value=0.95,
            expected_residual_compression=0.8,
            expected_projection_gain=0.35,
            expected_bridge_value=0.45,
            novelty_score=0.65,
            verification_cost=0.45,
            duplicate_risk=0.1,
            trust_status="not_a_proof_obstruction_candidate",
            notes="not_a_proof; proof-template candidate only; zero integer candidates do not prove Collatz.",
            **common,
        )
    return DiscoveryCandidate(
        candidate_id=_candidate_id("unknown_evidence_pack_candidate", pack_id),
        candidate_type="unknown_evidence_pack_candidate",
        title=f"Evidence replay for {pack_id}",
        descension_target="evidence_replay",
        verification_cost=0.5,
        trust_status="unknown_evidence_pack",
        notes=f"Generated from manifest keys: {','.join(sorted(manifest)[:5])}",
        **common,
    )


def _candidates_from_lean_declarations(rows: Sequence[Mapping[str, Any]], source_dir: Path, source_kind: str) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    for row in rows:
        name = str(row.get("name") or row.get("declaration_id") or "lean_declaration")
        trust = str(row.get("trust_status", ""))
        has_sorry = _truthy(row.get("has_sorry")) or _truthy(row.get("has_admit")) or trust == "incomplete_proof"
        has_axiom = _truthy(row.get("has_axiom")) or "axiom" in trust
        has_unsafe = _truthy(row.get("has_unsafe")) or "unsafe" in trust
        kind = str(row.get("declaration_kind", ""))
        if has_sorry:
            candidates.append(_lean_candidate(row, source_dir, source_kind, "lean_sorry_repair_candidate", "lean_digest_repair", 0.55, 0.25, 0.35, "Repair or replace incomplete textual Lean proof; verifier contact required."))
        elif has_axiom:
            candidates.append(_lean_candidate(row, source_dir, source_kind, "lean_axiom_boundary_candidate", "trust_audit", 0.05, 0.7, 0.2, "Axiom boundary audit; assumption is not proof."))
        elif has_unsafe:
            candidates.append(_lean_candidate(row, source_dir, source_kind, "lean_unsafe_audit_candidate", "trust_audit", 0.05, 0.65, 0.2, "Unsafe declaration audit; warning boundary required."))
        elif kind in {"theorem", "lemma", "def", "example"}:
            candidates.append(_lean_candidate(row, source_dir, source_kind, "lean_theorem_cluster_route_candidate", "reason_atlas_route_test", 0.35, 0.15, 0.45, "Textual imported declaration cluster route; cannot become VERIFIED_PROOF without Lean execution."))
    return candidates


def _candidates_from_lean_routes(rows: Sequence[Mapping[str, Any]], source_dir: Path, source_kind: str) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    for row in rows:
        route = str(row.get("route_type") or row.get("route_suggestion") or row.get("route") or "")
        name = str(row.get("name") or row.get("declaration_id") or route or "lean_route")
        if "import" in route:
            ctype = "lean_import_dependency_route_candidate"
        elif "axiom" in route:
            ctype = "lean_axiom_boundary_candidate"
        elif "unsafe" in route:
            ctype = "lean_unsafe_audit_candidate"
        elif "sorry" in route or "repair" in route:
            ctype = "lean_sorry_repair_candidate"
        else:
            ctype = "lean_theorem_cluster_route_candidate"
        candidates.append(
            DiscoveryCandidate(
                candidate_id=_candidate_id(ctype, name, route),
                candidate_type=ctype,
                source="lean_digest_routes",
                source_kind=source_kind,
                source_ref=str(source_dir),
                title=f"Lean route test: {name}",
                description=f"Route `{route}` from textual Lean digest memory.",
                mode_hint="harvest",
                suggested_route=route or ctype,
                descension_target="reason_atlas_route_test",
                expected_certificate_value=0.35 if "repair" in ctype or "cluster" in ctype else 0.05,
                expected_obstruction_value=0.65 if "axiom" in ctype or "unsafe" in ctype else 0.2,
                expected_residual_compression=0.3,
                expected_constructor_reuse=0.45,
                expected_bridge_value=0.25,
                novelty_score=0.25,
                verification_cost=0.35,
                duplicate_risk=0.25,
                trust_status=str(row.get("trust_status", "textual_digest_route")),
                notes="Textual Lean route suggestion is advisory only and cannot promote truth.",
            )
        )
    return candidates


def _lean_candidate(
    row: Mapping[str, Any],
    source_dir: Path,
    source_kind: str,
    candidate_type: str,
    descension_target: str,
    cert: float,
    obstruction: float,
    reuse: float,
    notes: str,
) -> DiscoveryCandidate:
    name = str(row.get("name") or row.get("declaration_id") or candidate_type)
    return DiscoveryCandidate(
        candidate_id=_candidate_id(candidate_type, name, row.get("file", ""), row.get("line", "")),
        candidate_type=candidate_type,
        source="lean_textual_digest",
        source_kind=source_kind,
        source_ref=str(source_dir),
        title=f"{candidate_type}: {name}",
        description=str(row.get("statement_text", "")),
        mode_hint="harvest",
        suggested_route=candidate_type,
        descension_target=descension_target,
        expected_certificate_value=cert,
        expected_obstruction_value=obstruction,
        expected_residual_compression=0.25,
        expected_constructor_reuse=reuse,
        expected_bridge_value=0.25,
        novelty_score=0.25,
        verification_cost=0.55 if "sorry" in candidate_type else 0.3,
        duplicate_risk=0.2,
        trust_status=str(row.get("trust_status", "textual_digest")),
        notes=f"{notes} Textual Lean digest entries cannot become VERIFIED_PROOF.",
    )


def _force_boundary(candidate: DiscoveryCandidate) -> DiscoveryCandidate:
    data = candidate.to_dict()
    data["advisory_only"] = True
    data["can_promote_truth"] = False
    return DiscoveryCandidate(**data)


def _count_by_source_kind(counts: dict[str, int], candidates: Sequence[DiscoveryCandidate]) -> None:
    for candidate in candidates:
        key = candidate.source_kind or candidate.source
        counts[key] = counts.get(key, 0) + 1


def _read_csv_optional(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _rejected_source_row(source_kind: str, source_ref: str, reason: str) -> dict[str, Any]:
    return {
        "candidate_id": "",
        "candidate_type": "source_warning",
        "source_kind": source_kind,
        "source_ref": source_ref,
        "violations": reason,
        "eligible": False,
    }


def _candidate_id(*parts: Any) -> str:
    text = "_".join(str(part) for part in parts if str(part))
    out = []
    for ch in text.lower():
        out.append(ch if ch.isalnum() else "_")
    collapsed = "_".join(part for part in "".join(out).split("_") if part)
    return collapsed[:140] or "candidate"


def _float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
