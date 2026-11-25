"""Recover pinned author sources and prepare a bounded native monitor experiment."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

MODEL_REV = '133447a8943721eaa1d16acf1ba5845b67a98df1'
FRET_REV = 'cf0f913cc15c41705e803593297e89cd6056b839'
EXPORT_PATH = 'FRET_CoCoSim/5_nn/CoCoSim/cocosim_output/nn_12B_with_contracts_PP/nn_12B_with_contracts_PP.KIND2.lus'
EXPORT_SHA256 = '8dbf83197dd057721e89fabe655dd7412421075fd32afad32e7bb377eefd8ace'
NODES = ['int_to_int32', 'OTlore_call_23_000', 'delay_call_70_000', 'OT_call_19_000', 'spec225_operator_256_000']
CLOCK = ['__time_step = (0.0 -> ((pre (__time_step)) + 1.0));',
         '__nb_step = (0 -> ((pre (__nb_step)) + 1));']
HARNESS = '''
node native_scalar_monitor(delta:real) returns (
  active:bool; instant:bool; past_ok:bool; __time_step:real; __nb_step:int; clock_nonnegative:bool);
var first:bool;
let
  __time_step = (0.0 -> ((pre (__time_step)) + 1.0));
  __nb_step = (0 -> ((pre (__nb_step)) + 1));
  first = (true -> (pre false));
  active = OT_call_19_000(200, 0, first, __time_step, __nb_step);
  instant = spec225_operator_256_000(active, delta <= 10.0 and delta >= -35.0, __time_step, __nb_step);
  past_ok = instant and (true -> pre past_ok);
  clock_nonnegative = __time_step >= 0.0 and __nb_step >= 0;
  --%PROPERTY clock_nonnegative;
tel
'''


def git(cwd, *args):
    return subprocess.check_output(['git', *args], cwd=cwd)


def recover(root):
    for name, repository, revision in [('lm_challenges', 'hbourbouh/lm_challenges', MODEL_REV),
                                        ('aerospace', 'NASA-SW-VnV/fret', FRET_REV)]:
        path = root / 'sources' / name
        if not path.exists():
            path.mkdir(parents=True)
            git(path, 'init', '--bare')
            git(path, 'remote', 'add', 'origin', 'https://github.com/' + repository + '.git')
            git(path, 'config', 'remote.origin.promisor', 'true')
            git(path, 'config', 'remote.origin.partialclonefilter', 'blob:none')
            git(path, 'fetch', '--filter=blob:none', '--depth=1', 'origin', revision)
            git(path, 'update-ref', 'refs/heads/pinned', revision)
            git(path, 'symbolic-ref', 'HEAD', 'refs/heads/pinned')
        assert git(path, 'rev-parse', 'HEAD').decode().strip() == revision


def project(node):
    """Keep the range predicates; move assert syntax to compile-supported assumptions."""
    bounds = re.findall(r'(?m)^\s*assert\s+(.*);\s*$', node)
    if not bounds:
        return node, []
    result = re.sub(r'(?m)^\s*assert\s+.*;\s*$', '', node)
    position = result.index(');', result.index('returns(')) + 2
    contract = '\n(*@contract\n' + ''.join('assume "original_range_' + str(i) + '" ' + bound + ';\n'
                                           for i, bound in enumerate(bounds)) + '*)\n'
    return result[:position] + contract + result[position:], bounds


def prepare(root, out):
    out.mkdir(parents=True, exist_ok=True)
    recover(root)
    qualifier_path = Path(__file__).resolve().parents[1] / 'verify_clock_sources.py'
    spec = importlib.util.spec_from_file_location('clock_source_auditor', qualifier_path)
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    qualification = auditor.audit(root)
    (out / 'clock_source_qualification.json').write_text(json.dumps(qualification, indent=2) + '\n')
    source = git(root / 'sources/lm_challenges', 'show', MODEL_REV + ':' + EXPORT_PATH)
    assert hashlib.sha256(source).hexdigest() == EXPORT_SHA256
    (out / 'original_export.lus').write_bytes(source)
    text = source.decode()
    nodes = {}
    for match in re.finditer(r'(?m)^node\s+([A-Za-z_][A-Za-z_0-9]*)\s*\(', text):
        finish = re.search(r'(?m)^tel\b', text[match.end():])
        assert finish is not None
        end = match.end() + finish.end()
        nodes[match.group(1)] = (match.start(), end, text[match.start():end])
    originals, projected, receipts = [], [], []
    for name in NODES:
        start, end, node = nodes[name]
        compiled, bounds = project(node)
        originals.append(node)
        projected.append(compiled)
        receipts.append({'node': name, 'source_start_byte': start, 'source_end_byte': end,
                         'original_sha256': hashlib.sha256(node.encode()).hexdigest(),
                         'projected_sha256': hashlib.sha256(compiled.encode()).hexdigest(),
                         'range_predicates_moved_to_contract_assumptions': bounds})
    for equation in CLOCK:
        assert text.count(equation) == 1 and equation in HARNESS
    checks = {
        'top_calls_network_with_clock': 'nn_2x10x10x1_392_000(x_1, y_1, __time_step, __nb_step)' in text,
        'network_imports_contract_with_clock': 'import nn_12B_NNSpec_4_000(x_1, y_1, __time_step, __nb_step) returns (z_1);' in text,
        'contract_calls_200_step_operator': 'OT_call_19_000(200, 0, branch_8_IF_1, __time_step, __nb_step)' in text,
        'contract_uses_expected_slope_predicate': 'spec225_operator_256_000(OT_call_1, ( (branch_9_IF_1 <= 10.0) ) and ( (branch_9_IF_1 >= -35.0) ), __time_step, __nb_step)' in text,
        'contract_has_matching_clock_assumption': 'assume "TIME_STEP" (__time_step = (0.0 -> ((pre (__time_step)) + 1.0)));' in text,
    }
    assert all(checks.values())
    (out / 'temporal_original_slice.lus').write_text('\n\n'.join(originals) + '\n' + HARNESS)
    (out / 'temporal_compile_projection.lus').write_text('\n\n'.join(projected) + '\n' + HARNESS)
    (out / 'clock_miter.lus').write_text('node clock_miter() returns (__time_step:real; __nb_step:int; clock_ok:bool);\nlet\n' +
                                       '\n'.join(CLOCK) + '\nclock_ok = __time_step = real __nb_step;\n--%PROPERTY clock_ok;\ntel\n')
    receipt = {'source_commit': MODEL_REV, 'source_path': EXPORT_PATH, 'source_sha256': EXPORT_SHA256,
               'copied_nodes': receipts, 'clock_equations_copied_exactly': CLOCK,
               'source_level_binding_checks': checks,
               'scope': 'Exact temporal helper slice plus new scalar-observation harness; not the complete NN/dataset/differencing model.',
               'projection': 'The same range predicates are retained as named contract assumptions. Native caller-assumption proofs and finite original/projected comparisons must pass.',
               'fresh_simulink_build': 'NOT_EXECUTED'}
    (out / 'source_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'prepared': str(out), 'source_sha256': EXPORT_SHA256, 'source_binding_checks': checks}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.root.resolve(), args.out.resolve())
