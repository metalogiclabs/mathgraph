#!/usr/bin/env python3
"""Persist a checked answer, then serve subsequent exact queries without search.

Trusted local store/runner prototype. Not an untrusted network admission service.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

from mathgraph.atp_tptp import residual_from_dict, run_vampire
from mathgraph.fol_admission import initial_query, prepare_check, check_and_admit
from mathgraph.protected_future import ContinuationStatus as S
from mathgraph.query_gateway import query_crystal, machine_to_dict, machine_from_dict


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.crystal-', suffix='.json')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(payload, out, indent=2, sort_keys=True)
            out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def resolve(r, *, store: Path, evidence_dir: Path, vampire='vampire', lean='lean',
            no_discovery=False, time_limit=5) -> dict:
    start = time.perf_counter()
    fresh, question = initial_query(r)
    machine = machine_from_dict(json.loads(store.read_text())) if store.exists() else fresh
    if machine.boundary_ref != r.boundary_ref or r.id not in machine.states:
        return {'status': 'UNKNOWN', 'reason': 'store_problem_mismatch', 'external_calls': 0}
    before = query_crystal(machine, question)
    if before.status is not S.UNKNOWN or no_discovery:
        return {'status': before.status.value, 'answer': before.to_dict(),
                'cache_hit': before.status is not S.UNKNOWN, 'external_calls': 0,
                'wall_seconds': time.perf_counter()-start}
    try:
        prepare_check(r)  # Do not send unsupported / injected input to a solver.
    except ValueError as exc:
        return {'status': 'UNKNOWN', 'reason': 'unsupported_fragment', 'detail': str(exc),
                'answer': before.to_dict(), 'external_calls': 0}
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / 'problem.p').write_text(r.to_tptp())
    try:
        candidate = run_vampire(r, executable=vampire, time_limit_seconds=time_limit)
    except OSError as exc:
        return {'status':'UNKNOWN', 'reason':'solver_unavailable', 'detail':str(exc),
                'answer':before.to_dict(), 'external_calls':1}
    atomic_json(evidence_dir / 'candidate.json', candidate.to_dict())
    attempt = check_and_admit(machine, question, r, candidate, lean=lean, evidence_dir=evidence_dir)
    after = query_crystal(attempt.machine, question)
    atomic_json(evidence_dir / 'admission.json', attempt.record)
    if attempt.status in (S.WARRANTED, S.EXCLUDED):
        atomic_json(store, machine_to_dict(attempt.machine))
    return {'status': after.status.value, 'reason': attempt.reason, 'before': before.to_dict(),
            'answer': after.to_dict(), 'admission': attempt.record,
            'candidate_status': candidate.candidate_status, 'cache_hit': False,
            'external_calls': 1, 'checker_accepted': attempt.record.get('accepted', False),
            'wall_seconds': time.perf_counter()-start}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--residual', type=Path, required=True)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path, required=True)
    p.add_argument('--vampire', default='vampire')
    p.add_argument('--lean', default='lean')
    p.add_argument('--no-discovery', action='store_true')
    args=p.parse_args()
    try:
        r=residual_from_dict(json.loads(args.residual.read_text()))
        out=resolve(r,store=args.store,evidence_dir=args.evidence_dir,
                    vampire=args.vampire,lean=args.lean,no_discovery=args.no_discovery)
        print(json.dumps(out,indent=2,sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status':'UNKNOWN','reason':'invalid_request_or_store','detail':str(exc)}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
