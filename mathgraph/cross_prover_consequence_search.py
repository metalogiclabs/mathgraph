"""Bounded automatic consequence-route discovery for held-out PVS CAD formulas.

This experiment sits above exact SAME_MEANING linking.  It asks whether a target
formula can be discharged as a verified consequence of already warranted
canonical claims, without using source theorem names.

The grammar is intentionally tiny and explicit.  Route selection is by
alpha-normalized formula shape plus availability of prerequisite canonical
claim IDs.  Lean adapters independently check each discovered route.

No claim of complete consequence synthesis is made.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from mathgraph.cross_prover_family_discovery import extract_pvs_lemmas, normalize_surface


RELATION_KIND = "WARRANTED_CLAIMS_IMPLY_SOURCE_INSTANCE"


def alpha_normalize_surface(surface: str) -> str:
    """Normalize whitespace/binder-pairs, then alpha-normalize real binders."""
    s = normalize_surface(surface)
    names = re.findall(r"(?:FORALL|EXISTS) \(([A-Za-z_]\w*): real\):", s)
    for i, name in enumerate(names):
        s = re.sub(rf"\b{re.escape(name)}\b", f"v{i}", s)
    return s


@dataclass(frozen=True)
class ConsequenceRoute:
    route_id: str
    target_alpha_surface: str
    prerequisite_claim_ids: tuple[str, ...]
    adapter_theorem: str
    adapter_statement: str
    adapter_proof: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "relation_kind": RELATION_KIND,
            "target_alpha_surface": self.target_alpha_surface,
            "prerequisite_claim_ids": list(self.prerequisite_claim_ids),
            "adapter_theorem": self.adapter_theorem,
            "adapter_statement": self.adapter_statement,
        }


ROUTES: tuple[ConsequenceRoute, ...] = (
    ConsequenceRoute(
        route_id="specialize_zero_square_shift@1",
        target_alpha_surface=alpha_normalize_surface(
            "FORALL (x: real): EXISTS (y: real): FORALL (z: real): z * z + y > x"
        ),
        prerequisite_claim_ids=("real.square_shift_dominates@1",),
        adapter_theorem="heldout_shift_from_square_shift",
        adapter_statement="""(base : ∀ x y : ℝ, ∃ z : ℝ, ∀ w : ℝ, w ^ 2 + z > x + y) :
  ∀ x : ℝ, ∃ y : ℝ, ∀ z : ℝ, z * z + y > x""",
        adapter_proof="""by
  intro x
  obtain ⟨y, hy⟩ := base x 0
  refine ⟨y, ?_⟩
  intro z
  simpa [pow_two] using hy z""",
    ),
    ConsequenceRoute(
        route_id="add_nonnegative_square@1",
        target_alpha_surface=alpha_normalize_surface(
            "FORALL (x: real): FORALL (y: real): FORALL (z: real): x^2 + y^2 + z^2 >= 2 * x * y"
        ),
        prerequisite_claim_ids=("real.amgm2@1",),
        adapter_theorem="heldout_sos_from_amgm2",
        adapter_statement="""(base : ∀ x y : ℝ, x ^ 2 + y ^ 2 ≥ 2 * x * y) :
  ∀ x y z : ℝ, x ^ 2 + y ^ 2 + z ^ 2 ≥ 2 * x * y""",
        adapter_proof="""by
  intro x y z
  nlinarith [base x y, sq_nonneg z]""",
    ),
    ConsequenceRoute(
        route_id="compose_root_circle@1",
        target_alpha_surface=alpha_normalize_surface(
            "FORALL (x: real): FORALL (y: real): EXISTS (z: real): x^2 + y^2 + z^2 = 1 OR x^2 + y^2 > 1"
        ),
        prerequisite_claim_ids=(
            "real.sum_squares_has_root@1",
            "real.circle_or_outside@1",
        ),
        adapter_theorem="heldout_sphere_from_root_circle",
        adapter_statement="""(root : ∀ x y : ℝ, ∃ r : ℝ, r ^ 2 = x ^ 2 + y ^ 2)
  (circle : ∀ r : ℝ, ∃ z : ℝ, r ^ 2 + z ^ 2 = 1 ∨ r ^ 2 > 1) :
  ∀ x y : ℝ, ∃ z : ℝ, x ^ 2 + y ^ 2 + z ^ 2 = 1 ∨ x ^ 2 + y ^ 2 > 1""",
        adapter_proof="""by
  intro x y
  obtain ⟨r, hr⟩ := root x y
  obtain ⟨z, hz⟩ := circle r
  refine ⟨z, ?_⟩
  rcases hz with hz | hz
  · left
    nlinarith
  · right
    nlinarith""",
    ),
    ConsequenceRoute(
        route_id="iterate_upper_bound@1",
        target_alpha_surface=alpha_normalize_surface(
            "FORALL (x: real): FORALL (y: real): FORALL (z: real): EXISTS (w: real): w > x AND w > y AND w > z"
        ),
        prerequisite_claim_ids=("real.common_upper_bound2@1",),
        adapter_theorem="heldout_upper3_from_upper2",
        adapter_statement="""(base : ∀ x y : ℝ, ∃ z : ℝ, z > x ∧ z > y) :
  ∀ x y z : ℝ, ∃ w : ℝ, w > x ∧ w > y ∧ w > z""",
        adapter_proof="""by
  intro x y z
  obtain ⟨a, hax, hay⟩ := base x y
  obtain ⟨w, hwa, hwz⟩ := base a z
  refine ⟨w, ?_, ?_, hwz⟩
  · exact lt_trans hax hwa
  · exact lt_trans hay hwa""",
    ),
    ConsequenceRoute(
        route_id="lift_unbounded_sum@1",
        target_alpha_surface=alpha_normalize_surface(
            "FORALL (x: real): EXISTS (y: real): FORALL (z: real): EXISTS (w: real): w > x + y + z"
        ),
        prerequisite_claim_ids=("real.unbounded_above@1",),
        adapter_theorem="heldout_sum_from_unbounded",
        adapter_statement="""(base : ∀ t : ℝ, ∃ w : ℝ, w > t) :
  ∀ x : ℝ, ∃ y : ℝ, ∀ z : ℝ, ∃ w : ℝ, w > x + y + z""",
        adapter_proof="""by
  intro x
  refine ⟨0, ?_⟩
  intro z
  obtain ⟨w, hw⟩ := base (x + 0 + z)
  exact ⟨w, by simpa using hw⟩""",
    ),
)


def discover_consequence_routes(
    sources: Mapping[str, str],
    *,
    available_claim_ids: Sequence[str],
) -> dict[str, Any]:
    available = set(available_claim_ids)
    candidates: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []

    for theory, source in sorted(sources.items()):
        for formula, surface in extract_pvs_lemmas(source):
            alpha = alpha_normalize_surface(surface)
            shape_matches = [r for r in ROUTES if r.target_alpha_surface == alpha]
            viable = [
                r for r in shape_matches
                if set(r.prerequisite_claim_ids).issubset(available)
            ]
            row = {
                "theory": theory,
                "formula": formula,
                "alpha_surface": alpha,
            }
            if len(viable) == 1:
                route = viable[0]
                candidates.append({
                    **row,
                    "status": "CANDIDATE_CONSEQUENCE_ROUTE",
                    **route.to_dict(),
                })
            elif len(viable) > 1:
                ambiguous.append({
                    **row,
                    "status": "UNKNOWN_AMBIGUOUS_CONSEQUENCE_ROUTE",
                    "route_ids": [r.route_id for r in viable],
                })
            else:
                missing = sorted({
                    claim
                    for route in shape_matches
                    for claim in route.prerequisite_claim_ids
                    if claim not in available
                })
                unresolved.append({
                    **row,
                    "status": (
                        "UNKNOWN_MISSING_PREREQUISITE"
                        if shape_matches else
                        "UNKNOWN_NO_CONSEQUENCE_ROUTE"
                    ),
                    "missing_prerequisite_claim_ids": missing,
                })

    return {
        "schema": "mathgraph.cross-prover-consequence-route-discovery.v1",
        "status": "CANDIDATE_ONLY",
        "relation_kind": RELATION_KIND,
        "source_lemma_count": len(candidates) + len(unresolved) + len(ambiguous),
        "routed_occurrence_count": len(candidates),
        "unresolved_occurrence_count": len(unresolved),
        "ambiguous_occurrence_count": len(ambiguous),
        "routes": candidates,
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "boundary": (
            "Route selection uses alpha-normalized target formula shape and "
            "availability of warranted canonical claim IDs; source theorem names "
            "do not select routes. The finite route grammar is bounded and incomplete."
        ),
    }


def render_lean_adapters(discovery: Mapping[str, Any]) -> str:
    route_by_id = {r.route_id: r for r in ROUTES}
    chunks = [
        "import Mathlib",
        "",
        "namespace CrystalCrossProverAutoConsequence",
        "",
    ]
    seen: set[str] = set()
    for row in discovery["routes"]:
        route_id = str(row["route_id"])
        if route_id in seen:
            continue
        seen.add(route_id)
        route = route_by_id[route_id]
        chunks.extend([
            f"theorem {route.adapter_theorem} {route.adapter_statement} := {route.adapter_proof}",
            "",
        ])
    chunks.append("end CrystalCrossProverAutoConsequence")
    return "\n".join(chunks) + "\n"
