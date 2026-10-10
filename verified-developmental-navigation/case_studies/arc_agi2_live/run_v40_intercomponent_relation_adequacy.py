"""V40: test the relation lift forced by V39.

V39 showed object-internal component roles are training-inadequate on 6/7 tasks.
Add only anonymous relations between components: relative centroid direction/distance
bins to the nearest component of the same shape and nearest different shape, plus
component-rank/multiplicity facts. No named ARC semantics and no held-out outputs
are used to construct the representation.

First ask whether the relation lift removes train collisions. If separable, freeze
signature->support labels and evaluate held-out recurrence/support.
"""
import json,sys,math
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v34_raw_support_induction as v34, run_v39_component_role_adequacy as v39
TARGET_IDS=sorted(v34.TARGET_IDS)

def sgn(x): return -1 if x<0 else (1 if x>0 else 0)
def dbin(x):
    if x is None:return None
    if x<=1:return 1
    if x<=2:return 2
    if x<=4:return 4
    return 5

def comp_info(g):
    comps,at,mult=v39.comp_map(g)
    for c in comps:
        n=len(c['cells'])
        c['centroid']=(sum(a for a,b in c['cells'])/n,sum(b for a,b in c['cells'])/n)
        rs=[a for a,b in c['cells']];cs=[b for a,b in c['cells']]
        c['bbox']=(max(rs)-min(rs)+1,max(cs)-min(cs)+1)
    return comps,at,mult

def nearest_rel(comps,i,pred):
    ci=comps[i]; ar,ac=ci['centroid']; best=None
    for j,cj in enumerate(comps):
        if j==i or not pred(cj):continue
        br,bc=cj['centroid']; dr,dc=br-ar,bc-ac; d=abs(dr)+abs(dc)
        key=(d,abs(dr),abs(dc),j)
        if best is None or key<best[0]:best=(key,(sgn(dr),sgn(dc),dbin(d),cj['shape'],cj['bbox']))
    return None if best is None else best[1]

def signatures(g):
    comps,at,mult=comp_info(g)
    sizes=[len(c['cells']) for c in comps]
    size_mult=Counter(sizes)
    out={}
    for p,ci in at.items():
        c=comps[ci]; rel=(p[0]-c['r0'],p[1]-c['c0']); n=len(c['cells'])
        same=nearest_rel(comps,ci,lambda q:q['shape']==c['shape'])
        diff=nearest_rel(comps,ci,lambda q:q['shape']!=c['shape'])
        # Anonymous relation signature: object-internal role + inter-object geometry.
        out[p]=(c['shape'],rel,mult[c['shape']],n,size_mult[n],same,diff)
    return out

def train_model(t):
    by=defaultdict(lambda:[0,0])
    for pair in t['train']:
        if v34.shape(pair['input'])!=v34.shape(pair['output']):return {'status':'SHAPE_CHANGE_TRAIN'}
        yy=v34.changed(pair['input'],pair['output'])
        for pos,s in signatures(pair['input']).items():by[s][int(pos in yy)]+=1
    coll={s:z for s,z in by.items() if z[0] and z[1]}
    if coll:return {'status':'RELATION_INADEQUATE','collision_signatures':len(coll),'ambiguous_cells':sum(sum(z) for z in coll.values()),'labels':None}
    return {'status':'RELATION_SEPARABLE','collision_signatures':0,'ambiguous_cells':0,'labels':{s:bool(z[1]) for s,z in by.items()}}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[];models=[]
    for tid in TARGET_IDS:
        m=train_model(tasks[tid]);models.append({'task':tid,**{k:v for k,v in m.items() if k!='labels'}})
        for qi,pair in enumerate(tasks[tid]['test']):
            if 'output' not in pair:continue
            if m['status']!='RELATION_SEPARABLE' or v34.shape(pair['input'])!=v34.shape(pair['output']):
                row={'task':tid,'test_index':qi,'status':m['status']}
            else:
                ss=signatures(pair['input']); yy=v34.changed(pair['input'],pair['output']); pred={pos for pos,s in ss.items() if m['labels'].get(s,False)};seen=sum(s in m['labels'] for s in ss.values())
                inter=len(pred&yy);prec=inter/len(pred) if pred else (1.0 if not yy else 0.0);rec=inter/len(yy) if yy else 1.0
                row={'task':tid,'test_index':qi,'status':'EVAL','predicted':len(pred),'target':len(yy),'intersection':inter,'precision':prec,'recall':rec,'exact_support':pred==yy,'seen_fraction':seen/len(ss) if ss else 0}
            rows.append(row);print(json.dumps(row,sort_keys=True),flush=True)
    result={'schema':'verified-developmental-navigation.arc-agi2-intercomponent-relation-adequacy.v40','evidence_label':'TRAIN_ONLY_RELATION_LIFT_THEN_KNOWN_WORLD_EVAL','models':models,'rows':rows,'separable_tasks':sum(m['status']=='RELATION_SEPARABLE' for m in models),
      'principle':'When object-internal roles alias verifier-distinct futures, add only the minimum inter-object relations needed to split those aliases.',
      'routing':'If relation lift restores separability, quotient the relation signature for recurrence. Persistent collisions force a richer/nonlocal relation family rather than more local context.'}
    out=HERE/'results_v40_intercomponent_relation_adequacy';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({'models':models,'separable_tasks':result['separable_tasks']},indent=2,sort_keys=True))
if __name__=='__main__':main()
