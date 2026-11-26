"""Profile ordinary ARM branch conditions, then screen fixed hint policies.

The development instrumentation has counters. No counters or mutable state
enter a candidate: emitted candidates only wrap existing conditions in
__builtin_expect. The held-out draw is never used for profile construction.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from hot_path_hints import BASE, HELDOUT_SEED

TRAIN = 150897616
POLICIES = ['root','decisive','moderate','all','guards']


def sites(source):
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',lambda m:' '*len(m[0]),source,flags=re.S)
    result=[]
    for fn in ['sigmoid','tanh','exp']:
        start=clean.index('static uint32_t t_t_eik_'+fn+'(uint32_t t_t_w)\n{')
        opening=clean.index('{',start);depth=1;end=opening+1
        while depth:
            depth+=(clean[end]=='{')-(clean[end]=='}');end+=1
        for index,m in enumerate(re.finditer(r'\bif\s*\(',clean[opening:end])):
            lo=opening+m.end();hi=lo;d=1
            while d:
                d+=(clean[hi]=='(')-(clean[hi]==')');hi+=1
            result.append({'function':fn,'index':index,'start':lo,'end':hi-1,
                           'condition':source[lo:hi-1]})
    for i,r in enumerate(result):r['site']=i
    return result


def wrap(source,records,replacement):
    for r in sorted(records,key=lambda r:r['start'],reverse=True):
        source=source[:r['start']]+replacement(r)+source[r['end']:]
    return source


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--kit',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    source=args.baseline.read_text()
    if hashlib.sha256(source.encode()).hexdigest()!=BASE:raise ValueError('baseline')
    sys.path.insert(0,str(args.kit.resolve()))
    from eik import inputs as I,config as K,reference as R
    records=sites(source);n=len(records)
    instrument='''static uint64_t dev_counts['''+str(n)+'''][2];
static uint32_t dev_observe(uint32_t value,uint32_t site) {
    dev_counts[site][!!value]++;return value;
}
'''
    observed=instrument+wrap(source,records,lambda r:'dev_observe(!!('+r['condition']+'),'+str(r['site'])+'u)')
    exports='\n'.join('uint32_t dev_'+f+'(uint32_t w) {return t_t_eik_'+f+'(w);}' for f in K.FUNCTIONS)
    observed+='\n'+exports+'''
uint64_t dev_count(uint32_t site,uint32_t taken) {return dev_counts[site][taken];}
void dev_reset(void) {memset(dev_counts,0,sizeof dev_counts);}
'''
    c=args.out/'instrumented.c';so=args.out/'instrumented.so';c.write_text(observed)
    command=['gcc','-std=c11','-O2','-fno-builtin','-ftrivial-auto-var-init=zero','-fPIC','-shared',
             '-include',str(args.kit.resolve()/'harness/eik.h'),str(c),'-o',str(so)]
    subprocess.run(command,check=True)
    lib=C.CDLL(str(so.resolve()));lib.dev_count.argtypes=[C.c_uint32,C.c_uint32];lib.dev_count.restype=C.c_uint64
    weighted=[[0.,0.] for _ in records];campaigns=[]
    for fn in K.FUNCTIONS:
        call=getattr(lib,'dev_'+fn);call.argtypes=[C.c_uint32];call.restype=C.c_uint32
        for set_name,words in I.draw(TRAIN,fn).items():
            lib.dev_reset();expected=R.outputs(fn,words)
            got=[call(w) for w in words]
            if got!=expected:raise ValueError(('instrumented native/reference difference',fn,set_name))
            weight=K.SETS[set_name]/len(words)
            counts=[[lib.dev_count(i,t) for t in (0,1)] for i in range(n)]
            for i,row in enumerate(counts):
                for t in (0,1):weighted[i][t]+=row[t]*weight
            campaigns.append({'function':fn,'set':set_name,'words':len(words),'counts':counts,'mismatches':0})
    for r,cnt in zip(records,weighted):
        r.update(weighted_false=cnt[0],weighted_true=cnt[1],visit_weight=sum(cnt),
                 probability=cnt[1]/sum(cnt) if sum(cnt) else None)
    variants=[]
    for policy in POLICIES:
        selected=[]
        for r in records:
            p=r['probability']
            if p is None or r['visit_weight']<.01:continue
            if policy=='root' and r['index']>1:continue
            if policy=='decisive' and .1<p<.9:continue
            if policy=='moderate' and .25<p<.75:continue
            if policy=='guards' and '&' not in r['condition']:continue
            selected.append({**r,'hint':int(p>=.5)})
        candidate=wrap(source,selected,lambda r:'__builtin_expect(!!('+r['condition']+'),'+str(r['hint'])+')')
        name='profile-'+policy;(args.out/(name+'.c')).write_text(candidate)
        variants.append({'name':name,'selected_sites':len(selected),
                         'source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'policy':policy})
    protocol={'baseline_sha256':BASE,'train_seed':TRAIN,'heldout_seed_frozen':HELDOUT_SEED,
              'minimum_training_gain':.005,'instrumented_native_reference_checks':sum(c['words'] for c in campaigns),
              'sites':records,'campaigns':campaigns,'variants':variants,
              'boundary':'Training-derived compiler hints only; no semantic or all-input correctness promotion'}
    (args.out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    print(json.dumps({'sites':n,'variants':variants,'native_checks':protocol['instrumented_native_reference_checks']},indent=2))


if __name__=='__main__':main()
