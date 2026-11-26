"""Isolate the marginal compiled cost of each profiled, visited ARM branch.

The profile fixes one hint direction per site before any single-site score.
Independent shards write disjoint source/report paths. No arithmetic changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from arm_profile_hints import TRAIN
from hot_path_hints import BASE, HELDOUT_SEED


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--kit',type=Path)
    p.add_argument('--shard')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if a.shard is None:
        source=a.baseline.read_text()
        if hashlib.sha256(source.encode()).hexdigest()!=BASE:raise ValueError('baseline')
        profile=json.loads(a.profile.read_text())
        if profile['baseline_sha256']!=BASE or profile['train_seed']!=TRAIN:raise ValueError('profile')
        variants=[]
        for r in profile['sites']:
            if r['probability'] is None or r['visit_weight']<.01:continue
            hint=int(r['probability']>=.5)
            name=r['function']+'-'+str(r['index'])+'-'+str(hint)
            expression='__builtin_expect(!!('+r['condition']+'),'+str(hint)+')'
            candidate=source[:r['start']]+expression+source[r['end']:]
            (a.out/(name+'.c')).write_text(candidate)
            variants.append({'name':name,'source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                             'site':r['site'],'probability':r['probability'],'hint':hint})
        (a.out/'protocol.json').write_text(json.dumps({'baseline_sha256':BASE,'train_seed':TRAIN,
            'heldout_seed_frozen':HELDOUT_SEED,'minimum_training_gain':.005,'variants':variants,
            'boundary':'Training-only marginal compiler-layout search; no candidate arithmetic change or takeover claim'},indent=2)+'\n')
        print('Frozen',len(variants),'one-condition variants',flush=True)
        return
    if not a.kit:raise ValueError('kit needed for measurements')
    i,n=map(int,a.shard.split('/'))
    if not 0<=i<n:raise ValueError('shard')
    sys.path.insert(0,str(a.kit.resolve()))
    from eik import stages as ST
    protocol=json.loads((a.out/'protocol.json').read_text())
    for index,v in enumerate(protocol['variants']):
        if index%n!=i:continue
        f=a.out/(v['name']+'.c')
        if hashlib.sha256(f.read_bytes()).hexdigest()!=v['source_sha256']:raise ValueError('candidate changed')
        report=ST.measure(f,TRAIN,targets=['thumbv6m'],sample=False)
        (a.out/(v['name']+'-train.json')).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'index':index,'name':v['name'],'verdict':report['verdict'],
                          'S':report.get('scores',{}).get('thumbv6m',{}).get('S')}),flush=True)


if __name__=='__main__':main()
