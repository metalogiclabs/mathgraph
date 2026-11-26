"""Conditional whole-score bound for a uniform per-call instruction saving.

This is score-model arithmetic on a pinned report, not an executable kernel.
The deliberately generous three-instruction model also removes the return
instruction's count; real frame elimination still needs a return.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def change(measurement, saving):
    result=copy.deepcopy(measurement)
    for sets in result['functions'].values():
        for stats in sets.values():
            for key in ['mean','median','p999','max']:
                if stats[key]<=saving:raise ValueError('nonpositive hypothetical instruction count')
                stats[key]-=saving
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--control',type=Path,required=True)
    ap.add_argument('--kit',type=Path,required=True)
    ap.add_argument('--champion',type=float,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    import sys
    sys.path.insert(0,str(a.kit.resolve()))
    from eik.score import score
    r=json.loads(a.control.read_text());target='thumbv6m';m=r['targets'][target];n=r['bytes'][target]
    original,_=score(m,n)
    assert abs(original-r['scores'][target]['S'])<1e-12
    rows=[]
    for saving in [0,1,2,3]:
        value,parts=score(change(m,saving),n)
        rows.append({'saving_every_call':saving,'hypothetical_S':value,
                     'clears_recorded_bar':value<=.97*a.champion})
    result={'state':'NAMED_OBSTRUCTION','name':'FRAME_ONLY_SCOPE_TOO_SMALL_AT_FIXED_BYTES',
            'control_sha256':hashlib.sha256(a.control.read_bytes()).hexdigest(),
            'source_sha256':r['sha256'],'seed':r['seed'],'fingerprint':r['fingerprint'],
            'fixed_bytes':n,'recorded_champion_S':a.champion,'recorded_bar':.97*a.champion,
            'boundary':'Counterfactual savings from every call on the recorded draw, fixed code/table bytes; not a future-draw takeover verdict',
            'models':rows}
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
