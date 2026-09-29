"""Residual-earned witness/counterexample compiler for PVS CAD existential formulas.

The compiler is intentionally bounded to the exact source-shape family exposed
by the previous Crystal residual router. It does not use theorem names to select
semantics. Each supported surface compiles to either:
- a concrete consumer-checkable witness schema for a true proposition, or
- a concrete refutation schema whose PVS authority is the source's proved
  negation.

Every unmatched existential remains UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.crystal import SemanticObject, canonical_bytes
from mathgraph.cross_prover_family_discovery import normalize_surface


@dataclass(frozen=True)
class WitnessSpec:
    claim_id: str
    disposition: str
    certificate_schema: str
    theorem_name: str
    lean_statement: str
    lean_proof: str
    pvs_authority_formula: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id":self.claim_id,
            "disposition":self.disposition,
            "certificate_schema":self.certificate_schema,
            "theorem_name":self.theorem_name,
            "lean_statement":self.lean_statement,
            "pvs_authority_formula":self.pvs_authority_formula,
        }


def _specs() -> dict[str,WitnessSpec]:
    rows: list[tuple[str,WitnessSpec]]=[]
    def add(surface: str, spec: WitnessSpec) -> None:
        rows.append((normalize_surface(surface),spec))

    add(
        "FORALL (c: real): EXISTS (x: real): x^3 - 3 * x + c = 0",
        WitnessSpec(
            "real.depressed_cubic_has_root@1","QUALIFY_TRUE","ivt_bounded_witness",
            "depressed_cubic_has_root",
            "(c : ℝ) : ∃ x : ℝ, x ^ 3 - 3 * x + c = 0",
            """by
  let M : ℝ := |c| + 2
  let f : ℝ → ℝ := fun x => x ^ 3 - 3 * x + c
  have ha : 0 ≤ |c| := abs_nonneg c
  have ha2 : 0 ≤ |c| ^ 2 := sq_nonneg |c|
  have ha3 : 0 ≤ |c| ^ 3 := pow_nonneg ha 3
  have hc_le : c ≤ |c| := le_abs_self c
  have hc_ge : -|c| ≤ c := neg_abs_le c
  have hab : -M ≤ M := by
    dsimp [M]
    linarith
  have hleft : f (-M) ≤ 0 := by
    dsimp [f, M]
    nlinarith
  have hright : 0 ≤ f M := by
    dsimp [f, M]
    nlinarith
  have hz : (0 : ℝ) ∈ Set.Icc (f (-M)) (f M) := ⟨hleft, hright⟩
  have hcont : Continuous f := by
    fun_prop
  rcases intermediate_value_Icc hab hcont.continuousOn hz with ⟨x, -, hx⟩
  exact ⟨x, by simpa [f] using hx⟩""",
        ),
    )
    add(
        "EXISTS (x: real): EXISTS (y: real): x^2 + y^2 = 1 AND y = x^2",
        WitnessSpec(
            "real.parabola_meets_unit_circle@1","QUALIFY_TRUE","nested_radical_witness",
            "parabola_meets_unit_circle",
            ": ∃ x y : ℝ, x ^ 2 + y ^ 2 = 1 ∧ y = x ^ 2",
            """by
  let r : ℝ := Real.sqrt 5
  let t : ℝ := (r - 1) / 2
  have hr0 : 0 ≤ r := by
    dsimp [r]
    exact Real.sqrt_nonneg 5
  have hr2 : r ^ 2 = 5 := by
    dsimp [r]
    simpa using Real.sq_sqrt (show (0 : ℝ) ≤ 5 by norm_num)
  have hr1 : 1 ≤ r := by
    nlinarith
  have ht0 : 0 ≤ t := by
    dsimp [t]
    linarith
  have htEq : t ^ 2 + t = 1 := by
    dsimp [t]
    nlinarith
  let x : ℝ := Real.sqrt t
  have hx2 : x ^ 2 = t := by
    dsimp [x]
    simpa using Real.sq_sqrt ht0
  refine ⟨x, t, ?_, ?_⟩
  · nlinarith
  · exact hx2.symm""",
        ),
    )
    add(
        "FORALL (x: real): EXISTS (y: real): x * y = 1",
        WitnessSpec(
            "real.all_reals_have_inverse@1","REJECT_FALSE","zero_counterexample",
            "not_all_reals_have_inverse",
            ": ¬ (∀ x : ℝ, ∃ y : ℝ, x * y = 1)",
            """by
  intro h
  rcases h 0 with ⟨y, hy⟩
  norm_num at hy""",
            pvs_authority_formula="d_no_inverse",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): x < y IMPLIES (x < z AND z < y)",
        WitnessSpec(
            "real.between_midpoint@1","QUALIFY_TRUE","midpoint_witness",
            "between_midpoint",
            "(x y : ℝ) : ∃ z : ℝ, x < y → (x < z ∧ z < y)",
            """by
  refine ⟨(x + y) / 2, ?_⟩
  intro h
  constructor <;> linarith""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): z^2 = x^2 + y^2",
        WitnessSpec(
            "real.cone_sqrt_witness@1","QUALIFY_TRUE","sqrt_nonnegative_witness",
            "cone_sqrt_witness",
            "(x y : ℝ) : ∃ z : ℝ, z ^ 2 = x ^ 2 + y ^ 2",
            """by
  have hq : 0 ≤ x ^ 2 + y ^ 2 := by
    nlinarith [sq_nonneg x, sq_nonneg y]
  refine ⟨Real.sqrt (x ^ 2 + y ^ 2), ?_⟩
  simpa using Real.sq_sqrt hq""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): FORALL (w: real): w^2 + z > x + y",
        WitnessSpec(
            "real.square_dominating_witness@1","QUALIFY_TRUE","affine_plus_one_witness",
            "square_dominating_witness",
            "(x y : ℝ) : ∃ z : ℝ, ∀ w : ℝ, w ^ 2 + z > x + y",
            """by
  refine ⟨x + y + 1, ?_⟩
  intro w
  nlinarith [sq_nonneg w]""",
        ),
    )
    add(
        "EXISTS (x: real): x^2 = 2",
        WitnessSpec(
            "real.sqrt_two_exists@1","QUALIFY_TRUE","sqrt_constant_witness",
            "sqrt_two_exists",
            ": ∃ x : ℝ, x ^ 2 = 2",
            """by
  refine ⟨Real.sqrt 2, ?_⟩
  simpa using Real.sq_sqrt (show (0 : ℝ) ≤ 2 by norm_num)""",
        ),
    )
    add(
        "FORALL (x: real): EXISTS (y: real): y > x",
        WitnessSpec(
            "real.unbounded_above_witness@1","QUALIFY_TRUE","affine_plus_one_witness",
            "unbounded_above_witness",
            "(x : ℝ) : ∃ y : ℝ, y > x",
            """by
  exact ⟨x + 1, by linarith⟩""",
        ),
    )
    add(
        "EXISTS (x: real): FORALL (y: real): x * y = 0",
        WitnessSpec(
            "real.zero_annihilator_witness@1","QUALIFY_TRUE","constant_zero_witness",
            "zero_annihilator_witness",
            ": ∃ x : ℝ, ∀ y : ℝ, x * y = 0",
            """by
  exact ⟨0, by intro y; simp⟩""",
        ),
    )
    add(
        "FORALL (x: real): EXISTS (y: real): x^2 + y^2 = 1 OR x^2 > 1",
        WitnessSpec(
            "real.circle_or_outside@1","QUALIFY_TRUE","piecewise_sqrt_witness",
            "circle_or_outside",
            "(x : ℝ) : ∃ y : ℝ, x ^ 2 + y ^ 2 = 1 ∨ x ^ 2 > 1",
            """by
  by_cases h : x ^ 2 > 1
  · exact ⟨0, Or.inr h⟩
  · have hle : x ^ 2 ≤ 1 := le_of_not_gt h
    have hnonneg : 0 ≤ 1 - x ^ 2 := sub_nonneg.mpr hle
    refine ⟨Real.sqrt (1 - x ^ 2), Or.inl ?_⟩
    have hs : (Real.sqrt (1 - x ^ 2)) ^ 2 = 1 - x ^ 2 := Real.sq_sqrt hnonneg
    linarith""",
        ),
    )
    add(
        "EXISTS (x: real): FORALL (y: real): x^2 + y^2 > 1",
        WitnessSpec(
            "real.vertical_line_outside_circle@1","QUALIFY_TRUE","constant_two_witness",
            "vertical_line_outside_circle",
            ": ∃ x : ℝ, ∀ y : ℝ, x ^ 2 + y ^ 2 > 1",
            """by
  refine ⟨2, ?_⟩
  intro y
  nlinarith [sq_nonneg y]""",
        ),
    )
    add(
        "FORALL (x: real): EXISTS (y: real): x + 2 * y = 1 AND y * y >= 0",
        WitnessSpec(
            "real.affine_line_witness@1","QUALIFY_TRUE","affine_solve_witness",
            "affine_line_witness",
            "(x : ℝ) : ∃ y : ℝ, x + 2 * y = 1 ∧ y * y ≥ 0",
            """by
  refine ⟨(1 - x) / 2, ?_, ?_⟩
  · ring
  · positivity""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): z > x AND z > y",
        WitnessSpec(
            "real.common_upper_witness@1","QUALIFY_TRUE","max_plus_one_witness",
            "common_upper_witness",
            "(x y : ℝ) : ∃ z : ℝ, z > x ∧ z > y",
            """by
  refine ⟨max x y + 1, ?_, ?_⟩
  · have h := le_max_left x y
    linarith
  · have h := le_max_right x y
    linarith""",
        ),
    )
    return dict(rows)


SPECS=_specs()


def discover_witness_batch(routing: Mapping[str,Any]) -> dict[str,Any]:
    rows=[]
    unmatched=[]
    for row in routing["rows"]:
        if row.get("residual_class")!="EXISTENTIAL_WITNESS":
            continue
        surface=normalize_surface(str(row["normalized_surface"]))
        spec=SPECS.get(surface)
        base={
            "theory":row["theory"],
            "formula":row["formula"],
            "normalized_surface":surface,
        }
        if spec is None:
            unmatched.append({**base,"status":"UNKNOWN_WITNESS_SCHEMA"})
        else:
            rows.append({**base,**spec.to_dict(),"status":"CANDIDATE_WITNESS_SCHEMA"})

    qualified=[x for x in rows if x["disposition"]=="QUALIFY_TRUE"]
    rejected=[x for x in rows if x["disposition"]=="REJECT_FALSE"]
    return {
        "schema":"mathgraph.cross-prover-witness-discovery.v1",
        "status":"CANDIDATE_DISCOVERY_ONLY",
        "input_witness_residual_count":sum(
            1 for x in routing["rows"] if x.get("residual_class")=="EXISTENTIAL_WITNESS"
        ),
        "matched_count":len(rows),
        "qualify_true_count":len(qualified),
        "reject_false_count":len(rejected),
        "unmatched_count":len(unmatched),
        "matched":rows,
        "unmatched":unmatched,
    }


def render_lean_witness_file(discovery: Mapping[str,Any]) -> str:
    chunks=["import Mathlib","","namespace CrystalCrossProverWitness",""]
    for row in discovery["matched"]:
        spec=next(x for x in SPECS.values() if x.claim_id==row["claim_id"])
        chunks.extend([
            f"theorem {spec.theorem_name} {spec.lean_statement} := {spec.lean_proof}",
            "",
        ])
    chunks.append("end CrystalCrossProverWitness")
    return "\n".join(chunks)+"\n"


def compile_witness_bundle(
    discovery: Mapping[str,Any],
    *,
    evidence_refs: Sequence[str],
) -> SemanticObject:
    if discovery["unmatched_count"] != 0:
        raise ValueError("cannot close witness residual with unmatched schemas")
    payload=canonical_bytes({
        "input_witness_residual_count":discovery["input_witness_residual_count"],
        "qualify_true":[
            {"claim_id":x["claim_id"],"certificate_schema":x["certificate_schema"],
             "source":[x["theory"],x["formula"]]}
            for x in discovery["matched"] if x["disposition"]=="QUALIFY_TRUE"
        ],
        "reject_false":[
            {"claim_id":x["claim_id"],"certificate_schema":x["certificate_schema"],
             "source":[x["theory"],x["formula"]],
             "pvs_authority_formula":x["pvs_authority_formula"]}
            for x in discovery["matched"] if x["disposition"]=="REJECT_FALSE"
        ],
        "evidence_refs":sorted(set(evidence_refs)),
    })
    return SemanticObject(
        "cross-prover.witness-certificate-family@1",
        1,
        payload,
        (
            "cross-prover.witness-family@1",
            "cross-prover.refutation-family@1",
            "cross-prover.native-verifier-family@1",
        ),
    )
