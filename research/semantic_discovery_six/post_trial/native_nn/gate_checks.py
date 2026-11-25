"""Qualify finite receipts before testing scoped evidence withdrawal.

This is an operator-authored post-trial control experiment, not a new blinded
comparison. The resolver's trusted-caller admission boundary remains explicit.
"""
import argparse
import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from host_codegen import check_analysis_report
from oracle import validate_certificate, expected
from replay_binary import replay


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def controls(artifact, certificate_path, source_root, repo, out):
    out.mkdir(parents=True, exist_ok=True)
    certificate = json.loads(certificate_path.read_text())
    verification = validate_certificate(certificate)
    repeated, repeated_summary = replay(artifact, out / 'independent-execution')
    assert repeated['cases'] == certificate['cases']
    assert repeated['binary_sha256'] == certificate['binary_sha256']
    for name in ['clock-miter-proof.stdout', 'monitor-proof-and-codegen.stdout']:
        check_analysis_report((artifact / 'native-logs' / name).read_text())
    source = artifact / 'original_export.lus'
    source_receipt = json.loads((artifact / 'source_receipt.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_receipt['source_sha256'] == '8dbf83197dd057721e89fabe655dd7412421075fd32afad32e7bb377eefd8ace'
    assert all(source_receipt['source_level_binding_checks'].values())
    auditor = load_module('native_source_clock_auditor', Path(__file__).resolve().parents[1] / 'verify_clock_sources.py')
    assert auditor.audit(source_root) == json.loads((artifact / 'clock_source_qualification.json').read_text())
    m = load_module('native_warrant_resolution', repo / 'mathgraph_check/warrant_resolution.py')
    scope = 'exact-scalar-monitor-cohort:' + hashlib.sha256(certificate_path.read_bytes()).hexdigest()
    documentary_scope = 'linked-NN-verification-configuration:133447a8943721eaa1d16acf1ba5845b67a98df1'
    claims = [m.Claim('native_ticks', 'formal', scope), m.Claim('clock_equations', 'formal', scope),
              m.Claim('author_clock', 'documentary', documentary_scope),
              m.Claim('sampled_seconds', 'formal', scope), m.Claim('whole_NN_requirement', 'formal', scope)]
    receipts = [m.Receipt(name, 'formal', scope) for name in ['native', 'clock-proof', 'export-binding', 'adapter', 'transfer']]
    receipts.append(m.Receipt('author-clock', 'documentary', documentary_scope))
    route = m.Route('sampled_seconds', ('transfer',), ('native_ticks', 'clock_equations', 'author_clock'), 'clock-adapter')
    relation = m.QualifiedRelation('clock-adapter', 'documentary', documentary_scope, 'formal', scope,
                                   'adapter', ('transfer',), route)
    routes = [m.Route('native_ticks', ('native',)), m.Route('clock_equations', ('clock-proof', 'export-binding')),
              m.Route('author_clock', ('author-clock',)), route]

    def ledger(withdrawn):
        live = {r.id for r in receipts} - set(withdrawn)
        boolean = {'native_ticks': 'native' in live,
                   'clock_equations': {'clock-proof', 'export-binding'} <= live,
                   'author_clock': 'author-clock' in live,
                   'sampled_seconds': {r.id for r in receipts} <= live,
                   'whole_NN_requirement': False}
        return {key: ('SOURCE_DOCUMENTED' if key == 'author_clock' else 'WARRANTED_BOUNDED')
                if value else 'UNKNOWN' for key, value in boolean.items()}

    base = m.resolve_graph(claims, routes, receipts, relations=[relation])
    snapshots = []
    scenarios = [('qualified', frozenset())] + [('withdraw-' + r.id, frozenset([r.id])) for r in receipts] + [('restore-author-clock', frozenset())]
    for name, withdrawn in scenarios:
        resolved = m.resolve_graph(claims, routes, receipts, relations=[relation], withdrawn=withdrawn)
        assert dict(resolved.states) == ledger(withdrawn)
        snapshots.append({'scenario': name, 'withdrawn': sorted(withdrawn), 'states': dict(resolved.states),
                          'changes_from_qualified': m.compare_snapshots(base.states, resolved.states)})
    withdrawal = next(s for s in snapshots if s['scenario'] == 'withdraw-author-clock')
    assert withdrawal['states']['native_ticks'] == 'WARRANTED_BOUNDED'
    assert withdrawal['states']['clock_equations'] == 'WARRANTED_BOUNDED'
    assert withdrawal['states']['sampled_seconds'] == 'UNKNOWN'
    assert withdrawal['changes_from_qualified']['sampled_seconds']['after'] == 'STALE'
    assert all(s['states']['whole_NN_requirement'] == 'UNKNOWN' for s in snapshots)
    negatives = []
    corrupted = copy.deepcopy(certificate)
    corrupted['cases'][0]['native'][201]['active'] = True
    try:
        validate_certificate(corrupted)
    except ValueError as error:
        negatives.append({'control': 'corrupted-native-certificate', 'result': 'REJECTED_ADMISSION', 'reason': str(error)})
    else:
        raise AssertionError('CORRUPTED_CERTIFICATE_ADMITTED')
    changed = dict(certificate, window_seconds=201)
    try:
        validate_certificate(changed)
    except ValueError as error:
        negatives.append({'control': 'changed-formal-window', 'result': 'REJECTED_ADMISSION', 'reason': str(error)})
    else:
        raise AssertionError('CHANGED_STATEMENT_ADMITTED')
    witnesses = []
    by_id = {c['id']: c for c in certificate['cases']}
    for name, tick, period, window in [('window-201', 201, Fraction(1), 201),
                                       ('half-second-clock', 201, Fraction(1, 2), 200),
                                       ('two-second-clock', 101, Fraction(2), 200)]:
        case = by_id['single-' + str(tick) + '-11']
        wanted = expected(case['values'], seconds_per_tick=period, window_seconds=window)[tick]
        native = case['native'][tick]
        assert native['instant'] != wanted['instant']
        witnesses.append({'control': name, 'classification': 'FINITE_COUNTERMODEL_TO_HYPOTHETICAL_TRANSFER',
                          'case_id': case['id'], 'tick': tick, 'delta': 11,
                          'alternative_seconds_per_tick': str(period), 'alternative_window_seconds': window,
                          'native_instant': native['instant'], 'alternative_requirement_instant': wanted['instant'],
                          'not_an_observation_of_changed_NASA_model': True})
    result = {'status': 'PASSED_BOUNDED_ADMISSION_AND_WITHDRAWAL_CONTROLS', 'native_verification': verification,
              'fresh_execution_before_admission': repeated_summary, 'snapshots': snapshots,
              'negative_admission_controls': negatives, 'semantic_transfer_witnesses': witnesses,
              'conventional_ledger_matches_every_snapshot': True,
              'scope': 'Only the declared scalar temporal cohort under the exact linked source clock; no whole-NN or deployment guarantee.',
              'trusted_boundary': 'Caller admission qualifies native replay, source identities and the documentary seconds interpretation before constructing receipts. The resolver does not authenticate evidence.',
              'comparative_architectural_or_economic_advantage': 'NOT_ESTABLISHED'}
    (out / 'warrant_controls.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'state_snapshots': len(snapshots),
                      'negative_admission_controls': len(negatives), 'semantic_transfer_witnesses': len(witnesses),
                      'ledger_parity': True}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--certificate', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    controls(args.artifact.resolve(), args.certificate.resolve(), args.source_root.resolve(), args.repo.resolve(), args.out.resolve())
