"""Finite reference observations; no hosted repair authorization."""
import json
from pathlib import Path
import subprocess
import copy
import hashlib
import platform
import tempfile
import argparse

ROOT = Path(__file__).resolve().parent
COHORT = json.loads((ROOT / 'cohort.json').read_text())
BASH = Path('/bin/bash').resolve()
TRUSTED_COMMANDS = {c['command'] for c in COHORT['cases']} | {
    c['command'] for c in COHORT['controls'].values()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def context():
    try:
        bash_hash = hashlib.sha256(BASH.read_bytes()).hexdigest()
    except OSError:
        bash_hash = None
    return {'cohort_sha256': digest(COHORT),
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'bash_sha256': bash_hash,
            'subject_sha256': digest(COHORT['subject']),
            'requirements_sha256': digest([c['authority'] for c in COHORT['cases']]),
            'assumptions_sha256': digest(COHORT['assumptions']),
            'environment': {'python': platform.python_version(), 'system': platform.system(),
                            'machine': platform.machine(), 'LC_ALL': 'C', 'PATH': '/usr/bin:/bin',
                            'bash_flags': ['--noprofile', '--norc']}}


def capture(command):
    """Execute only trusted frozen literals, never a model-provided shell command."""
    if command not in TRUSTED_COMMANDS:
        return {'status': 'UNSUPPORTED', 'calls': [], 'exit': None}
    prelude = '''exec 3> "$1"
python3() {
  printf '%s\\0' "$#" >&3
  for arg in "$@"; do printf '%s\\0' "$arg" >&3; done
  return 0
}
'''
    with tempfile.TemporaryDirectory(prefix='mathgraph-shell-oracle-') as tmp:
        trace = Path(tmp) / 'argv.bin'
        try:
            r = subprocess.run([str(BASH), '--noprofile', '--norc', '-c',
                                prelude + command, 'mathgraph-oracle', str(trace)],
                               cwd=tmp, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'},
                               capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            return {'status': 'TIMEOUT', 'calls': [], 'exit': None}
        except OSError as e:
            return {'status': 'UNAVAILABLE', 'calls': [], 'exit': None, 'diagnostic': str(e)}
        result = {'status': 'CRASH' if r.returncode < 0 else 'ERROR' if r.returncode else 'OK',
                  'calls': [], 'exit': r.returncode, 'stderr': r.stderr.decode(errors='replace')}
        if r.returncode:
            return result
        try:
            raw = trace.read_bytes()
            tokens = raw.decode('utf-8').split('\0')
            if tokens.pop() != '':
                raise ValueError('unterminated trace')
            i = 0
            while i < len(tokens):
                count = int(tokens[i])
                if count < 0 or i + 1 + count > len(tokens):
                    raise ValueError('invalid argument count')
                result['calls'].append(tokens[i + 1:i + 1 + count])
                i += count + 1
        except (OSError, ValueError, UnicodeError) as e:
            result.update(status='MALFORMED', calls=[], diagnostic=str(e))
        return result


def evaluate(case_id, proposal=None, required_context=None):
    case = next((c for c in COHORT['cases'] if c['id'] == case_id), None)
    ctx = context()
    result = {'Subject': copy.deepcopy(COHORT['subject']),
              'Obligation': copy.deepcopy(case), 'Relation': COHORT['relation'],
              'Verification': {'method': 'Bash function interception, repeated finite replay',
                               'execution': {'status': 'NOT_RUN', 'calls': [], 'exit': None},
                               'assumptions': COHORT['assumptions']},
              'Conclusion': {'status': 'UNKNOWN', 'reason': 'PROPOSAL_OUTSIDE_FROZEN_SCOPE',
                             'repair_authorized': False}, 'Dependencies': ctx}
    def finish(reason, status='UNKNOWN'):
        result['Conclusion'].update(status=status, reason=reason)
        return result
    if case is None or (proposal is not None and proposal != case):
        return result
    if ctx['bash_sha256'] is None:
        return finish('REFERENCE_IDENTITY_UNAVAILABLE')
    if required_context is not None and required_context != ctx:
        return finish('CONTEXT_CHANGED')
    if case['authority']['state'] != 'DECLARED' or not case['authority']['reference']:
        return finish('REQUIREMENT_NOT_ADMITTED')
    controls = {name: capture(c['command']) for name, c in COHORT['controls'].items()}
    result['Verification']['controls'] = controls
    if any(controls[k]['status'] != 'OK' or controls[k]['calls'] != v['calls']
           for k, v in COHORT['controls'].items()):
        return finish('REFERENCE_CONTROL_FAILED')
    first, repeat = capture(case['command']), capture(case['command'])
    result['Verification'].update(execution=first, repeat=repeat)
    if first['status'] != 'OK' or repeat['status'] != 'OK':
        return finish('REFERENCE_EXECUTION_INCOMPLETE')
    if first['calls'] != repeat['calls']:
        return finish('REFERENCE_NOT_REPEATABLE')
    if first['calls'] != case['expected_calls']:
        return finish('REFERENCE_CONTRADICTS_EXPECTATION', 'REJECTED')
    return finish('FINITE_REFERENCE_AGREEMENT', 'SUPPORTED')


def run_cohort():
    rows = [evaluate(c['id']) for c in COHORT['cases']]
    return {'calibration': COHORT['calibration'], 'records': rows,
            'counts': {s: sum(r['Conclusion']['status'] == s for r in rows)
                       for s in ['SUPPORTED', 'REJECTED', 'UNKNOWN']},
            'anticipated_labels_match': all(r['Conclusion']['status'] == c['anticipated_admission']
                                             for r, c in zip(rows, COHORT['cases']))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(run_cohort(), indent=2) + '\n')
