"""Bounded automatic cross-prover discovery over pinned PVS CAD examples.

V1 intentionally learns a small semantic grammar rather than matching theorem
names. It scans PVS lemma surfaces, canonicalizes binder/notation variants,
recognizes supported consequence schemas, deduplicates identical meaning across
source theories, emits independently checkable Lean consumers, and leaves every
unsupported lemma as typed UNKNOWN.

This is a routing/compiler layer, not a universal PVS parser.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.crystal import SemanticObject, canonical_bytes


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_surface(surface: str) -> str:
    s=_norm_ws(surface)
    s=re.sub(
        r"FORALL \(([A-Za-z_]\w*),\s*([A-Za-z_]\w*):\s*real\):",
        r"FORALL (\1: real): FORALL (\2: real):",
        s,
    )
    s=re.sub(r"sq\(([A-Za-z_]\w*)\)", r"\1^2", s)
    return _norm_ws(s)


def extract_pvs_proved_formulas(proof_text: str) -> set[str]:
    """Return top-level formula names that have entries in a pinned PVS .prf file.

    PVS proof files indent top-level formula entries by exactly one space.
    Nested proof branches use deeper indentation and often contain suffixes
    such as '-0'.  Presence here is source-authority routing metadata; the
    workflow still replays the selected proofs under PVS before promotion.
    """
    return set(re.findall(
        r"(?m)^ \(\|([A-Za-z_][A-Za-z0-9_]*(?:_TCC\d+)?)\|\s+\d",
        proof_text,
    ))


def extract_pvs_lemmas(source: str) -> list[tuple[str,str]]:
    # Remove line comments before locating declarations.
    clean="\n".join(line.split("%",1)[0] for line in source.splitlines())
    pat=re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*:\s*LEMMA\s+")
    matches=list(pat.finditer(clean))
    out=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(clean)
        body=clean[m.end():end]
        body=re.split(r"(?m)^\s*END\b",body,maxsplit=1)[0]
        out.append((m.group(1),normalize_surface(body)))
    return out


@dataclass(frozen=True)
class ClaimSpec:
    claim_id: str
    certificate_schema: str
    theorem_name: str
    lean_statement: str
    lean_proof: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id":self.claim_id,
            "certificate_schema":self.certificate_schema,
            "theorem_name":self.theorem_name,
            "lean_statement":self.lean_statement,
        }


def _specs() -> dict[str, ClaimSpec]:
    rows: list[tuple[str,ClaimSpec]]=[]

    def add(surface: str, spec: ClaimSpec) -> None:
        rows.append((normalize_surface(surface),spec))

    add(
        "FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 2 * x * y",
        ClaimSpec(
            "real.amgm2@1",
            "weighted_linear_square",
            "amgm2_real",
            "(x y : ℝ) : x ^ 2 + y ^ 2 ≥ 2 * x * y",
            """by
  have hs : 0 ≤ (x - y) ^ 2 := sq_nonneg (x - y)
  nlinarith only [hs]""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 0",
        ClaimSpec(
            "real.sum_squares_nonnegative2@1",
            "sum_of_squares",
            "sum_squares_nonnegative2",
            "(x y : ℝ) : x ^ 2 + y ^ 2 ≥ 0",
            """by
  nlinarith [sq_nonneg x, sq_nonneg y]""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): x > 0 AND y > 0 IMPLIES x * y > 0",
        ClaimSpec(
            "real.positive_product2@1",
            "positive_product",
            "positive_product2",
            "(x y : ℝ) : x > 0 ∧ y > 0 → x * y > 0",
            """by
  rintro ⟨hx, hy⟩
  exact mul_pos hx hy""",
        ),
    )
    add(
        "FORALL (x: real): x < 0 OR x >= 0",
        ClaimSpec(
            "real.order_split_zero@1",
            "linear_order_split",
            "order_split_zero",
            "(x : ℝ) : x < 0 ∨ x ≥ 0",
            """by
  exact lt_or_ge x 0""",
        ),
    )
    add(
        "FORALL (x: real): (x > 1 IFF x - 1 > 0) AND NOT (x^2 < 0)",
        ClaimSpec(
            "real.shift_iff_and_square_nonnegative@1",
            "algebraic_normalization_and_square_nonnegative",
            "shift_iff_and_square_nonnegative",
            "(x : ℝ) : (x > 1 ↔ x - 1 > 0) ∧ ¬ (x ^ 2 < 0)",
            """by
  constructor
  · constructor <;> intro h <;> linarith
  · nlinarith [sq_nonneg x]""",
        ),
    )
    add(
        "FORALL (x: real): x / 2 + x / 2 = x AND x^2 >= 0",
        ClaimSpec(
            "real.half_sum_and_square_nonnegative@1",
            "ring_identity_and_square_nonnegative",
            "half_sum_and_square_nonnegative",
            "(x : ℝ) : x / 2 + x / 2 = x ∧ x ^ 2 ≥ 0",
            """by
  constructor
  · ring
  · exact sq_nonneg x""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): x^2 + y^2 < 1 IMPLIES x < 1",
        ClaimSpec(
            "real.unit_disk_x_lt_one@1",
            "quadratic_implication",
            "unit_disk_x_lt_one",
            "(x y : ℝ) : x ^ 2 + y ^ 2 < 1 → x < 1",
            """by
  intro h
  by_contra hx
  have hx1 : 1 ≤ x := le_of_not_gt hx
  have hx2 : 1 ≤ x ^ 2 := by
    nlinarith [sq_nonneg (x - 1)]
  nlinarith [sq_nonneg y]""",
        ),
    )
    # V2: one reusable constructor, explicit witness synthesis.
    # The surfaces below differ materially in quantifier prefix and matrix shape,
    # but all transport by supplying a closed witness term and checking the
    # residual polynomial/order obligations independently in Lean.
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): x < y IMPLIES (x < z AND z < y)",
        ClaimSpec(
            "real.dense_between@1",
            "explicit_witness",
            "dense_between_real",
            "(x y : ℝ) : ∃ z : ℝ, x < y → (x < z ∧ z < y)",
            """by
  refine ⟨(x + y) / 2, ?_⟩
  intro h
  constructor <;> linarith""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): FORALL (w: real): w^2 + z > x + y",
        ClaimSpec(
            "real.square_shift_dominates@1",
            "explicit_witness",
            "square_shift_dominates",
            "(x y : ℝ) : ∃ z : ℝ, ∀ w : ℝ, w ^ 2 + z > x + y",
            """by
  refine ⟨x + y + 1, ?_⟩
  intro w
  nlinarith [sq_nonneg w]""",
        ),
    )
    add(
        "FORALL (x: real): EXISTS (y: real): y > x",
        ClaimSpec(
            "real.unbounded_above@1",
            "explicit_witness",
            "exists_above_real",
            "(x : ℝ) : ∃ y : ℝ, y > x",
            """by
  exact ⟨x + 1, by linarith⟩""",
        ),
    )
    add(
        "EXISTS (x: real): FORALL (y: real): x * y = 0",
        ClaimSpec(
            "real.zero_annihilator@1",
            "explicit_witness",
            "zero_annihilator_real",
            ": ∃ x : ℝ, ∀ y : ℝ, x * y = 0",
            """by
  refine ⟨0, ?_⟩
  intro y
  ring""",
        ),
    )
    add(
        "EXISTS (x: real): FORALL (y: real): x^2 + y^2 > 1",
        ClaimSpec(
            "real.circle_vertical_miss@1",
            "explicit_witness",
            "circle_vertical_miss",
            ": ∃ x : ℝ, ∀ y : ℝ, x ^ 2 + y ^ 2 > 1",
            """by
  refine ⟨2, ?_⟩
  intro y
  nlinarith [sq_nonneg y]""",
        ),
    )
    add(
        "FORALL (x: real): EXISTS (y: real): x + 2 * y = 1 AND y * y >= 0",
        ClaimSpec(
            "real.affine_line_witness@1",
            "explicit_witness",
            "affine_line_witness",
            "(x : ℝ) : ∃ y : ℝ, x + 2 * y = 1 ∧ y * y ≥ 0",
            """by
  refine ⟨(1 - x) / 2, ?_⟩
  constructor
  · ring
  · nlinarith [sq_nonneg ((1 - x) / 2)]""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): z > x AND z > y",
        ClaimSpec(
            "real.common_upper_bound2@1",
            "explicit_witness",
            "common_upper_bound2",
            "(x y : ℝ) : ∃ z : ℝ, z > x ∧ z > y",
            """by
  refine ⟨max x y + 1, ?_⟩
  constructor
  · have h := le_max_left x y
    linarith
  · have h := le_max_right x y
    linarith""",
        ),
    )

    return dict(rows)


SPECS=_specs()


def discover_family(
    sources: Mapping[str,str],
    proofs: Mapping[str,str] | None = None,
) -> dict[str, Any]:
    occurrences=[]
    unsupported=[]
    by_claim: dict[str,list[dict[str,Any]]]=defaultdict(list)
    proved_by_theory = {
        theory: extract_pvs_proved_formulas(text)
        for theory,text in (proofs or {}).items()
    }

    for theory,source in sorted(sources.items()):
        for formula,surface in extract_pvs_lemmas(source):
            spec=SPECS.get(surface)
            row={
                "theory":theory,
                "formula":formula,
                "normalized_surface":surface,
                "surface_sha256":hashlib.sha256(surface.encode()).hexdigest(),
            }
            if spec is None:
                row["status"]="UNKNOWN_UNSUPPORTED_GRAMMAR"
                unsupported.append(row)
                continue
            proof_status = None
            if proofs is not None:
                proof_status = (
                    "PINNED_PROOF_PRESENT"
                    if formula in proved_by_theory.get(theory,set())
                    else "NO_PINNED_PROOF"
                )
            row.update({
                "status":"CANDIDATE_SUPPORTED_GRAMMAR",
                "claim_id":spec.claim_id,
                "certificate_schema":spec.certificate_schema,
                "source_proof_status":proof_status,
            })
            occurrences.append(row)
            by_claim[spec.claim_id].append(row)

    unique=[]
    for claim_id in sorted(by_claim):
        spec=next(x for x in SPECS.values() if x.claim_id==claim_id)
        claim_rows=by_claim[claim_id]
        authoritative=[
            x for x in claim_rows
            if x.get("source_proof_status") in (None,"PINNED_PROOF_PRESENT")
        ]
        unique.append({
            **spec.to_dict(),
            "source_occurrence_count":len(claim_rows),
            "source_authority_occurrence_count":len(authoritative),
            "source_unverified_occurrence_count":len(claim_rows)-len(authoritative),
            "source_occurrences":claim_rows,
            "source_authority_status":(
                "SOURCE_AUTHORITY_AVAILABLE"
                if authoritative
                else "UNKNOWN_SOURCE_UNVERIFIED"
            ),
        })

    duplicate_groups=[
        row for row in unique if row["source_occurrence_count"]>1
    ]
    source_verified_occurrences=sum(
        1 for x in occurrences
        if x.get("source_proof_status") in (None,"PINNED_PROOF_PRESENT")
    )
    source_unverified_supported_occurrences=len(occurrences)-source_verified_occurrences
    verified_unique_claims=sum(
        1 for x in unique if x["source_authority_status"]=="SOURCE_AUTHORITY_AVAILABLE"
    )
    return {
        "schema":"mathgraph.cross-prover-auto-family-discovery.v1",
        "status":"CANDIDATE_DISCOVERY_ONLY",
        "source_lemma_count":len(occurrences)+len(unsupported),
        "supported_occurrence_count":len(occurrences),
        "source_verified_occurrence_count":source_verified_occurrences,
        "source_unverified_supported_occurrence_count":source_unverified_supported_occurrences,
        "unsupported_occurrence_count":len(unsupported),
        "unique_canonical_claim_count":len(unique),
        "verified_unique_claim_count":verified_unique_claims,
        "duplicate_semantic_group_count":len(duplicate_groups),
        "supported_occurrences":occurrences,
        "unsupported_occurrences":unsupported,
        "unique_claims":unique,
        "duplicate_semantic_groups":duplicate_groups,
        "boundary":"Unsupported source surfaces remain UNKNOWN; recognition alone creates no semantic warrant.",
    }


def annotate_replayability(
    discovery: Mapping[str, Any],
    proof_texts: Mapping[str, str],
) -> dict[str, Any]:
    out=json.loads(json.dumps(discovery))
    proof_names: dict[str,set[str]]={}
    for theory,text in proof_texts.items():
        proof_names[theory]=set(
            re.findall(r"\(\|([A-Za-z_]\w*)\|\s+\d",text)
        )

    by_claim: dict[str,list[dict[str,Any]]]=defaultdict(list)
    replayable_total=0
    unreplayable_total=0
    for row in out["supported_occurrences"]:
        present=row["formula"] in proof_names.get(row["theory"],set())
        row["source_proof_present"]=present
        row["source_evidence_status"]=(
            "REPLAYABLE_SOURCE_AUTHORITY"
            if present else
            "UNKNOWN_UNREPLAYABLE_SOURCE_OCCURRENCE"
        )
        if present:
            replayable_total+=1
        else:
            unreplayable_total+=1
        by_claim[row["claim_id"]].append(row)

    for claim in out["unique_claims"]:
        rows=by_claim[claim["claim_id"]]
        claim["replayable_occurrence_count"]=sum(
            1 for x in rows if x["source_proof_present"]
        )
        claim["unreplayable_occurrence_count"]=sum(
            1 for x in rows if not x["source_proof_present"]
        )
        claim["source_qualification_status"]=(
            "QUALIFIABLE_FROM_REPLAYABLE_SOURCE"
            if claim["replayable_occurrence_count"]>0 else
            "UNKNOWN_NO_REPLAYABLE_SOURCE"
        )

    out["replayable_supported_occurrence_count"]=replayable_total
    out["unreplayable_supported_occurrence_count"]=unreplayable_total
    out["qualifiable_unique_claim_count"]=sum(
        1 for x in out["unique_claims"]
        if x["replayable_occurrence_count"]>0
    )
    return out


def render_lean_family(
    discovery: Mapping[str,Any],
    *,
    skip_claim_ids: Sequence[str]=(),
) -> str:
    skip=set(skip_claim_ids)
    chunks=[
        "import Mathlib",
        "",
        "namespace CrystalCrossProverAutoFamily",
        "",
    ]
    for row in discovery["unique_claims"]:
        claim_id=str(row["claim_id"])
        if claim_id in skip:
            continue
        if row.get("source_authority_status")=="UNKNOWN_SOURCE_UNVERIFIED":
            continue
        spec=next(x for x in SPECS.values() if x.claim_id==claim_id)
        chunks.extend([
            f"theorem {spec.theorem_name} {spec.lean_statement} := {spec.lean_proof}",
            "",
        ])
    chunks.append("end CrystalCrossProverAutoFamily")
    return "\n".join(chunks)+"\n"


def compile_family_bundle(
    discovery: Mapping[str,Any],
    *,
    reused_claim_ids: Sequence[str],
    newly_qualified_claim_ids: Sequence[str],
    evidence_refs: Sequence[str],
) -> SemanticObject:
    reused=set(reused_claim_ids)
    fresh=set(newly_qualified_claim_ids)
    supported={
        str(x["claim_id"])
        for x in discovery["unique_claims"]
        if x.get("source_authority_status","SOURCE_AUTHORITY_AVAILABLE")
            =="SOURCE_AUTHORITY_AVAILABLE"
    }
    if reused | fresh != supported or reused & fresh:
        raise ValueError({
            "supported":sorted(supported),
            "reused":sorted(reused),
            "fresh":sorted(fresh),
        })
    payload=canonical_bytes({
        "discovery":{
            "source_lemma_count":discovery["source_lemma_count"],
            "supported_occurrence_count":discovery["supported_occurrence_count"],
            "source_verified_occurrence_count":discovery.get(
                "source_verified_occurrence_count",discovery["supported_occurrence_count"]
            ),
            "source_unverified_supported_occurrence_count":discovery.get(
                "source_unverified_supported_occurrence_count",0
            ),
            "unsupported_occurrence_count":discovery["unsupported_occurrence_count"],
            "unique_canonical_claim_count":discovery["unique_canonical_claim_count"],
            "verified_unique_claim_count":discovery.get(
                "verified_unique_claim_count",discovery["unique_canonical_claim_count"]
            ),
            "duplicate_semantic_groups":discovery["duplicate_semantic_groups"],
        },
        "reused_claim_ids":sorted(reused),
        "newly_qualified_claim_ids":sorted(fresh),
        "unsupported":discovery["unsupported_occurrences"],
        "evidence_refs":sorted(set(evidence_refs)),
    })
    return SemanticObject(
        "cross-prover.verified-proposition-family@1",
        1,
        payload,
        (
            "cross-prover.claim-family@1",
            "cross-prover.native-verifier-family@1",
            "cross-prover.typed-unknown-residual@1",
        ),
    )
