#!/usr/bin/env python3
"""Live Vampire -> independent Lean -> durable Crystal -> no-search replay gate."""
from __future__ import annotations
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import time

from mathgraph.atp_tptp import FirstOrderResidual
from mathgraph.fol_admission import initial_query
from mathgraph.query_gateway import machine_from_dict, query_crystal

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('learn_crystal',ROOT/'scripts/learn_crystal.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
OUT=ROOT/'evidence/crystal-query-admission-v1'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cases=[
        FirstOrderResidual('socrates',(('r','! [X] : (human(X) => mortal(X))'),('f','human(socrates)')),'mortal(socrates)',boundary_ref='live:horn'),
        FirstOrderResidual('converse',(('r','! [X] : (human(X) => mortal(X))'),('f','mortal(socrates)')),'human(socrates)',boundary_ref='live:horn'),
        FirstOrderResidual('renamed-chain',(('r1','! [X] : (p(X) => q(X))'),('r2','! [Y] : (q(Y) => r(Y))'),('f','p(z)')),'r(z)',boundary_ref='live:horn'),
    ]
    summaries=[]
    for r,expected in zip(cases,('WARRANTED','EXCLUDED','WARRANTED')):
        directory=OUT/r.problem_id; store=directory/'machine.json'
        if store.exists(): store.unlink()  # Qualification always starts cold.
        first=mod.resolve(r,store=store,evidence_dir=directory,vampire=os.environ['VAMP'],lean=os.environ['LEAN'])
        mod.atomic_json(directory/'first-query.json', first)
        assert first['status']==expected, first
        assert first['before']['status']=='UNKNOWN'
        assert first['checker_accepted'] is True and first['admission']['axioms']==[]
        # Neither engine is available at these deliberately invalid paths.
        replay=mod.resolve(r,store=store,evidence_dir=directory,vampire='/missing/vampire',lean='/missing/lean')
        assert replay['status']==expected and replay['external_calls']==0 and replay['cache_hit']
        assert replay['answer']['question_id']==first['before']['question_id']
        machine=machine_from_dict(json.loads(store.read_text()))
        _,q=initial_query(r)
        revoked=query_crystal(machine,replace(q,live_supports=()))
        assert revoked.status.value=='UNKNOWN'
        times=[]
        for _ in range(1000):
            start=time.perf_counter_ns(); a=query_crystal(machine,q); times.append(time.perf_counter_ns()-start)
            assert a.status.value==expected
        summaries.append({'problem':r.problem_id,'before':'UNKNOWN','candidate':first['candidate_status'],
            'after':expected,'replay':replay['status'],'replay_external_calls':0,
            'revoked':revoked.status.value,'terminal_form':first['admission']['terminal_form'],
            'axioms':first['admission']['axioms'],'cold_wall_seconds':first['wall_seconds'],
            'warm_gateway_median_ns':statistics.median(times),
            'query_id':q.id,'receipt':first['admission']['receipt_id']})
        mod.atomic_json(directory/'replay.json',replay)
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ('mathgraph/fol_admission.py','mathgraph/query_gateway.py','scripts/learn_crystal.py')}
    result={'status':'QUALIFIED_BOUNDED','commit':os.environ.get('GITHUB_SHA','local'),
        'parent':'fa151b066ab44155fbaad1368aa36139145b6579','cases':summaries,'source_sha256':hashes,
        'scope':'Unary ground facts, universal unary implications, ground unary queries only.',
        'validation':'Independent generated Lean reproof or complete finite-model evaluation; not arbitrary Vampire trace checking.',
        'trust_boundary':['pinned Lean executable','strict restricted parser and code generator','local store and runner','Python orchestration'],
        'nonclaims':['arbitrary FOL','automatic prose formalization','remote hostile-client admission','universal soundness or throughput theorem']}
    mod.atomic_json(OUT/'result.json',result)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__': main()
