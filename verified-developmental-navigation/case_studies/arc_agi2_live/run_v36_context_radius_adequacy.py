"""V36: after V35 proves unary observations inadequate, test the smallest
color-equivariant relational/context lift that can separate training edit support.

For each cell, build a canonical equality-pattern signature of its radius-r local
window (out-of-bounds has its own symbol). Literal color names are erased by
first-occurrence canonicalization, so the representation is translation-invariant
and color-equivariant. Increase r only until changed/unchanged support labels no
longer collide. This is an adequacy test, not a task solver.
"""
import json,sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v34_raw_support_induction as v34
TARGET_IDS=sorted(v34.TARGET_IDS)
MAX_R=5

def canon_window(g,i,j,r):
    h,w=v34.shape(g); ids={}; nxt=0; out=[]
    for di in range(-r,r+1):
      for dj in range(-r,r+1):
        a,b=i+di,j+dj
        if not (0<=a<h and 0<=b<w): out.append(-1); continue
        v=g[a][b]
        if v not in ids: ids[v]=nxt;nxt+=1
        out.append(ids[v])
    return tuple(out)

def radius_stats(t,r):
    by=defaultdict(lambda:[0,0])
    for p in t['train']:
      if v34.shape(p['input'])!=v34.shape(p['output']):return None
      yy=v34.changed(p['input'],p['output']);g=p['input'];h,w=v34.shape(g)
      for i in range(h):
       for j in range(w):
        s=canon_window(g,i,j,r);by[s][int((i,j) in yy)]+=1
    coll=[z for z in by.values() if z[0] and z[1]]
    cells=sum(sum(z) for z in by.values());amb=sum(sum(z) for z in coll)
    return {'radius':r,'unique_signatures':len(by),'collision_signatures':len(coll),
            'cells_in_collision_signatures':amb,'collision_fraction':amb/cells if cells else 0.0,
            'separable':len(coll)==0}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in TARGET_IDS:
      curve=[];first=None
      for r in range(MAX_R+1):
        q=radius_stats(tasks[tid],r)
        if q is None:break
        curve.append(q)
        if q['separable'] and first is None:first=r
      row={'task':tid,'minimal_separating_radius':first,'curve':curve};rows.append(row)
      print(json.dumps({'task':tid,'minimal_separating_radius':first,'collision_fractions':[round(x['collision_fraction'],4) for x in curve]},sort_keys=True),flush=True)
    result={'schema':'verified-developmental-navigation.arc-agi2-context-radius-adequacy.v36',
      'evidence_label':'TRAIN_ONLY_CONTEXT_ADEQUACY_TEST','max_radius':MAX_R,'rows':rows,
      'separable_within_radius_count':sum(r['minimal_separating_radius'] is not None for r in rows),
      'principle':'When unary quotient aliases cells with different verifier futures, add the minimum relational context needed to split those aliases; do not add named ontology first.',
      'routing':'If bounded local context removes collisions, induce support in that quotient. Persistent collisions force a nonlocal relation lift.'}
    out=HERE/'results_v36_context_radius_adequacy';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
