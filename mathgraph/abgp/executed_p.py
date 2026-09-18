"""Executed persistence boundary qualification, not a confirmatory P generator."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence


class WorkerProtocolError(RuntimeError):
    """The worker did not supply a valid sandboxed response; never fall back."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def run_worker(request: dict[str, Any], *, seccomp_library: str = 'libseccomp.so.2', worker_kind: str | None = None) -> dict[str, Any]:
    if not sys.platform.startswith('linux'):
        raise WorkerProtocolError('Linux syscall isolation is required')
    raw = canonical(request)
    if len(raw) > 65536:
        raise WorkerProtocolError('request exceeds byte budget')
    if worker_kind is None:
        worker_kind = ('acquisition' if request.get('operation') in ('acquire', 'posterior')
                       else 'posterior' if request.get('operation') == 'posterior_invoke' else 'invocation')
    images = {
        'acquisition': 'p_acquisition_worker.py',
        'invocation': 'p_worker.py',
        'posterior': 'p_posterior_worker.py',
        'structural_acquisition': 'p_structural_acquisition_worker.py',
        'structural_invocation': 'p_structural_invocation_worker.py',
        'structural_posterior': 'p_structural_posterior_worker.py',
    }
    if worker_kind not in images:
        raise WorkerProtocolError('unknown worker image')
    image = images[worker_kind]
    code = Path(__file__).with_name(image).read_bytes()
    bootstrap = Path(__file__).with_name('sandbox_runtime.py').read_bytes()
    expected_code = hashlib.sha256(code).hexdigest()
    with tempfile.TemporaryDirectory(prefix='abgp-worker-') as directory:
        worker = Path(directory) / 'worker.py'
        worker.write_bytes(code)
        (Path(directory) / 'runtime.py').write_bytes(bootstrap)
        started = time.perf_counter()
        try:
            process = subprocess.run(
                [sys.executable, '-I', '-S', str(worker), seccomp_library],
                input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=directory, env={'LC_ALL': 'C', 'TZ': 'UTC'},
                close_fds=True, start_new_session=True, timeout=8, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WorkerProtocolError('worker could not execute within its boundary') from exc
        elapsed = time.perf_counter() - started
    try:
        response = json.loads(process.stdout)
    except (ValueError, UnicodeError) as exc:
        raise WorkerProtocolError('worker returned no valid JSON receipt') from exc
    if process.returncode != 0 or not isinstance(response, dict) or 'error' in response:
        raise WorkerProtocolError(str(response))
    if response.get('worker_code_sha256') != expected_code:
        raise WorkerProtocolError('worker code digest mismatch')
    if response.get('bootstrap_sha256') != hashlib.sha256(bootstrap).hexdigest():
        raise WorkerProtocolError('bootstrap digest mismatch')
    if response.get('request_sha256') != hashlib.sha256(raw).hexdigest():
        raise WorkerProtocolError('worker input digest mismatch')
    if response.get('sandbox', {}).get('seccomp_mode') != 2 or response['sandbox'].get('no_new_privs') != 1:
        raise WorkerProtocolError('worker isolation receipt missing')
    if response.get('pid') == os.getpid() or response.get('operation') != request.get('operation'):
        raise WorkerProtocolError('worker execution identity mismatch')
    response['parent_pid'] = os.getpid()
    response['elapsed_seconds'] = elapsed
    return response


def execute_episode(policy: Sequence[int]) -> dict[str, Any]:
    """A DEV boundary exercise. Labels stay in acquisition/evaluation processes.

    The same-information posterior control is deliberately allowed to MATCH the
    retained lookup policy. Such a match is a scientific separator, not a bug.
    """
    truth = tuple(policy)
    if len(truth) != 4 or any(type(x) is not int for x in truth) or sorted(truth) != list(range(4)):
        raise ValueError('policy must be a permutation of 0..3')
    examples = [[c, truth[c]] for c in range(4)]
    contexts = list(range(4))
    runs: dict[str, dict[str, Any]] = {}
    runs['acquire'] = run_worker({'operation': 'acquire', 'examples': examples})
    retained = runs['acquire']['retained']
    if retained is None:
        raise WorkerProtocolError('complete source evidence did not identify the finite policy')
    runs['retained'] = run_worker({'operation': 'invoke', 'retained': retained, 'contexts': contexts})
    runs['cold'] = run_worker({'operation': 'invoke', 'retained': None, 'contexts': contexts})
    runs['ablation'] = run_worker({'operation': 'delete', 'retained': retained, 'lineage': retained['lineage']})
    runs['deleted'] = run_worker({'operation': 'invoke', 'retained': runs['ablation']['retained'], 'contexts': contexts})
    runs['reacquire'] = run_worker({'operation': 'acquire', 'examples': examples})
    runs['reacquired'] = run_worker({'operation': 'invoke', 'retained': runs['reacquire']['retained'], 'contexts': contexts})
    runs['posterior'] = run_worker({'operation': 'posterior', 'examples': examples})
    runs['posterior_invocation'] = run_worker({'operation': 'posterior_invoke', 'posterior_weights': runs['posterior']['posterior_weights'], 'contexts': contexts})
    # Independent evaluator: never use the worker's declared success as outcome.
    scores = {name: int(tuple(runs[name]['actions']) == truth)
              for name in ('retained', 'cold', 'deleted', 'reacquired')}
    scores['posterior'] = int(tuple(runs['posterior_invocation']['actions']) == truth)
    return {'schema': 'abgp.executed-p-mechanics.v1', 'mode': 'DEV_MECHANISMS_ONLY',
            'runs': runs, 'scores': scores,
            'structural_advantage_over_posterior': scores['retained'] > scores['posterior'],
            'source_distinct_scientific_qualification': False,
            'confirmatory_namespace_used': False}


def trace_p_episodes(count: int, *, namespace: str = 'ABGP-DEV-v1') -> dict[str, Any]:
    """Trace real DEV draws and executed descendants, never invent seed ancestry.

    This is a fixed 24-policy boundary-qualification model with four fixed probes,
    not the scientific source-distinct generator. Replay uses recorded draws.
    """
    if namespace != 'ABGP-DEV-v1':
        raise ValueError('this executable path accepts only its DEV namespace')
    if type(count) is not int or not 1 <= count <= 64:
        raise ValueError('DEV boundary batch size must lie in 1..64')
    import itertools
    import secrets
    from .ancestry import Ledger
    ledger = Ledger()
    protocol = ledger.fixed('protocol', {
        'namespace': namespace, 'contexts': [0, 1, 2, 3],
        'files': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                  for name in ('executed_p.py', 'p_worker.py', 'p_acquisition_worker.py',
                               'p_posterior_worker.py', 'sandbox_runtime.py')},
    })
    policies = tuple(itertools.permutations(range(4)))
    outputs, episodes, draws = {}, [], []
    for index in range(count):
        draw = ledger.sample(f'episode-{index}/policy-draw', lambda: secrets.randbelow(len(policies)), parents=(protocol,))
        policy = ledger.apply(f'episode-{index}/policy', lambda i: list(policies[i]), draw)
        result = ledger.apply(f'episode-{index}/execution', execute_episode, policy)
        outputs[f'episode-{index}'] = (result,)
        episodes.append(result.value)
        draws.append(draw.value)
    return {'namespace': namespace, 'source_sampling_model': 'uniform fixed-24 policy index via secrets.randbelow',
            'recorded_draw_indices': draws, 'future_contexts_fixed_not_randomly_sampled': True,
            'episodes': episodes, 'ancestry': ledger.audit(outputs),
            'confirmatory_namespace_used': False, 'scientific_source_distinctness_qualified': False}
