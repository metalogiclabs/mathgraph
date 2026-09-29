"""Residual-earned consequence projection certificates for cross-prover PVS→Lean linking.

This compiler handles only the eleven non-witness source surfaces left after the
existential witness family, excluding:
- d_no_inverse, whose semantic warrant is reused from the witness/refutation family;
- t_amgm3, which remains the exact final polynomial counterexample residual.

Several PVS surfaces contain opaque functions, list predicates, subtype facts or
quantified premises. Crystal compiles only the minimum consequence needed by the
consumer and independently checks it in Lean.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.crystal import SemanticObject, canonical_bytes
from mathgraph.cross_prover_family_discovery import normalize_surface


@dataclass(frozen=True)
class ProjectionSpec:
    claim_id: str
    certificate_schema: str
    theorem_name: str
    lean_statement: str
    lean_proof: str

    def to_dict(self) -> dict[str,Any]:
        return {
            "claim_id":self.claim_id,
            "certificate_schema":self.certificate_schema,
            "theorem_name":self.theorem_name,
            "lean_statement":self.lean_statement,
        }


def _specs() -> dict[str,ProjectionSpec]:
    rows: list[tuple[str,ProjectionSpec]]=[]
    def add(surface: str, spec: ProjectionSpec) -> None:
        rows.append((normalize_surface(surface),spec))

    add(
        "FORALL (x: nnreal, a: real): a = sqrt(x) AND a * a = x AND a > 1 IMPLIES x > 1",
        ProjectionSpec(
            "real.sqrt_square_projection@1","drop_opaque_sqrt_keep_square_relation",
            "sqrt_square_projection",
            "(x : ℝ≥0) (a : ℝ) : (a = Real.sqrt (x : ℝ) ∧ a * a = (x : ℝ) ∧ a > 1) → (x : ℝ) > 1",
            """by
  rintro ⟨-, hsq, ha⟩
  have hpos : 0 < a ^ 2 := sq_pos_of_ne_zero (by linarith)
  rw [pow_two] at hpos
  nlinarith""",
        ),
    )
    add(
        "FORALL (x: real, l: list[real]): f(x) > x^2 AND member(x, l) AND length(l) = 3 IMPLIES f(x) > -1",
        ProjectionSpec(
            "real.opaque_function_square_lower_bound@1","drop_list_context_keep_numeric_bound",
            "opaque_function_square_lower_bound",
            "(f : ℝ → ℝ) (x : ℝ) (l : List ℝ) : (f x > x ^ 2 ∧ x ∈ l ∧ l.length = 3) → f x > -1",
            """by
  rintro ⟨hfx, -, -⟩
  nlinarith [sq_nonneg x]""",
        ),
    )
    add(
        "FORALL (b: real): FORALL (c: real): (FORALL (z: real): z^2 + b * z + c > 0) IMPLIES b^2 < 4 * c",
        ProjectionSpec(
            "real.positive_quadratic_discriminant@1","critical_point_instantiation",
            "positive_quadratic_discriminant",
            "(b c : ℝ) : (∀ z : ℝ, z ^ 2 + b * z + c > 0) → b ^ 2 < 4 * c",
            """by
  intro h
  have hz := h (-b / 2)
  nlinarith""",
        ),
    )
    add(
        "FORALL (x: real): x > 0 IMPLIES EXISTS (y: real): y * y = x",
        ProjectionSpec(
            "real.positive_has_square_root@1","sqrt_witness",
            "positive_has_square_root",
            "(x : ℝ) : x > 0 → ∃ y : ℝ, y * y = x",
            """by
  intro hx
  refine ⟨Real.sqrt x, ?_⟩
  have hs := Real.sq_sqrt (le_of_lt hx)
  simpa [pow_two] using hs""",
        ),
    )
    add(
        "FORALL (a: real): a > 0 IMPLIES (FORALL (z: real): EXISTS (w: real): w * a > z)",
        ProjectionSpec(
            "real.positive_scale_unbounded@1","division_witness",
            "positive_scale_unbounded",
            "(a : ℝ) : a > 0 → ∀ z : ℝ, ∃ w : ℝ, w * a > z",
            """by
  intro ha z
  have ha0 : a ≠ 0 := ne_of_gt ha
  refine ⟨(z + 1) / a, ?_⟩
  have hcalc : ((z + 1) / a) * a = z + 1 := by
    field_simp
  linarith""",
        ),
    )
    add(
        "FORALL (c: real): (FORALL (z: real): EXISTS (w: real): w > z AND w * c > 1) IMPLIES c > 0",
        ProjectionSpec(
            "real.unbounded_product_forces_positive@1","single_quantifier_instantiation",
            "unbounded_product_forces_positive",
            "(c : ℝ) : (∀ z : ℝ, ∃ w : ℝ, w > z ∧ w * c > 1) → c > 0",
            """by
  intro h
  rcases h 0 with ⟨w, hw, hwc⟩
  by_contra hc
  have hc' : c ≤ 0 := le_of_not_gt hc
  have hprod : w * c ≤ 0 := mul_nonpos_of_nonneg_of_nonpos (by linarith) hc'
  linarith""",
        ),
    )
    add(
        "FORALL (x: posreal): x + 1 > 1",
        ProjectionSpec(
            "real.positive_subtype_shift@1","subtype_range_projection",
            "positive_subtype_shift",
            "(x : {x : ℝ // 0 < x}) : (x : ℝ) + 1 > 1",
            """by
  have hx : 0 < (x : ℝ) := x.property
  linarith""",
        ),
    )
    add(
        "FORALL (y: nnreal): sqrt(y) + 1 >= 1",
        ProjectionSpec(
            "real.sqrt_nonnegative_shift@1","range_fact_projection",
            "sqrt_nonnegative_shift",
            "(y : ℝ≥0) : Real.sqrt (y : ℝ) + 1 ≥ 1",
            """by
  have h := Real.sqrt_nonneg (y : ℝ)
  linarith""",
        ),
    )
    add(
        "FORALL (x: real): (FORALL (z: real): g(z) <= 1) AND (x > 0 IMPLIES EXISTS (z: real): z * z = x) AND x > 2 IMPLIES x > 1",
        ProjectionSpec(
            "real.skip_irrelevant_context@1","drop_irrelevant_conjuncts",
            "skip_irrelevant_context",
            "(g : ℝ → ℝ) (x : ℝ) : ((∀ z : ℝ, g z ≤ 1) ∧ (x > 0 → ∃ z : ℝ, z * z = x) ∧ x > 2) → x > 1",
            """by
  rintro ⟨-, -, hx⟩
  linarith""",
        ),
    )
    add(
        "FORALL (x: real, l: list[real]): P(x) AND cons?(l) AND (FORALL (z: real): f(z) >= 0) AND f(x) > x^2 AND x /= 0 IMPLIES f(x) > 0",
        ProjectionSpec(
            "real.opaque_context_strict_positive@1","drop_opaque_context_keep_strict_square_bound",
            "opaque_context_strict_positive",
            "(P : ℝ → Prop) (f : ℝ → ℝ) (x : ℝ) (l : List ℝ) : (P x ∧ l ≠ [] ∧ (∀ z : ℝ, f z ≥ 0) ∧ f x > x ^ 2 ∧ x ≠ 0) → f x > 0",
            """by
  rintro ⟨-, -, -, hfx, hx⟩
  have hx2 : 0 < x ^ 2 := sq_pos_of_ne_zero hx
  linarith""",
        ),
    )
    add(
        "FORALL (a: real): (EXISTS (u, v: real): u * u + v * v = a) IMPLIES a >= 0",
        ProjectionSpec(
            "real.sum_two_squares_nonnegative@1","existential_destruct_square_nonnegative",
            "sum_two_squares_nonnegative",
            "(a : ℝ) : (∃ u v : ℝ, u * u + v * v = a) → a ≥ 0",
            """by
  rintro ⟨u, v, rfl⟩
  nlinarith [sq_nonneg u, sq_nonneg v]""",
        ),
    )
    return dict(rows)


SPECS=_specs()


def discover_projection_batch(routing: Mapping[str,Any]) -> dict[str,Any]:
    rows=[]
    unmatched=[]
    target_classes={
        "OPAQUE_OR_NONPOLYNOMIAL",
        "EXISTENTIAL_CONSEQUENT",
        "QUANTIFIED_PREMISE",
        "EXISTENTIAL_PREMISE",
        "SUBTYPE_RANGE",
    }
    for row in routing["rows"]:
        if row.get("residual_class") not in target_classes:
            continue
        surface=normalize_surface(str(row["normalized_surface"]))
        spec=SPECS.get(surface)
        base={
            "theory":row["theory"],
            "formula":row["formula"],
            "residual_class":row["residual_class"],
            "normalized_surface":surface,
        }
        if spec is None:
            unmatched.append({**base,"status":"UNKNOWN_PROJECTION_SCHEMA"})
        else:
            rows.append({**base,**spec.to_dict(),"status":"CANDIDATE_PROJECTION_SCHEMA"})
    return {
        "schema":"mathgraph.cross-prover-projection-discovery.v1",
        "status":"CANDIDATE_DISCOVERY_ONLY",
        "input_target_count":sum(1 for x in routing["rows"] if x.get("residual_class") in target_classes),
        "matched_count":len(rows),
        "unmatched_count":len(unmatched),
        "matched":rows,
        "unmatched":unmatched,
    }


def render_lean_projection_file(discovery: Mapping[str,Any]) -> str:
    chunks=["import Mathlib","","namespace CrystalCrossProverProjection",""]
    for row in discovery["matched"]:
        spec=next(x for x in SPECS.values() if x.claim_id==row["claim_id"])
        chunks.extend([
            f"theorem {spec.theorem_name} {spec.lean_statement} := {spec.lean_proof}",
            "",
        ])
    chunks.append("end CrystalCrossProverProjection")
    return "\n".join(chunks)+"\n"


def compile_projection_bundle(
    discovery: Mapping[str,Any],
    *,
    evidence_refs: Sequence[str],
) -> SemanticObject:
    if discovery["unmatched_count"] != 0:
        raise ValueError("projection residual not fully matched")
    payload=canonical_bytes({
        "input_target_count":discovery["input_target_count"],
        "claims":[
            {
                "claim_id":x["claim_id"],
                "certificate_schema":x["certificate_schema"],
                "source":[x["theory"],x["formula"]],
                "residual_class":x["residual_class"],
            }
            for x in discovery["matched"]
        ],
        "evidence_refs":sorted(set(evidence_refs)),
    })
    return SemanticObject(
        "cross-prover.consequence-projection-family@1",
        1,
        payload,
        (
            "cross-prover.consequence-projection-family@1",
            "cross-prover.native-verifier-family@1",
        ),
    )
