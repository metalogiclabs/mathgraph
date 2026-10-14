"""V39: test whether anonymous component-relative identity is the missing support object.

V38 showed verified compression of local pixel contexts materially improves recurrence,
but support transfer remains weak. Replace literal local windows with a more structural,
color-equivariant identity: connected same-value component shape (translated to origin)
plus the cell's relative coordinate inside that component and component multiplicity by
shape. No named ARC semantics or held-out outputs are used for induction.

First test training label collisions. Then, when separable, freeze signature->support
labels and evaluate held-out support recurrence/accuracy. Collisions among identical
component roles imply the missing distinction is relational BETWEEN components.
"""
import json,sys
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v34_raw_support_induction as v34
TARGET_IDS=sorted(v34.TARGET_IDS)

def comp_map(g):
    h,w=v34.shape(g);seen=set(); comps=[]; at={}
    for i in range(h):
      for j in range(w):
       if (i,j) in seen:continue
       val=g[i][j];stack=[(i,j)];seen.add((i,j));cells=[]
       while stack:
        a,b=stack.pop();cells.append((a,b))
        for da,db in ((1,0),(-1,0),(0,1),(0,-1)):
         u,v=a+da,b+db
         if 0<=u<h and 0<=v<w and (u,v) not in seen and g[u][v]==val:
          seen.add((u,v));stack.append((u,v))
       r0=min(a for a,b in cells);c0=min(b for a,b in cells)
       shp=tuple(sorted((a-r0,b-c0) for a,b in cells)); idx=len(comps)
       comps.append({'cells':cells,'shape':shp,'r0':r0,'c0':c0})
       for p in cells:at[p]=idx
    mult=Counter(c['shape'] for c in comps)
    return comps,at,mult

def signatures(g):
    comps,at,mult=comp_map(g);out={}
    for p,ci in at.items():
      c=comps[ci];rel=(p[0]-c['r0'],p[1]-c['c0'])
      out[p]=(c['shape'],rel,mult[c['shape']])
    return out

def train_model(t):
    by=defaultdict(lambda:[0,0])
    for p in t['train']:
      if v34.shape(p['input'])!=v34.shape(p['output']):return {'status':'SHAPE_CHANGE_TRAIN'}
      yy=v34.changed(p['input'],p['output'])
      for pos,s in signatures(p['input']).items():by[s][int(pos in yy)]+=1
    coll={s:z for s,z in by.items() if z[0] and z[1]}
    if coll:return {'status':'COMPONENT_ROLE_INADEQUATE','collision_signatures':len(coll),'ambiguous_cells':sum(sum(z) for z in coll.values()),'labels':None}
    return {'status':'COMPONENT_ROLE_SEPARABLE','collision_signatures':0,'ambiguous_cells':0,'labels':{s:bool(z[1]) for s,z in by.items()}}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[];models=[]
    for tid in TARGET_IDS:
      m=train_model(tasks[tid]);models.append({'task':tid,**{k:v for k,v in m.items() if k!='labels'}})
      for qi,p in enumerate(tasks[tid]['test']):
       if 'output' not in p:continue
       if m['status']!='COMPONENT_ROLE_SEPARABLE' or v34.shape(p['input'])!=v34.shape(p['output']):
        row={'task':tid,'test_index':qi,'status':m['status']}
       else:
        ss=signatures(p['input']);yy=v34.changed(p['input'],p['output']);pred={pos for pos,s in ss.items() if m['labels'].get(s,False)};seen=sum(s in m['labels'] for s in ss.values())
        inter=len(pred&yy);prec=inter/len(pred) if pred else (1.0 if not yy else 0.0);rec=inter/len(yy) if yy else 1.0
        row={'task':tid,'test_index':qi,'status':'EVAL','predicted':len(pred),'target':len(yy),'intersection':inter,'precision':prec,'recall':rec,'exact_support':pred==yy,'seen_fraction':seen/len(ss) if ss else 0}
       rows.append(row);print(json.dumps(row,sort_keys=True),flush=True)
    result={'schema':'verified-developmental-navigation.arc-agi2-component-role-adequacy.v39','evidence_label':'TRAIN_ONLY_STRUCTURAL_IDENTITY_THEN_KNOWN_WORLD_EVAL','models':models,'rows':rows,
      'separable_tasks':sum(m['status']=='COMPONENT_ROLE_SEPARABLE' for m in models),
      'principle':'If two cells have the same anonymous component role but different verifier futures, object-internal identity is too coarse and the missing state is relational between components.',
      'routing':'Broad component-role collisions force an inter-component relation lift; separability with poor recurrence forces quotienting component roles across source-distinct histories.'}
    out=HERE/'results_v39_component_role_adequacy';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({'models':models,'separable_tasks':result['separable_tasks']},indent=2,sort_keys=True))
if __name__=='__main__':main()
