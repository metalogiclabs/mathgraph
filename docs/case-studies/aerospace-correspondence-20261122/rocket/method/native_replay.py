"""Replays authentic, public, pinned FRET->C2PO->R2U2 output.

The source FRETish [0,7] and manually constructed [1,7] are both executed.
This bounded native qualification never authorizes operational-intent repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

FRET_SHA = 'cf0f913cc15c41705e803593297e89cd6056b839'
R2U2_SHA = '2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a'
SPEC_DIGESTS = {'source':'61cdfdb56da7463f3fb220381649c011efb6d0a5177a841255540186f2b3ea15',
                'challenger':'cc16408a46782573397b8d6f06857fb011651adac90d1c8a9379213c9aef7100'}
MAP_DIGEST = 'dc8649dfeefbccd35f1df8afbf25f8e14b10cc0ff97551b8b6aa79724f79ea2f'
CASES = ('simultaneous','next_tick','no_coast','no_boost')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_checkout(path, required_sha):
    result = subprocess.run(['git','-C',str(path),'rev-parse','HEAD'],check=True,text=True,capture_output=True)
    if result.stdout.strip() != required_sha:
        raise ValueError('UPSTREAM_SOURCE_IDENTITY_CHANGED: '+str(path))


def call(*args, input=None, cwd=None):
    proc = subprocess.run(list(map(str,args)),input=input,text=True,capture_output=True,cwd=cwd,timeout=75)
    if proc.returncode != 0:
        raise ValueError('NATIVE_EXEC_FAILED: '+str(args[:2])+'\n'+proc.stderr[:1200])
    return proc.stdout


def oracle_at(trace, current, lower):
    # Complete 8-tick finite oracle. Not MLTL theorem under open-prefix semantics.
    return not bool(trace[current]['BOOST']) or any(
        bool(trace[i]['COAST']) for i in range(current+lower,min(8,current+8))
    )


def decode_aggregated(text):
    """R2U2 reports last index of contiguous equal verdicts; not missing ticks."""
    out={}
    next_time=0
    for line in text.splitlines():
        m=re.fullmatch(r'0:([0-9]+),([TF])',line)
        if m is None:raise ValueError('MALFORMED_NATIVE_VERDICT: '+line)
        last=int(m[1]); val=m[2]=='T'
        if last<next_time or last>=8:
            raise ValueError('NATIVE_VERDICT_HORIZON_INVALID')
        for time in range(next_time,last+1): out[time]=val
        next_time=last+1
    if set(out)!=set(range(8)):
        raise ValueError('INCOMPLETE_NATIVE_VERDICTS')
    return [out[i] for i in range(8)]


def admitted_binding(spec,map_,binary,trace,expected_binary):
    """Byte-level comparison only. expected_binary comes from this native build.

    A forged receipt self-generated from attacker-selected bytes is NOT authenticated.
    """
    if sha(spec)!=SPEC_DIGESTS[Path(spec).stem]:return 'UNKNOWN_SOURCE_CHANGED'
    if sha(map_)!=MAP_DIGEST:return 'UNKNOWN_SIGNAL_MAP_CHANGED'
    if sha(binary)!=expected_binary:return 'UNKNOWN_BINARY_CHANGED'
    line=Path(trace).read_text().splitlines()[0].strip()
    if [s.strip() for s in line.removeprefix('#').split(',')]!=['BOOST','COAST'] or not line.startswith('#'):
        return 'UNKNOWN_SIGNAL_HEADER_CHANGED'
    return 'BOUND_WITHIN_NATIVE_RUN'


def run(out:Path,fret:Path,r2u2:Path):
    check_checkout(fret,FRET_SHA)
    check_checkout(r2u2,R2U2_SHA)
    if not (r2u2/'monitors/c/build/r2u2').is_file():
        raise ValueError('R2U2_NATIVE_MONITOR_MISSING')
    compiler=r2u2/'compiler/c2po.py'
    runner=r2u2/'monitors/c/build/r2u2'
    for variant in ('source','challenger'):
        spec=out/(variant+'.c2po');mapping=out/(variant+'.map')
        if sha(spec)!=SPEC_DIGESTS[variant] or sha(mapping)!=MAP_DIGEST:
            raise ValueError('FRET_EXPORT_SOURCE_MAP_CHANGED: '+variant)
        call(sys.executable,compiler,'--spec',spec,'--map',mapping,'--output',out/(variant+'.bin'),cwd=r2u2)
    digests={v:sha(out/(v+'.bin')) for v in ('source','challenger')}
    observations=[]
    observed_count=0
    for case in CASES:
        samples=json.loads((out/(case+'.json')).read_text())
        if len(samples)!=8 or any(type(t)!=dict or set(t)!={'BOOST','COAST'} or any(x not in (0,1) or type(x)!=int for x in t.values()) for t in samples):
            raise ValueError('INVALID_TRACE_DOMAIN: '+case)
        csv_lines=(out/(case+'.csv')).read_text().splitlines()
        if (len(csv_lines)!=9 or csv_lines[0].strip()!='# BOOST, COAST' or
            csv_lines[1:] != [f"{row['BOOST']},{row['COAST']}" for row in samples]):
            raise ValueError('TRACE_CSV_NAMED_VALUES_CHANGED: '+case)
        for variant,low in (('source',0),('challenger',1)):
            binary=out/(variant+'.bin');spec=out/(variant+'.c2po');mapping=out/(variant+'.map');trace=out/(case+'.csv')
            if admitted_binding(spec,mapping,binary,trace,digests[variant])!='BOUND_WITHIN_NATIVE_RUN':
                raise ValueError('INCOMPLETE_NATIVE_BINDING: '+variant+':'+case)
            native=decode_aggregated(call(runner,binary,input=trace.read_text(),cwd=r2u2))
            oracle=[oracle_at(samples,t,low) for t in range(8)]
            if native!=oracle:raise ValueError('NATIVE_ORACLE_DISAGREEMENT: '+variant+':'+case)
            observations.append({'scenario':case,'variant':variant,'native':native,'oracle':oracle})
            observed_count+=len(native)
    source=next(x for x in observations if x['scenario']=='simultaneous' and x['variant']=='source')
    challenger=next(x for x in observations if x['scenario']=='simultaneous' and x['variant']=='challenger')
    if (source['native'][0],challenger['native'][0])!=(True,False):
        raise ValueError('SEMANTIC_SEPARATOR_NOT_OBSERVED')
    # Negative controls: altered signal header and binary substitution cannot pass the gate.
    swapped=out/'synthetic-swapped.csv'
    try:
        swapped.write_text((out/'simultaneous.csv').read_text().replace('# BOOST, COAST','# COAST, BOOST',1))
        if admitted_binding(out/'source.c2po',out/'source.map',out/'source.bin',swapped,digests['source'])!='UNKNOWN_SIGNAL_HEADER_CHANGED':
            raise ValueError('HEADER_TAMPERING_NOT_REFUSED')
        if admitted_binding(out/'source.c2po',out/'source.map',out/'challenger.bin',out/'simultaneous.csv',digests['source'])!='UNKNOWN_BINARY_CHANGED':
            raise ValueError('BINARY_SWAP_NOT_REFUSED')
    finally:
        swapped.unlink(missing_ok=True)
    manifest={
      'schema':'mathgraph.check.rocket-native-replay.v1',
      'source_pins':{'fret':FRET_SHA,'r2u2':R2U2_SHA},
      'source_sha256':{v:sha(out/(v+'.c2po')) for v in digests},
      'map_sha256':MAP_DIGEST,
      'binary_sha256':digests,
      'monitor_executable_sha256':sha(runner),
      'native_oracle_positions':observed_count,
      'native_match':'WARRANTED_BOUNDED_EXACT_TESTED_DOMAIN',
      'original_fretish':'whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST',
      'source_formula':'(BOOST -> (F[0,7] COAST))',
      'comparison_formula':'(BOOST -> (F[1,7] COAST))',
      'comparison_role':'CONSTRUCTED_NOT_FRETISH_OUTPUT_NOT_OWNER_APPROVED',
      'operational_intent':'UNKNOWN', 'repair_authority':'UNKNOWN',
      'auto_repair':'DENIED','permission':'ADVISORY_ONLY',
      'overall':'UNKNOWN',
      'coverage':'4 eight-tick Boolean cases x 2 formulas x 8 decoded verdicts',
      'verification_receipt':'UNSIGNED_RUN_OBSERVATION_NOT_OWNER_AUTHORITY',
      'observations':observations,
    }
    (out/'native-result.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--fret',type=Path,required=True)
    p.add_argument('--r2u2',type=Path,required=True)
    args=p.parse_args();res=run(args.out.resolve(),args.fret.resolve(),args.r2u2.resolve())
    print(json.dumps({k:res[k] for k in ['native_oracle_positions','native_match','overall','repair_authority','auto_repair']},sort_keys=True))


if __name__=='__main__':main()
