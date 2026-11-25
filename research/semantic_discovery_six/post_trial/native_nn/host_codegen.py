"""Run native Kind 2 proofs and its Rust backend on a prepared scoped monitor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def qualify(kind2, z3, out):
    logs = out / 'native-logs'
    logs.mkdir(exist_ok=True)
    commands = []

    def run(name, argv, timeout=90, cwd=None):
        start = time.monotonic()
        process = subprocess.Popen(list(map(str, argv)), cwd=cwd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        for suffix, raw in [('stdout', stdout), ('stderr', stderr)]:
            (logs / (name + '.' + suffix)).write_bytes(raw)
        record = {'name': name, 'argv': list(map(str, argv)), 'exit_code': process.returncode,
                  'timed_out': timed_out, 'wall_seconds': time.monotonic() - start,
                  'stdout': str((logs / (name + '.stdout')).relative_to(out)),
                  'stderr': str((logs / (name + '.stderr')).relative_to(out)),
                  'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
                  'stderr_sha256': hashlib.sha256(stderr).hexdigest()}
        commands.append(record)
        (out / 'host-native-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        print(json.dumps(record), flush=True)
        if process.returncode != 0:
            raise RuntimeError(name + ' failed; retained stdout/stderr')
        return stdout

    run('kind2-version', [kind2, '--version'])
    run('z3-version', [z3, '--version'])
    run('rustc-version', ['rustup', 'run', '1.85.0', 'rustc', '--version'])
    run('original-export-parse', [kind2, '-json', '--only_parse', 'true', '--lus_main',
                                 'nn_12B_with_contracts_PP', out / 'original_export.lus'])
    common = [kind2, '-json', '--smt_solver', 'Z3', '--z3_bin', z3,
              '--enable', 'BMC', '--enable', 'IND', '--timeout', '60']
    run('clock-miter-proof', common + ['--lus_main', 'clock_miter', out / 'clock_miter.lus'])
    run('monitor-proof-and-codegen', common + ['--lus_main', 'native_scalar_monitor', '--compile', 'true',
                                             '--output_dir', out / 'rust-codegen', out / 'temporal_compile_projection.lus'])
    manifests = list((out / 'rust-codegen').rglob('Cargo.toml'))
    assert len(manifests) == 1
    project = manifests[0].parent
    run('cargo-build', ['rustup', 'run', '1.85.0', 'cargo', 'build', '--release', '--offline',
                        '--manifest-path', manifests[0]], timeout=120, cwd=project)
    summary = {'status': 'COMPILED_MONITOR_AVAILABLE_PENDING_REPLAY',
               'kind2_sha256': hashlib.sha256(kind2.read_bytes()).hexdigest(),
               'z3_sha256': hashlib.sha256(z3.read_bytes()).hexdigest(),
               'cargo_manifest': str(manifests[0].relative_to(out)),
               'full_nn_execution': 'NOT_QUALIFIED', 'fresh_simulink_compilation': 'NOT_EXECUTED',
               'scope': 'Temporal source slice plus scalar harness and copied exported clock equations.'}
    (out / 'host_codegen_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind2', type=Path, required=True)
    parser.add_argument('--z3', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.kind2.resolve(), args.z3.resolve(), args.out.resolve())
