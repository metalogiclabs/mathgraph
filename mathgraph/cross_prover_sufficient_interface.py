"""Candidate sufficient-interface projection for cross-prover transport.

This layer is deliberately distinct from exact semantic linking.  A projected
interface may be stronger than the source theorem.  Therefore the relation is
INTERFACE_IMPLIES_SOURCE_INSTANCE, never SAME_MEANING.

V1 recognizes a tiny pinned family from pvs_cad by formula shape, records which
context is discarded, emits a stronger reusable Lean interface, and emits a
Lean adapter proving that the interface suffices for a source-shaped theorem.
Native PVS replay is a separate promotion gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mathgraph.cross_prover_family_discovery import (
    extract_pvs_lemmas,
    extract_pvs_proved_formulas,
    normalize_surface,
)


RELATION_KIND = "INTERFACE_IMPLIES_SOURCE_INSTANCE"


@dataclass(frozen=True)
class SufficientInterfaceSpec:
    interface_id: str
    interface_theorem: str
    interface_statement: str
    interface_proof: str
    adapter_theorem: str
    adapter_statement: str
    adapter_proof: str
    discarded_context: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "interface_id": self.interface_id,
            "relation_kind": RELATION_KIND,
            "interface_theorem": self.interface_theorem,
            "interface_statement": self.interface_statement,
            "adapter_theorem": self.adapter_theorem,
            "adapter_statement": self.adapter_statement,
            "discarded_context": list(self.discarded_context),
        }


def _specs() -> dict[str, SufficientInterfaceSpec]:
    rows: list[tuple[str, SufficientInterfaceSpec]] = []

    def add(surface: str, spec: SufficientInterfaceSpec) -> None:
        rows.append((normalize_surface(surface), spec))

    add(
        "FORALL (x: nnreal, a: real): a = sqrt(x) AND a * a = x AND a > 1 IMPLIES x > 1",
        SufficientInterfaceSpec(
            "interface.square_identity_gt_one@1",
            "square_identity_gt_one_interface",
            "(a x : ℝ) : a * a = x ∧ a > 1 → x > 1",
            """by
  rintro ⟨hax, ha⟩
  nlinarith [sq_nonneg (a - 1)]""",
            "source_sqrt_from_interface",
            "(x a : ℝ) : a = Real.sqrt x ∧ a * a = x ∧ a > 1 → x > 1",
            """by
  intro h
  exact square_identity_gt_one_interface a x ⟨h.2.1, h.2.2⟩""",
            ("a = sqrt(x)", "x : nnreal range fact"),
        ),
    )
    add(
        "FORALL (x: real, l: list[real]): f(x) > x^2 AND member(x, l) AND length(l) = 3 IMPLIES f(x) > -1",
        SufficientInterfaceSpec(
            "interface.above_square_gt_neg_one@1",
            "above_square_gt_neg_one_interface",
            "(x u : ℝ) : u > x ^ 2 → u > -1",
            """by
  intro h
  nlinarith [sq_nonneg x]""",
            "source_fun_from_interface",
            "(f : ℝ → ℝ) (x : ℝ) (l : List ℝ) : f x > x ^ 2 ∧ x ∈ l ∧ l.length = 3 → f x > -1",
            """by
  intro h
  exact above_square_gt_neg_one_interface x (f x) h.1""",
            ("member(x,l)", "length(l)=3", "function identity beyond f(x)"),
        ),
    )
    add(
        "FORALL (x: real): (FORALL (z: real): g(z) <= 1) AND (x > 0 IMPLIES EXISTS (z: real): z * z = x) AND x > 2 IMPLIES x > 1",
        SufficientInterfaceSpec(
            "interface.gt_two_gt_one@1",
            "gt_two_gt_one_interface",
            "(x : ℝ) : x > 2 → x > 1",
            """by
  intro h
  linarith""",
            "source_skip_from_interface",
            "(g : ℝ → ℝ) (x : ℝ) : (∀ z : ℝ, g z ≤ 1) ∧ (x > 0 → ∃ z : ℝ, z * z = x) ∧ x > 2 → x > 1",
            """by
  intro h
  exact gt_two_gt_one_interface x h.2.2""",
            ("∀z, g(z)≤1", "x>0 -> ∃z, z*z=x"),
        ),
    )
    add(
        "FORALL (x: real, l: list[real]): P(x) AND cons?(l) AND (FORALL (z: real): f(z) >= 0) AND f(x) > x^2 AND x /= 0 IMPLIES f(x) > 0",
        SufficientInterfaceSpec(
            "interface.above_nonzero_square_positive@1",
            "above_nonzero_square_positive_interface",
            "(x u : ℝ) : u > x ^ 2 ∧ x ≠ 0 → u > 0",
            """by
  rintro ⟨hu, hx⟩
  have hx2 : 0 < x ^ 2 := sq_pos_of_ne_zero hx
  nlinarith""",
            "source_mix_from_interface",
            "(P : ℝ → Prop) (Q : List ℝ → Prop) (f : ℝ → ℝ) (x : ℝ) (l : List ℝ) : P x ∧ Q l ∧ (∀ z : ℝ, f z ≥ 0) ∧ f x > x ^ 2 ∧ x ≠ 0 → f x > 0",
            """by
  intro h
  exact above_nonzero_square_positive_interface x (f x) ⟨h.2.2.2.1, h.2.2.2.2⟩""",
            ("P(x)", "cons?(l)", "∀z, f(z)≥0"),
        ),
    )
    # V2 extension: subtype/range erasure.  These are not SAME_MEANING
    # claims unless the source subtype interpretation is carried explicitly.
    # We therefore retain them as stronger real-valued interfaces plus typed
    # Lean adapters for the corresponding source-shaped subtype statements.
    add(
        "FORALL (x: posreal): x + 1 > 1",
        SufficientInterfaceSpec(
            "interface.positive_add_one_gt_one@1",
            "positive_add_one_gt_one_interface",
            "(x : ℝ) : x > 0 → x + 1 > 1",
            """by
  intro hx
  linarith""",
            "source_posreal_from_interface",
            "(x : {x : ℝ // 0 < x}) : (x : ℝ) + 1 > 1",
            """by
  exact positive_add_one_gt_one_interface (x : ℝ) x.2""",
            ("PVS posreal subtype wrapper",),
        ),
    )
    add(
        "FORALL (y: nnreal): sqrt(y) + 1 >= 1",
        SufficientInterfaceSpec(
            "interface.sqrt_add_one_ge_one@1",
            "sqrt_add_one_ge_one_interface",
            "(y : ℝ) : Real.sqrt y + 1 ≥ 1",
            """by
  have h := Real.sqrt_nonneg y
  linarith""",
            "source_nnreal_sqrt_from_interface",
            "(y : NNReal) : Real.sqrt (y : ℝ) + 1 ≥ 1",
            """by
  exact sqrt_add_one_ge_one_interface (y : ℝ)""",
            ("PVS nnreal subtype wrapper",),
        ),
    )

    return dict(rows)


SPECS = _specs()


def discover_sufficient_interfaces(
    sources: Mapping[str, str],
    proofs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    proved = {
        theory: extract_pvs_proved_formulas(text)
        for theory, text in (proofs or {}).items()
    }

    for theory, source in sorted(sources.items()):
        for formula, surface in extract_pvs_lemmas(source):
            spec = SPECS.get(surface)
            if spec is None:
                continue
            proof_status = None
            if proofs is not None:
                proof_status = (
                    "PINNED_PROOF_PRESENT"
                    if formula in proved.get(theory, set())
                    else "NO_PINNED_PROOF"
                )
            rows.append({
                "theory": theory,
                "formula": formula,
                "normalized_surface": surface,
                "source_proof_status": proof_status,
                "status": "CANDIDATE_SUFFICIENT_INTERFACE",
                **spec.to_dict(),
            })

    return {
        "schema": "mathgraph.cross-prover-sufficient-interface-discovery.v1",
        "status": "CANDIDATE_ONLY",
        "relation_kind": RELATION_KIND,
        "candidate_count": len(rows),
        "source_authority_candidate_count": sum(
            1 for row in rows
            if row["source_proof_status"] in (None, "PINNED_PROOF_PRESENT")
        ),
        "candidates": rows,
        "boundary": (
            "The interface is a verified stronger sufficient rule, not an "
            "equivalent canonical meaning. Pinned proof-file presence is routing "
            "metadata only until native PVS replay."
        ),
    }


def render_lean_projection(discovery: Mapping[str, Any]) -> str:
    chunks = [
        "import Mathlib",
        "",
        "namespace CrystalCrossProverMSIProjection",
        "",
    ]
    seen: set[str] = set()
    for row in discovery["candidates"]:
        interface_id = str(row["interface_id"])
        if interface_id in seen:
            continue
        seen.add(interface_id)
        spec = next(x for x in SPECS.values() if x.interface_id == interface_id)
        chunks.extend([
            f"theorem {spec.interface_theorem} {spec.interface_statement} := {spec.interface_proof}",
            "",
            f"theorem {spec.adapter_theorem} {spec.adapter_statement} := {spec.adapter_proof}",
            "",
        ])
    chunks.append("end CrystalCrossProverMSIProjection")
    return "\n".join(chunks) + "\n"
