#!/usr/bin/env python3
"""Finite source-model -> qualified minimal experiment/obstruction receipt CLI."""
from __future__ import annotations
import argparse,hashlib,json,pathlib
from compiler import compile_experiment

SCHEMA='metalogic.consequence-to-experiment.finite-v1'

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def main():
    p=argparse.ArgumentParser(description='Finite action/observation compilation; inputs are explicit assumptions')
    p.add_argument('--model',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    args=p.parse_args()
    original=args.model.read_bytes()
    model=json.loads(original)
    result=compile_experiment(model)
    here=pathlib.Path(__file__).resolve().parent
    artifact={'schema':SCHEMA,'input_sha256':sha(original),
              'compiler_source_sha256':sha((here/'compiler.py').read_bytes()),
              'result':result,
              'limitations':['All state/effect/readout tables and grants are provided, not independently measured',
                             'No new physical primitive inferred or permission granted',
                             'Obstruction applies only to the complete declared finite grammar']}
    payload=(json.dumps(artifact,sort_keys=True,indent=2)+'\n').encode()
    args.output.parent.mkdir(exist_ok=True,parents=True)
    args.output.write_bytes(payload)
    print('FINITE_COMPILER_RECEIPT_SHA256='+sha(payload))
    print('FINITE_COMPILER_STATUS='+result['status']+' / '+result['diagnosis'])
    return 0

if __name__=='__main__':raise SystemExit(main())