"""Execute finite cell interventions against a supplied protected evaluator.

Unlike the historical planted G fixtures, flip labels are derived by evaluating
both the unmodified and modified object. Relevance is audited over the supplied
finite intervention alphabet. Exhaustiveness outside that alphabet is not claimed.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Iterable, Mapping, Sequence
from .dev_world import DevWorld

Evaluator = Callable[[DevWorld], Sequence[str]]


def legacy_world_order(world: DevWorld) -> tuple[str, ...]:
    """Read the existing world's protected-action truth without inventing semantics.

    The legacy world stores this label independently of all comparative cells.
    Consequently its cells cannot justify its pre-assigned relevance annotations.
    """
    ids = tuple(action.action_id for action in world.actions)
    start = ids.index(world.optimal_action_id)
    return ids[start:] + ids[:start]


def evaluate_corruption(world: DevWorld, evaluator: Evaluator,
                        replacements: Mapping[str, int]) -> dict[str, Any]:
    cells = {c.cell_id for c in world.comparative_cells}
    if not set(replacements) <= cells or any(type(v) is not int for v in replacements.values()):
        raise ValueError('corruption must specify existing cell IDs and integer values')
    changed = replace(world, comparative_cells=tuple(
        replace(cell, value=replacements[cell.cell_id]) if cell.cell_id in replacements else cell
        for cell in world.comparative_cells))
    before, after = tuple(evaluator(world)), tuple(evaluator(changed))
    return {'before': before, 'after': after, 'flip': int(before != after),
            'replacement_values': dict(replacements), 'evaluator_calls': 2}


def audit_relevance(world: DevWorld, evaluator: Evaluator,
                    admissible_values: Iterable[int]) -> dict[str, Any]:
    values = tuple(admissible_values)
    if not values or len(set(values)) != len(values) or any(type(v) is not int for v in values):
        raise ValueError('need a finite distinct integer intervention alphabet')
    base = tuple(evaluator(world))
    calls, actual, witnesses = 1, [], {}
    for cell in world.comparative_cells:
        alternatives = []
        for value in values:
            if value == cell.value:
                continue
            changed = replace(world, comparative_cells=tuple(
                replace(c, value=value) if c.cell_id == cell.cell_id else c for c in world.comparative_cells))
            after = tuple(evaluator(changed))
            calls += 1
            if after != base:
                alternatives.append({'replacement': value, 'before': base, 'after': after})
        if alternatives:
            actual.append(cell.cell_id)
            witnesses[cell.cell_id] = alternatives
    declared = [c.cell_id for c in world.comparative_cells if c.action_relevant]
    return {'world_index': world.world_index, 'actual_relevant_cell_ids': actual,
            'declared_relevant_cell_ids': declared,
            'declared_relevance_matches': set(actual) == set(declared),
            'eligible_matched_corruption_design': bool(actual) and len(actual) < len(world.comparative_cells),
            'evaluations': calls, 'admissible_values': values, 'separating_witnesses': witnesses,
            'scope': 'complete single-cell interventions over specified finite alphabet'}


# --- Executed structural G design ---

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from math import floor

from .exchangeability import audit_joint_law
from .manifest import derive_dev_seed


_STRUCTURAL_DOSES = (0.1, 0.25, 0.5, 1.0)
_DOSE_WEIGHTS = {0.1: 2, 0.25: 5, 0.5: 10, 1.0: 20}


@dataclass(frozen=True)
class StructuralGCell:
    cell_id: str
    pair_id: str
    pair_index: int
    side: str
    value: int
    action_relevant: bool


@dataclass(frozen=True)
class StructuralGWorld:
    world_index: int
    seed_digest: str
    assignment: int
    actions: tuple[str, str, str, str]
    comparative_cells: tuple[StructuralGCell, ...]
    pair_order: tuple[str, ...]
    base_world_digest: str


def _structural_base(world_index: int) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    if type(world_index) is not int or world_index < 0:
        raise ValueError('world_index must be a nonnegative integer')
    seed = derive_dev_seed('G', 'structural-world-base', world_index, 'abgp-g-structural-v1')
    actions = tuple(f'g_{seed[:8]}_a{i}' for i in range(4))
    pair_ids = tuple(f'g_{seed[:8]}_pair_{i:02d}' for i in range(10))
    pair_order = tuple(sorted(pair_ids, key=lambda pid: sha256(f'{seed}|select|{pid}'.encode()).hexdigest()))
    payload = (seed, actions, pair_ids, tuple((pid, 0, 0) for pid in pair_ids), pair_order)
    base_digest = sha256(repr(payload).encode('utf-8')).hexdigest()
    return seed, actions, pair_ids, pair_order, base_digest


def make_structural_g_world(world_index: int, assignment: int | None = None) -> StructuralGWorld:
    seed, actions, pair_ids, pair_order, base_digest = _structural_base(world_index)
    if assignment is None:
        assignment_seed = derive_dev_seed(
            'G', 'structural-world-label-assignment', world_index, 'abgp-g-structural-v1'
        )
        assignment = int(assignment_seed[:2], 16) & 1
    if assignment not in (0, 1):
        raise ValueError('assignment must be 0 or 1')
    cells = []
    for pair_index, pair_id in enumerate(pair_ids):
        for side_index, side in enumerate(('L', 'R')):
            relevant = side_index == assignment
            cells.append(
                StructuralGCell(
                    cell_id=f'{pair_id}_{side}',
                    pair_id=pair_id,
                    pair_index=pair_index,
                    side=side,
                    value=0,
                    action_relevant=relevant,
                )
            )
    return StructuralGWorld(
        world_index=world_index,
        seed_digest=seed,
        assignment=int(assignment),
        actions=actions,  # type: ignore[arg-type]
        comparative_cells=tuple(cells),
        pair_order=pair_order,
        base_world_digest=base_digest,
    )


def structural_order(world: StructuralGWorld, *, evaluator_mode: str = 'cell_causal') -> tuple[str, ...]:
    if evaluator_mode not in ('cell_causal', 'registered_sharp_null'):
        raise ValueError('unknown structural G evaluator mode')
    if evaluator_mode == 'cell_causal':
        contributing = [cell for cell in world.comparative_cells if cell.action_relevant and cell.value]
    else:
        # Nested sharp-null restriction of the same finite evaluator family:
        # the relevance assignment has no causal effect, so both physical sides
        # contribute identically. This is executed from the same world object.
        contributing = [cell for cell in world.comparative_cells if cell.value]
    if not contributing:
        return tuple(world.actions)
    score = sum((cell.pair_index + 1) * int(cell.value) for cell in contributing)
    shift = 1 + (score % 3)
    actions = tuple(world.actions)
    return actions[shift:] + actions[:shift]


def audit_structural_relevance(world: StructuralGWorld) -> dict[str, Any]:
    result = audit_relevance(
        world,
        lambda candidate: structural_order(candidate, evaluator_mode='cell_causal'),
        (0, 1),
    )
    result['relevance_assignment'] = world.assignment
    result['computed_before_corruption'] = True
    result['protected_evaluator'] = 'structural_order/cell_causal'
    return result


def _selected_pair_ids(world: StructuralGWorld, dose: float) -> tuple[str, ...]:
    if dose not in _STRUCTURAL_DOSES:
        raise ValueError('dose is not preregistered')
    count = floor(dose * len(world.pair_order))
    if count <= 0:
        raise ValueError('nonzero dose must select at least one pair')
    return world.pair_order[:count]


def _selected_cells(world: StructuralGWorld, pair_ids: Sequence[str], *, relevant: bool) -> tuple[StructuralGCell, ...]:
    selected = set(pair_ids)
    rows = tuple(
        cell
        for cell in world.comparative_cells
        if cell.pair_id in selected and cell.action_relevant is relevant
    )
    if len(rows) != len(selected):
        raise AssertionError('matched-pair selection did not choose exactly one side per pair')
    return rows


def _dose_record(world: StructuralGWorld, dose: float, *, evaluator_mode: str = 'cell_causal') -> dict[str, Any]:
    pair_ids = _selected_pair_ids(world, dose)
    relevant_cells = _selected_cells(world, pair_ids, relevant=True)
    irrelevant_cells = _selected_cells(world, pair_ids, relevant=False)
    evaluator = lambda candidate: structural_order(candidate, evaluator_mode=evaluator_mode)
    relevant = evaluate_corruption(
        world, evaluator, {cell.cell_id: 1 for cell in relevant_cells}
    )
    irrelevant = evaluate_corruption(
        world, evaluator, {cell.cell_id: 1 for cell in irrelevant_cells}
    )
    return {
        'dose': dose,
        'weight': _DOSE_WEIGHTS[dose],
        'selected_pair_ids': list(pair_ids),
        'matched_count': len(relevant_cells) == len(irrelevant_cells) == len(pair_ids),
        'corruption_magnitude': 1,
        'relevant_cell_ids': [cell.cell_id for cell in relevant_cells],
        'irrelevant_cell_ids': [cell.cell_id for cell in irrelevant_cells],
        'relevant': relevant,
        'irrelevant': irrelevant,
        'relevant_flip': relevant['flip'],
        'irrelevant_flip': irrelevant['flip'],
    }


def audit_g_randomization_design(world_index: int) -> dict[str, Any]:
    worlds = (make_structural_g_world(world_index, assignment=0),
              make_structural_g_world(world_index, assignment=1))
    same_base = worlds[0].base_world_digest == worlds[1].base_world_digest
    same_pair_order = worlds[0].pair_order == worlds[1].pair_order
    selections = [
        tuple(tuple(_selected_pair_ids(world, dose)) for dose in _STRUCTURAL_DOSES)
        for world in worlds
    ]
    pair_selection_same = selections[0] == selections[1]

    null_vectors = []
    for world in worlds:
        records = [_dose_record(world, dose, evaluator_mode='registered_sharp_null')
                   for dose in _STRUCTURAL_DOSES]
        null_vectors.append(
            tuple((record['relevant_flip'], record['irrelevant_flip']) for record in records)
        )
    law = [(null_vectors[0], Fraction(1, 2)), (null_vectors[1], Fraction(1, 2))]
    law_audit = audit_joint_law(law)
    valid = (
        same_base
        and same_pair_order
        and pair_selection_same
        and law_audit['exchangeable']
    )
    return {
        'world_index': world_index,
        'randomization_unit': 'world',
        'assignment_support': ['left-side-relevant', 'right-side-relevant'],
        'assignment_probabilities': ['1/2', '1/2'],
        'assignment_generated_before_outcomes': True,
        'same_base_world_under_both_assignments': same_base,
        'pair_selection_identical_under_label_swap': pair_selection_same,
        'fixed_complete_dose_schedule': True,
        'no_adaptive_stopping': True,
        'registered_sharp_null': (
            'relevance assignment has no causal effect on the complete paired '
            'within-world outcome vector; physical sides are otherwise generated symmetrically'
        ),
        'null_potential_vectors': [[list(pair) for pair in vector] for vector in null_vectors],
        'null_law_exchangeable': bool(law_audit['exchangeable']),
        'null_law_audit': law_audit,
        'randomization_valid_under_registered_sharp_null': valid,
        'scope': (
            'finite generated paired-cell design with one fair world-level role assignment; '
            'not a theorem about arbitrary observational relevance labels'
        ),
    }


def run_structural_g_world(world_index: int) -> dict[str, Any]:
    world = make_structural_g_world(world_index)
    relevance = audit_structural_relevance(world)
    if not relevance['declared_relevance_matches']:
        raise AssertionError('pre-corruption relevance labels disagree with executed evaluator')
    design = audit_g_randomization_design(world_index)
    if not design['randomization_valid_under_registered_sharp_null']:
        raise AssertionError('G randomization design failed its exact sharp-null audit')
    records = [_dose_record(world, dose) for dose in _STRUCTURAL_DOSES]
    return {
        'schema': 'abgp.executed-g-world.v1',
        'mode': 'DEV_MECHANISM_ONLY',
        'world_index': world_index,
        'base_world_digest': world.base_world_digest,
        'assignment': world.assignment,
        'evaluator_mode': 'cell_causal',
        'relevance_audit': relevance,
        'randomization_design_audit': design,
        'dose_records': records,
        'max_dose_relevant_flip': records[-1]['relevant_flip'],
        'max_dose_irrelevant_flip': records[-1]['irrelevant_flip'],
        'confirmatory_namespace_used': False,
    }


def run_structural_g_batch(world_count: int) -> dict[str, Any]:
    if type(world_count) is not int or world_count <= 0:
        raise ValueError('world_count must be positive')
    worlds = [run_structural_g_world(index) for index in range(world_count)]
    pairs = []
    max_relevant = []
    max_irrelevant = []
    for world in worlds:
        for record in world['dose_records']:
            pairs.append({
                'world_id': world['world_index'],
                'weight': record['weight'],
                'relevant': record['relevant_flip'],
                'irrelevant': record['irrelevant_flip'],
            })
        max_relevant.append(world['max_dose_relevant_flip'])
        max_irrelevant.append(world['max_dose_irrelevant_flip'])
    exchangeability = all(
        world['randomization_design_audit']['randomization_valid_under_registered_sharp_null']
        for world in worlds
    )
    preclassified = all(world['relevance_audit']['computed_before_corruption'] for world in worlds)
    matched = all(
        record['matched_count']
        for world in worlds
        for record in world['dose_records']
    )
    return {
        'schema': 'abgp.executed-g-batch.v1',
        'mode': 'DEV_MECHANISM_ONLY',
        'worlds': worlds,
        'analysis_input': {
            'pairs': pairs,
            'max_dose_relevant': max_relevant,
            'max_dose_irrelevant': max_irrelevant,
            'hard_gates': {
                'world_exchangeability_contract': exchangeability,
                'preclassified': preclassified,
                'matched_corruption': matched,
                'nonzero_dose_nonempty': True,
                'same_evaluator': True,
            },
        },
        'confirmatory_namespace_used': False,
    }
