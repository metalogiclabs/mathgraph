"""Separate, no-secrets artifact reader and source/map/binary qualified replay.

This verifier does NOT trust manifest status strings or in-band owner flags.
It re-reads supplied binary artifacts, reconstructs protected observations,
and runs the separately built R2U2 monitor. It is not a mission approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

FRET_SHA='cf0f913cc15c41705e803593297e89cd6056b839'
R2U2_SHA='2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a'
SPECS={'source':'61cdfdb56da7463f3fb220381649c011efb6d0a5177a841255540186f2b3ea15',
       'challenger':'cc16408a46782573397b8d6f06857fb011651adac90d1c8a9379213c9aef7100'}
MAP='dc8649dfeefbccd35f1df8afbf25f8e14b10cc0ff97551b8b6aa79724f79ea2f'
CASES=(('simultaneous',0,0),('next_tick',0,1),('no_coast',0,-1),('no_boost',-1,-1))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_report(out:Path,monitor:Path):
    manifest=json.loads((out/'native-result.json').read_text())
    if manifest.get('schema')!='mathgraph.check.rocket-native-replay.v1':raise ValueError('UNSUPPORTED_NATIVE_REPORT')
    if any(k in manifest for k in ('owner_approved','operator','authorized','semantic_truth')):
        raise ValueError('EVIDENCE_ATTEMPTS_AUTHORITY_PROMOTION')
    if manifest.get('source_pins')!={'fret':FRET_SHA,'r2u2':R2U2_SHA}:
        raise ValueError('SOURCE_NOT_PINNED')
    if manifest.get('source_sha256')!=SPECS or manifest.get('map_sha256')!=MAP:
        raise ValueError('WRONG_NATIVE_SOURCE_REFERENCE')
    if set(manifest.get('binary_sha256',{}))!=set(SPECS):raise ValueError('INCOMPLETE_BINARY_REFERENCE')
    if (manifest.get('overall')!='UNKNOWN' or manifest.get('repair_authority')!='UNKNOWN' or
        manifest.get('auto_repair')!='DENIED' or manifest.get('permission')!='ADVISORY_ONLY'):
        raise ValueError('EVIDENCE_ATTEMPTS_AUTHORITY_PROMOTION')
    if manifest.get('native_oracle_positions')!=64:raise ValueError('UNEXPECTED_CASE_CENSUS')
    observations=[]
    for variant in SPECS:
        if digest(out/(variant+'.c2po'))!=SPECS[variant]:raise ValueError('SPEC_CHANGED')
        if digest(out/(variant+'.map'))!=MAP:raise ValueError('MAP_CHANGED')
        if digest(out/(variant+'.bin'))!=manifest['binary_sha256'][variant]:raise ValueError('BINARY_CHANGED')
    if digest(monitor)!=manifest['monitor_executable_sha256']:
        # A different build does not warrant exact binary identity. Fail closed.
        raise ValueError('MONITOR_EXECUTABLE_NOT_IDENTICAL')
    for name,boost,coast in CASES:
        raw=(out/(name+'.csv')).read_text().splitlines()
        if len(raw)!=9 or raw[0]!='# BOOST, COAST':raise ValueError('TRACE_NAME_MAP_CHANGED')
        direct=[(int(i==boost),int(i==coast)) for i in range(8)]
        if raw[1:]!=[f'{b},{c}' for b,c in direct]:raise ValueError('TRACE_DATA_CHANGED')
        for variant,minimum in [('source',0),('challenger',1)]:
            process=subprocess.run([str(monitor),str(out/(variant+'.bin'))],input='\n'.join(raw)+'\n',capture_output=True,text=True,timeout=45)
            if process.returncode:raise ValueError('R2U2_EXEC_FAILED')
            results={}
            next_t=0
            for line in process.stdout.splitlines():
                mat=re.fullmatch('0:([0-9]+),([TF])',line)
                if not mat:raise ValueError('MALFORMED_VERDICT')
                t=int(mat.group(1))
                if t>=8 or t<next_t:raise ValueError('WRONG_VERDICT_HORIZON')
                results.update({i:mat.group(2)=='T' for i in range(next_t,t+1)})
                next_t=t+1
            if set(results)!=set(range(8)):raise ValueError('INCOMPLETE_NATIVE_VERDICTS')
            expected={}
            for t,(b,c) in enumerate(direct):
                successors=direct[t+minimum:min(t+8,8)]
                expected[t] = not bool(b) or any(coast_==1 for boost_,coast_ in successors)
            if results!=expected:raise ValueError('INDEPENDENT_REFERENCE_MISMATCH')
            observations.append({'case':name,'variant':variant,'decoded':results})
    if (observations[0]['decoded'][0],observations[1]['decoded'][0])!=(True,False):
        raise ValueError('SOURCE_VS_COMPARISON_NOT_DISTINGUISHED')
    return {'schema':'mathgraph.check.rocket-native-qualification.v1',
            'native_scope':'WARRANTED_BOUNDED_EXACT_CASES',
            'positions':64,
            'artifact_sha256':{n:digest(out/(n+'.bin')) for n in SPECS},
            'monitor_sha256':digest(monitor),
            'intent_status':'UNKNOWN', 'repair':'DENIED','permission':'ADVISORY_ONLY',
            'overall':'UNKNOWN',
            'independent_replay':'SECOND_CI_JOB_DIRECT_ORACLE_AND_NATIVE_C',
            'limitations':['4 complete Boolean 8-tick traces only',
                           'Owner purpose not authenticated',
                           'Native R2U2 executable and exact source pinned',
                           'No general MLTL correctness or external release permission']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--monitor',type=Path,required=True)
    x=p.parse_args();res=validate_report(x.out.resolve(),x.monitor.resolve())
    (x.out/'independent-qualification.json').write_text(json.dumps(res,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:res[k] for k in ('native_scope','positions','overall','intent_status','repair')}))

if __name__=='__main__':main()
