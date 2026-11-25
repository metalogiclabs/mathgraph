"""Execute the generated monitor and check every output against the independent oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from oracle import cases, validate_certificate, STEPS, WINDOW_SECONDS


def replay(artifact, out, binary=None):
    out.mkdir(parents=True, exist_ok=True)
    transcripts = out / 'transcripts'
    transcripts.mkdir(exist_ok=True)
    manifest = (artifact / 'MANIFEST.sha256').read_text().splitlines()
    for line in manifest:
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((artifact / name).read_bytes()).hexdigest() == digest
    if binary is None:
        binary = artifact / 'rust-codegen/native_scalar_monitor/implem/target/release/native_scalar_monitor_implem'
    binary.chmod(binary.stat().st_mode | 0o100)
    certificate = {'scope': 'SCALAR_TEMPORAL_SLICE_204_TICKS_UNIT_SECONDS',
                   'steps': STEPS, 'window_seconds': WINDOW_SECONDS,
                   'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'cases': []}
    commands = []
    start = time.monotonic()
    for case in cases():
        # The generated CLI recognizes its clean exit command after CSV splitting.
        data = ''.join(str(v) + '\n' for v in case['values']) + 'exit,\n'
        begin = time.monotonic()
        result = subprocess.run([str(binary)], input=data, text=True, capture_output=True, timeout=5)
        prefix = transcripts / case['id']
        prefix.with_suffix('.stdin').write_text(data)
        prefix.with_suffix('.stdout').write_text(result.stdout)
        prefix.with_suffix('.stderr').write_text(result.stderr)
        record = {'case_id': case['id'], 'exit_code': result.returncode,
                  'wall_seconds': time.monotonic() - begin,
                  'stdin_sha256': hashlib.sha256(data.encode()).hexdigest(),
                  'stdout_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
                  'stderr_sha256': hashlib.sha256(result.stderr.encode()).hexdigest()}
        commands.append(record)
        (out / 'native_commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if result.returncode != 0 or result.stderr:
            raise RuntimeError('NATIVE_EXECUTION_FAILED:' + case['id'])
        rows = []
        for line in result.stdout.splitlines():
            fields = [value.strip() for value in line.split(',')]
            if len(fields) != 6 or any(fields[i] not in ['true', 'false'] for i in [0, 1, 2, 5]):
                raise ValueError('NATIVE_OUTPUT_SCHEMA_MISMATCH')
            rows.append({'active': fields[0] == 'true', 'instant': fields[1] == 'true',
                         'past_ok': fields[2] == 'true', 'time': fields[3],
                         'step': int(fields[4]), 'clock_nonnegative': fields[5] == 'true'})
        certificate['cases'].append(dict(case, native=rows))
    verdict = validate_certificate(certificate)
    (out / 'native_certificate.json').write_text(json.dumps(certificate) + '\n')
    summary = dict(verdict, status='WARRANTED_BOUNDED_NATIVE_FINITE_COHORT',
                   binary_sha256=certificate['binary_sha256'],
                   certificate_sha256=hashlib.sha256((out / 'native_certificate.json').read_bytes()).hexdigest(),
                   total_wall_seconds=time.monotonic() - start,
                   native_process_seconds=sum(r['wall_seconds'] for r in commands),
                   full_nn_requirement='UNKNOWN', fresh_simulink_build='NOT_EXECUTED')
    (out / 'replay_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)
    return certificate, summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--binary', type=Path)
    args = parser.parse_args()
    replay(args.artifact.resolve(), args.out.resolve(), args.binary.resolve() if args.binary else None)
