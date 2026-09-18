"""Exact exchangeability check for an explicitly supplied finite joint law.

The support must come from the actual generation/selection/stopping model to
justify that model. Symmetry of a convenient synthetic law proves nothing about
an unrelated experiment. No estimate from a finite observed sample is used.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any, Sequence


def audit_joint_law(
    law: Sequence[tuple[Sequence[Sequence[int]], Fraction]],
    *, contexts: Sequence[str] | None = None,
) -> dict[str, Any]:
    if not law or (contexts is not None and len(contexts) != len(law)):
        raise ValueError('need complete support with aligned pre-outcome contexts')
    mass: dict[tuple[str, tuple[tuple[int, int], ...]], Fraction] = defaultdict(Fraction)
    widths = set()
    for index, (vector, weight) in enumerate(law):
        if not isinstance(weight, (Fraction, int)) or weight < 0:
            raise ValueError('probability masses must be exact nonnegative rationals')
        if not vector or any(len(pair) != 2 or any(type(v) is not int or v not in (0, 1) for v in pair) for pair in vector):
            raise ValueError('nonempty paired binary vectors required')
        key = tuple((pair[0], pair[1]) for pair in vector)
        widths.add(len(key))
        context = 'unconditional' if contexts is None else str(contexts[index])
        mass[(context, key)] += Fraction(weight)
    if len(widths) != 1 or sum(mass.values()) != 1:
        raise ValueError('support must have fixed dimension and exactly unit total mass')
    witnesses = []
    for (context, vector), probability in sorted(mass.items()):
        swapped = tuple((right, left) for left, right in vector)
        reverse_mass = mass.get((context, swapped), Fraction(0))
        if reverse_mass != probability:
            witnesses.append({'context': context, 'vector': vector,
                              'mass': str(probability), 'joint_swapped_mass': str(reverse_mass)})
    return {'exchangeable': not witnesses, 'separating_witnesses': witnesses,
            'support_size': len(mass), 'dose_count': next(iter(widths)),
            'scope': 'exact supplied finite joint law including context; not validation of an unbound generator'}
