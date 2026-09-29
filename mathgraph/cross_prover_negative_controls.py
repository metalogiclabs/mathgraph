"""Exact negative-control classification for the pinned PVS CAD corpus.

These source surfaces are not candidates for semantic promotion.  Each is
recognized by formula shape and paired with an independently checkable Lean
countermodel theorem proving the negation of the source formula.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mathgraph.cross_prover_family_discovery import extract_pvs_lemmas, normalize_surface


@dataclass(frozen=True)
class NegativeSpec:
    control_id: str
    theorem_name: str
    lean_statement: str
    lean_proof: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "theorem_name": self.theorem_name,
            "lean_statement": self.lean_statement,
            "disposition": "REJECTED_BY_VERIFIED_COUNTERMODEL",
        }


def _specs() -> dict[str, NegativeSpec]:
    rows: list[tuple[str, NegativeSpec]] = []

    def add(surface: str, spec: NegativeSpec) -> None:
        rows.append((normalize_surface(surface), spec))

    add(
        "FORALL (x: real): EXISTS (y: real): x * y = 1",
        NegativeSpec(
            "negative.real.zero_inverse_forall@1",
            "d_inverse_countermodel",
            ": ¬ (∀ x : ℝ, ∃ y : ℝ, x * y = 1)",
            """by
  intro h
  rcases h 0 with ⟨y, hy⟩
  norm_num at hy""",
        ),
    )
    add(
        "FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 3 * x * y",
        NegativeSpec(
            "negative.real.amgm3_false@1",
            "t_amgm3_countermodel",
            ": ¬ (∀ x y : ℝ, x ^ 2 + y ^ 2 ≥ 3 * x * y)",
            """by
  intro h
  have h11 := h 1 1
  norm_num at h11""",
        ),
    )
    return dict(rows)


SPECS = _specs()


def discover_negative_controls(sources: Mapping[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for theory, source in sorted(sources.items()):
        for formula, surface in extract_pvs_lemmas(source):
            spec = SPECS.get(surface)
            if spec is None:
                continue
            rows.append({
                "theory": theory,
                "formula": formula,
                "normalized_surface": surface,
                **spec.to_dict(),
            })
    return {
        "schema": "mathgraph.cross-prover-negative-controls.v1",
        "status": "CANDIDATE_COUNTERMODELS",
        "negative_count": len(rows),
        "negative_controls": rows,
        "boundary": (
            "A recognized negative source surface is never a promotion candidate. "
            "Rejection becomes warranted only after the generated countermodel theorem "
            "kernel-checks."
        ),
    }


def render_lean_negative_controls(discovery: Mapping[str, Any]) -> str:
    chunks = [
        "import Mathlib",
        "",
        "namespace CrystalCrossProverNegativeControls",
        "",
    ]
    seen: set[str] = set()
    for row in discovery["negative_controls"]:
        control_id = str(row["control_id"])
        if control_id in seen:
            continue
        seen.add(control_id)
        spec = next(x for x in SPECS.values() if x.control_id == control_id)
        chunks.extend([
            f"theorem {spec.theorem_name} {spec.lean_statement} := {spec.lean_proof}",
            "",
        ])
    chunks.append("end CrystalCrossProverNegativeControls")
    return "\n".join(chunks) + "\n"
