"""Bounded structural router for cross-prover held-out residuals.

This module is intentionally downstream of the exact V5 linker. It routes only
surfaces left UNKNOWN by exact semantic matching. Routing is based on
alpha-normalized formula shape, never theorem names.

A route is either:
- DERIVED_CONSEQUENCE: a prior warranted claim interface is sufficient to prove
  the source instance; or
- NEW_EXACT_SCHEMA: the source expresses a genuinely new canonical meaning
  handled by a reusable proof-construction schema.

Classification alone is CANDIDATE evidence. Promotion still requires the
declared Lean adapter/schema proof and native source-verifier replay.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from mathgraph.cross_prover_family_discovery import normalize_surface


@dataclass(frozen=True)
class SchemaRoute:
    route_kind: str
    schema_id: str
    dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "route_kind": self.route_kind,
            "schema_id": self.schema_id,
            "dependencies": list(self.dependencies),
        }


def alpha_normalize_surface(surface: str) -> str:
    # Expand paired real binders before the existing surface normalization.
    s=surface
    pair=re.compile(r"(FORALL|EXISTS) \(([A-Za-z_]\w*),\s*([A-Za-z_]\w*):\s*real\):")
    while True:
        m=pair.search(s)
        if m is None:
            break
        q,a,b=m.groups()
        s=s[:m.start()]+f"{q} ({a}: real): {q} ({b}: real):"+s[m.end():]
    s=normalize_surface(s)
    names=[m.group(2) for m in re.finditer(
        r"(FORALL|EXISTS) \(([A-Za-z_]\w*): real\):",s
    )]
    mapping: dict[str,str]={}
    for name in names:
        if name not in mapping:
            mapping[name]=f"v{len(mapping)}"
    # All bounded source families used here have unique binder names.
    for old,new in sorted(mapping.items(),key=lambda kv:-len(kv[0])):
        s=re.sub(rf"\b{re.escape(old)}\b",new,s)
    return normalize_surface(s)


_Q=re.compile(r"^(FORALL|EXISTS) \((v\d+): real\):\s*")


def _prefix(surface: str) -> tuple[list[tuple[str,str]],str]:
    rest=surface.strip()
    qs=[]
    while True:
        m=_Q.match(rest)
        if m is None:
            return qs,rest
        qs.append((m.group(1),m.group(2)))
        rest=rest[m.end():].strip()


def _false_antecedent(surface: str) -> str | None:
    s=surface.strip()
    if not (s.startswith("(") and s.endswith(") IMPLIES FALSE")):
        return None
    return s[1:-len(") IMPLIES FALSE")].strip()


def _all_conjuncts(body: str) -> set[str]:
    return {x.strip() for x in body.split(" AND ")}


def route_surface(surface: str) -> SchemaRoute | None:
    s=alpha_normalize_surface(surface)

    # Finite upper-bound fold: forall x_0 ... x_n, exists w, w > every x_i.
    qs,body=_prefix(s)
    if len(qs)>=3 and all(q=="FORALL" for q,_ in qs[:-1]) and qs[-1][0]=="EXISTS":
        witness=qs[-1][1]
        outers=[v for _,v in qs[:-1]]
        if _all_conjuncts(body)=={f"{witness} > {v}" for v in outers}:
            return SchemaRoute(
                "DERIVED_CONSEQUENCE",
                "finite_upper_bound_fold@1",
                ("real.common_upper_bound2@1",),
            )

    # Specialize the already-warranted two-input square-shift theorem at y=0.
    if qs==[("FORALL","v0"),("EXISTS","v1"),("FORALL","v2")]:
        if body in {"v2 * v2 + v1 > v0","v2^2 + v1 > v0"}:
            return SchemaRoute(
                "DERIVED_CONSEQUENCE",
                "square_shift_specialization@1",
                ("real.square_shift_dominates@1",),
            )

    # AM-GM plus additional nonnegative square coordinates.
    if len(qs)>=3 and all(q=="FORALL" for q,_ in qs):
        rhs="2 * v0 * v1"
        if f" >= {rhs}" in body:
            left,right=body.rsplit(" >= ",1)
            terms={x.strip() for x in left.split(" + ")}
            expected={f"v{i}^2" for i in range(len(qs))}
            if right==rhs and terms==expected:
                return SchemaRoute(
                    "DERIVED_CONSEQUENCE",
                    "amgm_square_extension@1",
                    ("real.amgm2@1",),
                )

    # Root the sum of two squares, then reuse the scalar circle/outside claim.
    if qs==[("FORALL","v0"),("FORALL","v1"),("EXISTS","v2")]:
        if body==(
            "v0^2 + v1^2 + v2^2 = 1 OR "
            "v0^2 + v1^2 > 1"
        ):
            return SchemaRoute(
                "DERIVED_CONSEQUENCE",
                "root_circle_composition@1",
                ("real.sum_squares_has_root@1","real.circle_or_outside@1"),
            )

    # Choose the first existential arbitrarily, then use unbounded-above at the
    # final additive target.
    if qs==[
        ("FORALL","v0"),("EXISTS","v1"),("FORALL","v2"),("EXISTS","v3")
    ] and body=="v3 > v0 + v1 + v2":
        return SchemaRoute(
            "DERIVED_CONSEQUENCE",
            "nested_unbounded_above@1",
            ("real.unbounded_above@1",),
        )

    ant=_false_antecedent(s)
    if ant is not None:
        aqs,abody=_prefix(ant)

        # Adversarial interval: set all universal endpoints equal.
        if len(aqs)>=3 and all(q=="FORALL" for q,_ in aqs[:-1]) and aqs[-1][0]=="EXISTS":
            w=aqs[-1][1]
            cs=_all_conjuncts(abody)
            greater=[c for c in cs if c.startswith(f"{w} > ")]
            less=[c for c in cs if c.startswith(f"{w} < ")]
            if greater and less and len(cs)==len(greater)+len(less):
                return SchemaRoute(
                    "NEW_EXACT_SCHEMA",
                    "adversarial_quantifier_refutation@1",
                )

        # Existential x; universal y; existential z with z²=y-x is refuted by
        # the adversarial specialization y=x-1.
        if aqs==[("EXISTS","v0"),("FORALL","v1"),("EXISTS","v2")]:
            if abody in {"v2 * v2 = v1 - v0","v2^2 = v1 - v0"}:
                return SchemaRoute(
                    "NEW_EXACT_SCHEMA",
                    "adversarial_quantifier_refutation@1",
                )

    return None


def route_many(surfaces: Sequence[str]) -> list[SchemaRoute | None]:
    return [route_surface(x) for x in surfaces]
