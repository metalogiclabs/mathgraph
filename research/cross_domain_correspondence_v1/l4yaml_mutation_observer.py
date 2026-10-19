#!/usr/bin/env python3
"""Inspect actual native Lean log + independent YAML 1.2 consumer; never infer source semantics from a status code."""
import argparse,json,hashlib
from pathlib import Path
from ruamel.yaml import YAML
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--mutant',type=Path,required=True);p.add_argument('--restored',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
def read(path):
 raw=path.read_text();checks={};dumps={}
 for line in raw.splitlines():
  if line.startswith('CHECK:'):
   k,sep,v=line[6:].partition('=');assert sep and k not in checks and v in ('true','false');checks[k]=(v=='true')
  if line.startswith('DUMP:'):
   k,sep,v=line[5:].partition('=');assert sep and k not in dumps;dumps[k]=v.replace('\\n','\n')
 assert len(checks)==11 and set(dumps)=={'true','none','qNone','qStringNull'},(checks,dumps)
 reader=YAML(typ='safe');reader.version=(1,2)
 semantic={k:reader.load(v) for k,v in dumps.items()}
 return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checks':checks,'dumps':dumps,'semantic':semantic}
o,m,r=(read(x) for x in [a.original,a.mutant,a.restored])
assert o['checks']==r['checks'] and o['dumps']==r['dumps'] and o['semantic']==r['semantic'],'SOURCE_RESTORATION_NATIVE_REPLAY_DIFF'
assert all(o['checks'][k]==m['checks'][k] for k in o['checks']), 'UNEXPECTED_NATIVE_SCHEMA_CHECK_DRIFT'
assert o['semantic']['none']=='null' and m['semantic']['none'] is None
assert o['semantic']['true']=='true' and m['semantic']['true'] is True
assert o['semantic']['qNone']=={'x':'null'} and m['semantic']['qNone']=={'x':None}
assert o['semantic']['qStringNull']=={'x':'null'} and m['semantic']['qStringNull']=={'x':None}
assert m['dumps']['qNone']==m['dumps']['qStringNull'],'MUTATION_UNEXPECTEDLY_FIXED_COLLISION'
changes=sorted(k for k in o['semantic'] if o['semantic'][k]!=m['semantic'][k])
assert changes==['none','qNone','qStringNull','true'],changes
result={'experiment':'L4YAML_DEFAULT_RESERVED_POLICY_NATIVE_MUTATION','bounds':'source-native Lean probe and independent YAML 1.2 oracle; not a repair to quoted-scalar resolution or to option collision','source_changed':True,'original':o,'mutated':m,'restored':r,'changed_external_consumer_semantics':changes,'restoration_native_replay_matches':True,'status':'WARRANTED_BOUNDED_IF_ACTIONS_JOB_GREEN'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print('NATIVE_SOURCE_MUTATION_AND_RESTORATION_VERIFIED',changes)
