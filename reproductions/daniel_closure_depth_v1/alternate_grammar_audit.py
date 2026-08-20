#!/usr/bin/env python3
"""Independent representation-invariance audit for O1.

This does not import the experiment runner. It compares two genuinely different
constructor syntaxes:

A. direct position-indexed rewrites r[i, a -> b];
B. fixed-slot rewrites transported by the old cyclic action,
   rho^(-k) ; r[0, a -> b] ; rho^k.

The two grammars must recover the same closure-relative capability class across
both acquisition cases even though their literal constructor terms differ.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

TOKENS = ("LT", "LE", "AND", "OR", "A", "B", "C", "D")

State = tuple[str, str, str, str]

SOURCES: tuple[tuple[State, State], ...] = (
    (("LT", "A", "B", "C"), ("LE", "A", "B", "C")),
    (("A", "B", "LT", "C"), ("A", "B", "LE", "C")),
)


def rotate(xs: State, k: int) -> State:
    k %= len(xs)
    return xs[k:] + xs[:k]


@dataclass(frozen=True)
class Direct:
    pos: int
    src: str
    dst: str

    def apply(self, xs: State) -> State | None:
        if xs[self.pos] != self.src:
            return None
        out = list(xs)
        out[self.pos] = self.dst
        return tuple(out)  # type: ignore[return-value]


@dataclass(frozen=True)
class ConjugatedFixedSlot:
    shift: int
    src: str
    dst: str

    def apply(self, xs: State) -> State | None:
        # Rotate so the selected site becomes slot 0, rewrite slot 0, rotate back.
        y = rotate(xs, self.shift)
        if y[0] != self.src:
            return None
        z = list(y)
        z[0] = self.dst
        return rotate(tuple(z), -self.shift)  # type: ignore[arg-type,return-value]


def direct_candidates() -> list[Direct]:
    return [
        Direct(i, src, dst)
        for i in range(4)
        for src in TOKENS
        for dst in TOKENS
        if src != dst
    ]


def conjugated_candidates() -> list[ConjugatedFixedSlot]:
    return [
        ConjugatedFixedSlot(k, src, dst)
        for k in range(4)
        for src in TOKENS
        for dst in TOKENS
        if src != dst
    ]


def surviving_classes(grammar: str, source: State, target: State) -> set[tuple[str, str]]:
    if grammar == "direct":
        return {
            (r.src, r.dst)
            for r in direct_candidates()
            if r.apply(source) == target
        }
    if grammar == "conjugated-fixed-slot":
        return {
            (r.src, r.dst)
            for r in conjugated_candidates()
            if r.apply(source) == target
        }
    raise ValueError(grammar)


def literal_survivors(grammar: str, source: State, target: State) -> list[dict[str, object]]:
    if grammar == "direct":
        return [
            {"pos": r.pos, "src": r.src, "dst": r.dst}
            for r in direct_candidates()
            if r.apply(source) == target
        ]
    return [
        {"shift": r.shift, "fixed_slot": 0, "src": r.src, "dst": r.dst}
        for r in conjugated_candidates()
        if r.apply(source) == target
    ]


def main() -> int:
    per_case: list[dict[str, object]] = []
    direct_intersection: set[tuple[str, str]] | None = None
    conjugated_intersection: set[tuple[str, str]] | None = None

    for idx, (source, target) in enumerate(SOURCES, start=1):
        d = surviving_classes("direct", source, target)
        c = surviving_classes("conjugated-fixed-slot", source, target)
        direct_intersection = d if direct_intersection is None else direct_intersection & d
        conjugated_intersection = c if conjugated_intersection is None else conjugated_intersection & c
        per_case.append(
            {
                "case": idx,
                "direct_literal_survivors": literal_survivors("direct", source, target),
                "conjugated_literal_survivors": literal_survivors("conjugated-fixed-slot", source, target),
                "direct_classes": sorted([list(x) for x in d]),
                "conjugated_classes": sorted([list(x) for x in c]),
            }
        )

    expected = {("LT", "LE")}
    gates = {
        "A0_constructor_syntaxes_are_distinct": (
            "pos" in per_case[0]["direct_literal_survivors"][0]  # type: ignore[index,operator]
            and "shift" in per_case[0]["conjugated_literal_survivors"][0]  # type: ignore[index,operator]
        ),
        "A1_direct_grammar_recovers_unique_class": direct_intersection == expected,
        "A2_conjugated_fixed_slot_grammar_recovers_unique_class": conjugated_intersection == expected,
        "A3_same_class_across_grammars": direct_intersection == conjugated_intersection == expected,
    }

    report = {
        "protocol": "INDEPENDENT_ALTERNATE_GRAMMAR_AUDIT_V1",
        "grammar_A": "direct position-indexed one-site rewrite",
        "grammar_B": "fixed-slot rewrite conjugated by old C4 transport",
        "per_case": per_case,
        "direct_intersection": sorted([list(x) for x in (direct_intersection or set())]),
        "conjugated_intersection": sorted([list(x) for x in (conjugated_intersection or set())]),
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
