"""Exact-source operator-entry calibration and refusal controls; no remote writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT/'bin/mathgraph-check.mjs'
ORIGINAL = '791b3492ed8d6a7f39bd240837fc601ac491278e'
REPAIRED = '429c784f7267ce6b8a0b03c90c213b397282644b'
PROFILE = 'telemetry-integer-identity-v1'


def require(ok, reason):
    if not ok: raise RuntimeError(reason)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve(); out.mkdir()
    started = time.monotonic()
    summary = {'qualification': 'INCOMPLETE', 'runs': {}, 'operator_use': 'NOT_RUN',
               'comparative_value': 'NOT_RUN', 'boundary': 'Known-source finite operator-entry calibration'}
    def persist():
        summary['wall_seconds'] = time.monotonic()-started
        (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    persist()
    try:
        campaigns = [('original', ORIGINAL, ORIGINAL, 1, 29, 29, []),
                     ('repair', ORIGINAL, REPAIRED, 0, 29, 0, []),
                     ('withdrawal', REPAIRED, ORIGINAL, 1, 0, 29, []),
                     ('unchanged', REPAIRED, REPAIRED, 0, 0, 0, []),
                     ('missing-revision', REPAIRED, '0'*40, 2, 0, None, []),
                     ('missing-tool', REPAIRED, REPAIRED, 2, None, None,
                      ['--python', str(out/'deliberately-unavailable-python')])]
        for name, base, head, expected_exit, base_bad, head_bad, extra in campaigns:
            destination = out/name
            command = ['node', str(CLI), '--profile', PROFILE, '--repo', str(Path(args.repo).resolve()),
                       '--base', base, '--head', head, '--out', str(destination), *extra]
            p = subprocess.run(command, capture_output=True, text=True, timeout=330)
            (out/(name+'.log')).write_text(p.stdout+p.stderr)
            result = json.loads((destination/'result.json').read_text())
            require(p.returncode == expected_exit, name+': INCORRECT_EXIT')
            require(result['permission'] == 'ADVISORY_ONLY', name+': AUTHORITY_PROMOTION')
            require(result['release']['profile'] == PROFILE, name+': WRONG_PROFILE')
            require(result['release']['tracked_entry_clean'] is True, name+': UNCOMMITTED_OPERATOR_SOURCE')
            expected_status = 'UNKNOWN' if expected_exit == 2 else 'OBSERVED_MISMATCH' if head_bad else 'OBSERVED_AGREEMENT'
            require(result['status'] == expected_status, name+': INCORRECT_OUTCOME')
            for side, ref, wanted in [('base', base, base_bad), ('head', head, head_bad)]:
                arm = result[side]
                if wanted is None:
                    require(arm['complete'] is False and arm.get('reason'), name+': REFUSAL_NOT_UNKNOWN')
                    continue
                require(result['subjects'][side]['revision'] == ref, name+': SOURCE_IDENTITY')
                rows = arm['observations']
                require(arm['complete'] is True and len(rows) == 108 and len({r['id'] for r in rows}) == 108,
                        name+': INCOMPLETE_OBSERVATIONS')
                require(len(arm['mismatches']) == wanted and
                        arm['mismatches'] == [r['id'] for r in rows if not r['passed']], name+': WRONG_OBSERVATIONS')
                require(all(type(r['passed']) is bool for r in rows), name+': MISSING_CASE_OUTCOME')
                witness = next((r for r in rows if r['id'] == 'INT-8-integer'), None)
                require(witness and witness['expected_repr'] == '9007199254740993', name+': WRONG_INTEGER_REFERENCE')
            for path, digest in result['evidence'].items():
                require(hashlib.sha256((destination/path).read_bytes()).hexdigest() == digest,
                        name+': ARTIFACT_DIGEST_CHANGED')
            summary['runs'][name] = {'qualification': 'PASSED', 'exit': p.returncode,
                                     'status': result['status'], 'cost': result['cost'],
                                     'verifier': result['release']['commit']}
            persist()
        summary['qualification'] = 'PASSED';persist()
    except Exception as error:
        summary.update(qualification='FAILED', reason=str(error));persist();raise
    finally:
        inventory = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'inventory.json'}
        (out/'inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')


if __name__ == '__main__': main()
