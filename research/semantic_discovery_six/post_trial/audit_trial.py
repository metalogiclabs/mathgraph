"""Mechanical audit, run only after both final results are locked.

This checks identities, accounting and retained audit material, not semantics.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys


def audit(trial):
    for arm in ('mathgraph', 'conventional'):
        if not (trial / arm / 'results/final.sha256').is_file():
            raise ValueError('BOTH_FINAL_LOCKS_REQUIRED')
    selection = json.loads((trial / 'selection_receipt.json').read_text())
    expected = {c['case_id']: c['input_sha256'] for c in selection['cases']}
    invocation = json.loads((trial / 'invocation_receipt.json').read_text())
    report = {'freeze_commit': selection['freeze_commit'], 'case_count': len(expected), 'arms': {}}
    for arm in ('mathgraph', 'conventional'):
        root = trial / arm
        for case, digest in expected.items():
            assert sha256((root / 'inputs' / (case + '.json')).read_bytes()).hexdigest() == digest
        assert sha256((root / 'kit/instructions.txt').read_bytes()).hexdigest() == invocation[arm]['instructions_sha256']
        final = root / 'results/final.json'
        actual_digest = sha256(final.read_bytes()).hexdigest()
        assert (root / 'results/final.sha256').read_text().split()[0] == actual_digest
        assert (root / 'results/.final.lock').read_text().strip() == actual_digest
        value = json.loads(final.read_text())
        assert isinstance(value.get('cases'), list)
        ids = [c['case_id'] for c in value['cases']]
        assert len(ids) == len(expected) and set(ids) == set(expected)
        events = [json.loads(x) for x in (root / 'journal.jsonl').read_text().splitlines()]
        starts = {e['request_id']: e for e in events if e['phase'] == 'start'}
        ends = {e['request_id']: e for e in events if e['phase'] == 'end'}
        assert len(starts) == len(ends) and starts.keys() == ends.keys()
        assert len(starts) * 2 == len(events)
        credits = Counter()
        for e in starts.values():
            credits[e['case']] += e['credits']
        for case, count in credits.items():
            assert case in expected or case == 'shared'
            assert count <= (12 if case == 'shared' else 24)
        blobs = root / 'results/.broker-audit/blobs'
        verified_blobs = 0
        for f in blobs.iterdir():
            assert f.is_file() and sha256(f.read_bytes()).hexdigest() == f.name
            verified_blobs += 1
        snapshots = list((root / 'results/.broker-audit/runs').glob('*.json'))
        for f in snapshots:
            v = json.loads(f.read_text())
            for entry in v['entries'].values():
                if entry['type'] == 'file':
                    b = root / entry['path'] if entry['path'].startswith('results/') else None
                    # Blob references use audit paths; entry names are keys in entries.
                    assert b is not None and b.is_file()
                    assert sha256(b.read_bytes()).hexdigest() == entry['sha256']
        end_values = list(ends.values())
        report['arms'][arm] = {
            'final_sha256': actual_digest, 'requests': len(starts),
            'actions': dict(Counter(e['action'] for e in starts.values())),
            'credits_by_case': dict(credits), 'total_credits': sum(credits.values()),
            'failed_requests': sum(not e['ok'] for e in end_values),
            'input_bytes': sum(e['input_bytes'] for e in starts.values()),
            'output_bytes': sum(e['output_bytes'] for e in end_values),
            'written_bytes_including_versions': sum(e['written_bytes'] for e in end_values),
            'audit_written_bytes': sum(e['audit_written_bytes'] for e in end_values),
            'broker_execution_seconds': sum(e['elapsed_seconds'] for e in end_values),
            'journal_span_seconds': (max(e['wall_end_ns'] for e in end_values) - min(e['wall_start_ns'] for e in starts.values())) / 1e9,
            'verified_content_blobs': verified_blobs, 'retained_snapshots': len(snapshots),
            'unmeasured_costs': ['model tokens', 'monetary cost', 'pre-first-broker model reasoning'],
        }
    (trial / 'mechanical_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    audit(Path(sys.argv[1]).resolve())
