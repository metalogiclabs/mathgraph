from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence


def analyze_direction_iut(
    treatment: Sequence[int | bool],
    controls: Mapping[str, Sequence[int | bool]],
    direction_labels: Sequence[str],
    intervention_agreement: Sequence[int | bool],
    *,
    pvalue_fn: Callable[[Sequence[tuple[int | bool, int | bool]]], float],
    effect_fn: Callable[[Sequence[int | bool], Sequence[int | bool]], float],
    interval_fn: Callable[[Sequence[int | bool], Sequence[int | bool]], tuple[float, float]],
) -> dict[str, Any]:
    n = len(treatment)
    if n <= 0 or len(direction_labels) != n:
        raise ValueError("B IUT requires one direction label per non-empty world unit")
    for values in controls.values():
        if len(values) != n:
            raise ValueError("B IUT controls must pair exactly with treatment units")

    indices: dict[str, list[int]] = defaultdict(list)
    for index, direction in enumerate(direction_labels):
        label = str(direction)
        if not label:
            raise ValueError("B direction labels must be non-empty")
        indices[label].append(index)
    if len(indices) != 12:
        raise ValueError("B IUT requires exactly 12 ordered grammar directions")

    if len(intervention_agreement) != n * 4:
        raise ValueError("B interventions must remain four nested evaluations per world unit")

    pvalues: dict[str, float] = {}
    effects: dict[str, float] = {}
    intervals: dict[str, tuple[float, float]] = {}
    unit_counts: dict[str, int] = {}
    for direction in sorted(indices):
        group = indices[direction]
        unit_counts[direction] = len(group)
        t = [treatment[i] for i in group]
        for control_name in sorted(controls):
            c = [controls[control_name][i] for i in group]
            key = f"{direction}|{control_name}"
            pvalues[key] = pvalue_fn(list(zip(c, t)))
            effects[key] = effect_fn(c, t)
            intervals[key] = interval_fn(c, t)

    return {
        "component_pvalues": pvalues,
        "component_effects": effects,
        "component_effect_intervals": intervals,
        "raw_pvalue": max(pvalues.values()),
        "minimum_component_effect": min(effects.values()),
        "direction_count": len(indices),
        "unit_count": n,
        "unit_counts_by_direction": unit_counts,
        "interventions_per_unit": 4,
        "intervention_evaluations": len(intervention_agreement),
        "inferential_unit": "ordered_direction_world_pair",
        "iut_rule": "maximum_direction_by_control_component_pvalue",
    }
