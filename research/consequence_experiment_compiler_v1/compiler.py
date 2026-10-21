#!/usr/bin/env python3
"""A finite consequence-to-experiment compiler.

The source supplies complete transition tables, observation tables, a protected
future signature, authority grants, and a desired observational partition.
The compiler may COMPOSE these supplied operations. It never invents real-world
access, treats a denied operation as authorized, or implies empirical truth.

It enumerates the *entire* reachable finite transformation monoid (no depth cap)
and solves a finite minimum-cost experimental basis over reachable observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappush, heappop
from itertools import combinations
from typing import Any


@dataclass(frozen=True)
class Instrument:
    name: str
    image: tuple[int, ...]
    cost: int


@dataclass(frozen=True)
class Readout:
    name: str
    values: tuple[int, ...]
    cost: int


@dataclass(frozen=True)
class Snapshot:
    protected: tuple[int, ...]
    operations: tuple[Instrument, ...]
    readouts: tuple[Readout, ...]
    grants: frozenset[str]
    # Prior readouts are already available and included in the observation kernel.
    base_readouts: tuple[str, ...]
    max_monoid: int = 65536


def parse_model(obj: dict[str, Any]) -> Snapshot:
    n = len(obj['protected'])
    assert 2 <= n <= 12
    assert all(isinstance(x, int) for x in obj['protected'])
    operations = tuple(Instrument(x['name'], tuple(x['image']), x['cost']) for x in obj['operations'])
    readouts = tuple(Readout(x['name'], tuple(x['values']), x['cost']) for x in obj['readouts'])
    names = [x.name for x in operations] + [x.name for x in readouts]
    assert len(set(names)) == len(names)
    assert all(len(x.image) == n and set(x.image) <= set(range(n)) and type(x.cost) is int and x.cost > 0 for x in operations)
    assert all(len(x.values) == n and type(x.cost) is int and x.cost > 0 for x in readouts)
    grants = frozenset(obj['grants']); base = tuple(obj['base_readouts'])
    assert grants <= set(names) and set(base) <= set(z.name for z in readouts)
    assert all(name in grants for name in base), 'Original observation must itself be authorized'
    max_monoid = obj.get('max_monoid', 65536)
    assert type(max_monoid) is int and max_monoid >= 1
    return Snapshot(tuple(obj['protected']), operations, readouts, grants, base, max_monoid)


def safe_operation(op: Instrument, protected: tuple[int, ...]) -> bool:
    # This models a precise *declared* protected future, not any real-world safety.
    return all(protected[i] == protected[op.image[i]] for i in range(len(protected)))


def kernels(labels: tuple[Any, ...]) -> set[tuple[int, int]]:
    return {p for p in combinations(range(len(labels)), 2) if labels[p[0]] == labels[p[1]]}


def transformation_closure(model: Snapshot, *, ignore_grants: bool = False) -> tuple[dict[tuple[int, ...], tuple[int, int, tuple[str, ...]]], dict[str, int]]:
    """Dijkstra over reachable total functions; complete because domain finite.

    Every allowed transition is individually protected-safe for *all* states.
    Only strictly positive primitive cost is admitted. No path length cut-off.
    """
    granted = [op for op in model.operations if (ignore_grants or op.name in model.grants) and safe_operation(op, model.protected)]
    granted.sort(key=lambda x: x.name)
    start = tuple(range(len(model.protected)))
    best: dict[tuple[int, ...], tuple[int, int, tuple[str, ...]]] = {start: (0, 0, ())}
    queue: list[tuple[int, int, tuple[str, ...], tuple[int, ...]]] = [(0, 0, (), start)]
    transitions = 0
    while queue:
        cost, depth, word, image = heappop(queue)
        if best.get(image) != (cost, depth, word):
            continue
        for op in granted:
            transitions += 1
            new_image = tuple(op.image[i] for i in image)
            proposed = (cost + op.cost, depth + 1, word + (op.name,))
            if new_image not in best or proposed < best[new_image]:
                best[new_image] = proposed
                if len(best) > model.max_monoid:
                    raise OverflowError('FINITE_CLOSURE_RESOURCE_BOUND: no impossibility result warranted')
                heappush(queue, (*proposed, new_image))
    return best, {'transformations': len(best), 'transitions': transitions, 'safe_operations': len(granted)}


def compile_profiles(model: Snapshot, closure: dict[tuple[int, ...], tuple[int, int, tuple[str, ...]]], ignore_grants: bool = False) -> list[dict[str, Any]]:
    # Identical observation functions need only their cheapest certified program.
    seen: dict[tuple[int, ...], tuple[Any, ...]] = {}
    for image, (cost, depth, word) in closure.items():
        for read in model.readouts:
            if not (ignore_grants or read.name in model.grants):
                continue
            vals = tuple(read.values[i] for i in image)
            key = (cost + read.cost, depth, len(word), word, read.name)
            if vals not in seen or key < seen[vals][0]:
                seen[vals] = (key, word, read)
    profiles = []
    for vals, (key, word, read) in seen.items():
        profiles.append({'values': vals, 'program': (*word, read.name), 'cost': key[0], 'depth': key[1]})
    return sorted(profiles, key=lambda x: (x['cost'], x['depth'], x['program']))


def goal_kernel(model: Snapshot, desired_labels: tuple[int, ...]) -> tuple[set[tuple[int, int]], tuple[tuple[Any, ...], ...]]:
    assert len(desired_labels) == len(model.protected)
    by_name = {r.name: r for r in model.readouts}
    # The target refines, never erases, the directly observed equivalence.
    features = tuple(tuple(by_name[name].values[i] for name in model.base_readouts) + (desired_labels[i],)
                     for i in range(len(desired_labels)))
    return kernels(features), features


def cover_goal(model: Snapshot, desired_labels: tuple[int, ...], *, ignore_grants: bool = False,
               prepared: tuple | None = None) -> dict[str, Any]:
    if prepared is None:
        closure, stats = transformation_closure(model, ignore_grants=ignore_grants)
        profiles = compile_profiles(model, closure, ignore_grants=ignore_grants)
    else:
        closure, stats, profiles = prepared
    target, _ = goal_kernel(model, desired_labels)
    by_name = {r.name: r for r in model.readouts}
    base_kernel = set(combinations(range(len(model.protected)), 2))
    for name in model.base_readouts:
        base_kernel &= kernels(by_name[name].values)
    needed = sorted(base_kernel - target)
    # A legal exact target basis must preserve all pairs declared equivalent.
    legal = [p for p in profiles if target <= kernels(p['values'])]
    candidates: list[tuple[int, dict[str, Any]]] = []
    for p in legal:
        mask = sum(1 << k for k, pair in enumerate(needed) if p['values'][pair[0]] != p['values'][pair[1]])
        if mask:
            candidates.append((mask, p))
    full = (1 << len(needed)) - 1
    accessible = 0
    for mask, p in candidates: accessible |= mask
    if accessible != full:
        uncovered = [needed[k] for k in range(len(needed)) if not accessible & (1 << k)]
        return {
            'status': 'UNREALIZABLE_IN_COMPLETE_DECLARED_FINITE_GRAMMAR',
            'target_pairs': len(needed), 'unresolved_pairs': [list(p) for p in uncovered],
            'closure': stats, 'admissible_distinct_profiles': len(profiles),
            'goal_kernel': [list(x) for x in sorted(target)], 'base_kernel': [list(x) for x in sorted(base_kernel)],
            'basis': None, 'basis_cost': None,
        }
    # Weighted exact set cover; no greedy assumption. Include a lexicographic tie rule.
    dp: dict[int, tuple[int, int, tuple[tuple[str, ...], ...]]] = {0: (0, 0, ())}
    for mask, p in candidates:
        old = list(dp.items())
        for covered, (cost, size, programs) in old:
            nxt = covered | mask
            new = (cost + p['cost'], size + 1, programs + (p['program'],))
            if nxt not in dp or new < dp[nxt]: dp[nxt] = new
    solution = dp[full]
    by_program = {p['program']: p for p in legal}
    chosen = [by_program[program] for program in solution[2]]
    actual = set(base_kernel)
    for item in chosen: actual &= kernels(item['values'])
    assert actual == target, 'Compiler must preserve exactly the requested target partition'
    return {
        'status': 'EXACT_BASIS_CONSTRUCTED', 'basis_cost': solution[0],
        'basis': [{'program': list(p['program']), 'values': list(p['values']), 'cost': p['cost']} for p in chosen],
        'target_pairs': len(needed), 'unresolved_pairs': [],
        'closure': stats, 'admissible_distinct_profiles': len(profiles),
        'goal_kernel': [list(x) for x in sorted(target)], 'base_kernel': [list(x) for x in sorted(base_kernel)],
    }


def compile_experiment(obj: dict[str, Any]) -> dict[str, Any]:
    m = parse_model(obj)
    desired = tuple(obj['desired_labels'])
    initial = cover_goal(m, desired)
    initial['model_name'] = obj['name']
    initial['grants'] = sorted(m.grants)
    initial['proof_boundary'] = 'complete finite declared transition tables, declared protection and grants only'
    if initial['status'] != 'EXACT_BASIS_CONSTRUCTED':
        all_available = cover_goal(m, desired, ignore_grants=True)
        if all_available['status'] == 'EXACT_BASIS_CONSTRUCTED':
            initial['diagnosis'] = 'MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR'
            initial['hypothetical_full_access_cost'] = all_available['basis_cost']
        else:
            initial['diagnosis'] = 'NEEDS_NEW_OBSERVATION_TYPE_OR_REVISED_TARGET'
            initial['hypothetical_full_access_cost'] = None
        initial['abstract_missing_requirement'] = 'A source-authorized safe observation separating at least one unresolved pair; NOT a physical-operation claim'
    else:
        initial['diagnosis'] = 'COMPOSED_FROM_ALREADY_GRANTED_OPERATIONS'
    return initial


def compile_many(obj: dict[str, Any], desired_label_sets: list[tuple[int, ...]]) -> dict[str, Any]:
    """Compile one fixed authority snapshot ONCE, then reuse the qualified profiles.

    No cache crosses a grant/primitive/source change. Full-grant diagnosis is a
    separate hypothetical snapshot. Independent oracle gets the same chance to
    reuse finite closure; we make no unique runtime advantage claim.
    """
    model = parse_model(obj)
    closure, stats = transformation_closure(model)
    stored = (closure, stats, compile_profiles(model, closure))
    complete = None
    hypothetical_count = 0
    out = []
    for goal in desired_label_sets:
        result = cover_goal(model, tuple(goal), prepared=stored)
        if result['status'] != 'EXACT_BASIS_CONSTRUCTED':
            if complete is None:
                closure2, stats2 = transformation_closure(model, ignore_grants=True)
                complete = (closure2, stats2, compile_profiles(model, closure2, ignore_grants=True))
                hypothetical_count += 1
            all_available = cover_goal(model, tuple(goal), ignore_grants=True, prepared=complete)
            result['diagnosis'] = ('MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR'
                if all_available['status']=='EXACT_BASIS_CONSTRUCTED' else
                'NEEDS_NEW_OBSERVATION_TYPE_OR_REVISED_TARGET')
            result['hypothetical_full_access_cost'] = all_available['basis_cost']
        else:
            result['diagnosis'] = 'COMPOSED_FROM_ALREADY_GRANTED_OPERATIONS'
        result['model_name'] = obj['name']
        result['proof_boundary'] = 'complete finite declared transition tables, declared protection and grants only'
        out.append(result)
    return {'results': out, 'snapshot_closure_calculations':1,
            'hypothetical_full_access_closure_calculations':hypothetical_count,
            'goals':len(out),'source_primitive_invention':False}