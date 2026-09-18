"""Run auditable DEV mechanism checks. There is no confirmation mode."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from itertools import permutations
import json
from pathlib import Path
import tempfile
import time

from mathgraph.abgp.arm_b import generate_b_dev_records
from mathgraph.abgp.dev_world import make_dev_world
from mathgraph.abgp.executed_g import audit_relevance, legacy_world_order
from mathgraph.abgp.executed_p import execute_episode, run_worker, trace_p_episodes
from mathgraph.abgp.exchangeability import audit_joint_law
from mathgraph.abgp.manifest import load_design_manifest
from mathgraph.abgp.runner import run_dev_matrix


ROOT = Path(__file__).resolve().parent


def run_boundary_checks() -> dict:
    design = load_design_manifest(ROOT / 'preregistration/abgp-design-manifest-v1.json')
    if design.status not in ('REVIEW_PENDING', 'FROZEN') or design.confirmatory_execution_enabled:
        raise ValueError('boundary checks require REVIEW_PENDING/FROZEN manifest with confirmation disabled')
    normative_hashes = {name: sha256((ROOT / 'preregistration' / name).read_bytes()).hexdigest()
                       for name in ('abgp-design-manifest-v1.json', 'abgp-analysis-plan-v1.json')}
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as directory:
        canary = Path(directory) / 'source-examples-private.txt'
        canary.write_text('ACQUISITION_STATE_MUST_NOT_BE_READ')
        health = run_worker({'operation': 'probe', 'path': str(canary), 'fd': 99})
    if not all(row['blocked'] for row in health['probes'].values()):
        raise AssertionError('a prohibited system access succeeded')

    # Exhaust ALL possible policies. This is a finite mechanism proof-by-cases,
    # not 24 independent confirmatory observations and not a power estimate.
    episodes = [execute_episode(policy) for policy in permutations(range(4))]
    totals = {key: sum(e['scores'][key] for e in episodes)
              for key in ('retained', 'cold', 'deleted', 'reacquired', 'posterior')}
    if totals != {'retained': 24, 'cold': 1, 'deleted': 1, 'reacquired': 24, 'posterior': 24}:
        raise AssertionError('executed finite-policy results disagree with the independent truth evaluator')
    if any(e['runs']['acquire']['retained']['lineage'] != e['runs']['posterior']['information_digest'] for e in episodes):
        raise AssertionError('control and acquisition did not see identical source evidence')
    traced = trace_p_episodes(8)
    b_records = generate_b_dev_records(4)
    b_matches = sum(r.treatment_success == r.bisimulation_bayes_success for r in b_records)
    if b_matches != len(b_records):
        raise AssertionError('same-information finite oracle was weakened')
    g_audits = [audit_relevance(make_dev_world('G', i, 'abgp-g-dev-v1'), legacy_world_order, range(7)) for i in range(2)]
    if any(a['actual_relevant_cell_ids'] for a in g_audits):
        raise AssertionError('unexpected cell dependence in label-only legacy truth')
    symmetric = audit_joint_law([(((1, 0), (0, 0)), Fraction(1, 2)), (((0, 1), (0, 0)), Fraction(1, 2))])
    asymmetric = audit_joint_law([(((0, 0), (0, 1)), Fraction(1, 3)), (((0, 1), (1, 1)), Fraction(1, 3)), (((1, 0), (1, 0)), Fraction(1, 3))])
    if not symmetric['exchangeable'] or asymmetric['exchangeable']:
        raise AssertionError('joint probability audit accepted the wrong law')
    legacy_matrix = run_dev_matrix(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=8)
    verdicts = {a: legacy_matrix['analysis']['arms'][a]['verdict'] for a in ('A', 'B', 'G', 'P')}
    if any(v != 'INVALID' for v in verdicts.values()):
        raise AssertionError('a legacy fixture still masquerades as a valid executed study')
    return {
        'schema': 'abgp.executed-boundaries.v1', 'mode': 'DEV_MECHANISM_AND_CONTROL_QUALIFICATION',
        'status': 'MECHANISM_CHECKS_PASSED_FREEZE_BLOCKED',
        'implementation_qualified': False, 'complete_pass_power_qualified': False,
        'confirmatory_namespace_used': False, 'freeze_authorized': False,
        'normative_file_sha256': normative_hashes,
        'sandbox_health': health,
        'exhaustive_P': {'policy_count': 24, 'totals': totals, 'episodes': episodes,
                         'interpretation': 'restart/deletion execute, but same-information posterior explains this whole family'},
        'traced_P_development_batch': traced,
        'B_ordinary_control': {'records': [asdict(r) for r in b_records], 'matching_records': b_matches,
                               'record_count': len(b_records), 'interpretation': 'answer codecs are fully explained by exact source-history inference'},
        'G_actual_relevance_audit': g_audits,
        'G_exact_law_checks': {'symmetric': symmetric, 'equal_marginals_but_asymmetric_joint': asymmetric},
        'legacy_scientific_verdicts': verdicts,
        'elapsed_seconds': time.perf_counter() - started,
        'remaining_scientific_requirements': [
            'source-distinct retained capability beyond the solved policy-table family',
            'independent grammar generation and scoped information-matched B control',
            'cell-based protected evaluator and justified actual G null sampling law',
            'executed A construction under agreed channel boundary',
            'reviewed full-PASS power model and normative consistency',
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('abgp-executed-boundaries.json'))
    args = parser.parse_args()
    result = run_boundary_checks()
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    print('P exhaustive totals', result['exhaustive_P']['totals'])
    print('B matched-source posterior matches', result['B_ordinary_control']['matching_records'])
    print('G actual relevant cells', [len(a['actual_relevant_cell_ids']) for a in result['G_actual_relevance_audit']])
    print('legacy scientific verdicts', result['legacy_scientific_verdicts'])
    print('implementation_qualified 0')
    print('confirmatory_namespace_used 0')
    print('ABGP_EXECUTED_BOUNDARIES_OK')


if __name__ == '__main__':
    main()
