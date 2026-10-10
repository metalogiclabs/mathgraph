"""V38: compress V36's training-sufficient local context before transfer.

V37 showed that the smallest separating radius still memorizes mostly novel held-out
windows. Apply the same verified-forgetting law inside that context: start from all
offsets in the minimum separating window and greedily delete offsets while the
remaining color-equivariant signature still has zero changed/unchanged label
collisions on every training cell. Freeze that minimal sufficient projection, then
evaluate held-out support recurrence and accuracy.
"""
import json,sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v34_raw_support_induction as v34, run_v36_context_radius_adequacy as v36
TARGET_IDS=sorted(v34.TARGET_IDS)

def sig(g,i,j,offsets):
    h,w=v34.shape(g);ids={};nxt=0;out=[]
    for di,dj in offsets:
      a,b=i+di,j+dj
      if not (0<=a<h and 0<=b<w):out.append(-1);continue
      v=g[a][b]
      if v not in ids:ids[v]=nxt;nxt+=1
      out.append(ids[v])
    return tuple(out)

def collisions(t,offsets):
    by=defaultdict(lambda:[0,0])
    for p in t['train']:
      if v34.shape(p['input'])!=v34.shape(p['output']):return 10**9
      yy=v34.changed(p['input'],p['output']);g=p['input'];h,w=v34.shape(g)
      for i in range(h):
       for j in range(w):by[sig(g,i,j,offsets)][int((i,j) in yy)]+=1
    return sum(1 for z in by.values() if z[0] and z[1])

def learn(t):
    r=None
    for q in range(v36.MAX_R+1):
      z=v36.radius_stats(t,q)
      if z and z['separable']:r=q;break
    if r is None:return None
    offsets=[(di,dj) for di in range(-r,r+1) for dj in range(-r,r+1)]
    full=len(offsets);changed=True
    while changed:
      changed=False
      for o in list(offsets):
        trial=[x for x in offsets if x!=o]
        if trial and collisions(t,trial)==0:
          offsets=trial;changed=True
    labels={}
    for p in t['train']:
      yy=v34.changed(p['input'],p['output']);g=p['input'];h,w=v34.shape(g)
      for i in range(h):
       for j in range(w):labels[sig(g,i,j,offsets)]=((i,j) in yy)
    return {'radius':r,'full_offsets':full,'offsets':offsets,'labels':labels}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[];summ=[]
    for tid in TARGET_IDS:
      model=learn(tasks[tid]);
      if model:summ.append({'task':tid,'radius':model['radius'],'full_offsets':model['full_offsets'],'retained_offsets':len(model['offsets']),'compression':1-len(model['offsets'])/model['full_offsets']})
      for qi,p in enumerate(tasks[tid]['test']):
       if 'output' not in p:continue
       if model is None or v34.shape(p['input'])!=v34.shape(p['output']):
        row={'task':tid,'test_index':qi,'status':'UNAVAILABLE'}
       else:
        g=p['input'];yy=v34.changed(g,p['output']);h,w=v34.shape(g);pred=set();seen=0
        for i in range(h):
         for j in range(w):
          s=sig(g,i,j,model['offsets'])
          if s in model['labels']:
           seen+=1
           if model['labels'][s]:pred.add((i,j))
        inter=len(pred&yy);prec=inter/len(pred) if pred else (1.0 if not yy else 0.0);rec=inter/len(yy) if yy else 1.0
        row={'task':tid,'test_index':qi,'status':'EVAL','radius':model['radius'],'retained_offsets':len(model['offsets']),
             'predicted':len(pred),'target':len(yy),'intersection':inter,'precision':prec,'recall':rec,'exact_support':pred==yy,
             'seen_fraction':seen/(h*w)}
       rows.append(row);print(json.dumps(row,sort_keys=True),flush=True)
    ev=[x for x in rows if x['status']=='EVAL']
    result={'schema':'verified-developmental-navigation.arc-agi2-minimal-context-projection.v38','evidence_label':'TRAIN_ONLY_VERIFIED_CONTEXT_COMPRESSION_THEN_KNOWN_WORLD_EVAL',
      'models':summ,'rows':rows,'exact_support':sum(x['exact_support'] for x in ev),
      'mean_precision':sum(x['precision'] for x in ev)/len(ev) if ev else None,'mean_recall':sum(x['recall'] for x in ev)/len(ev) if ev else None,
      'mean_seen_fraction':sum(x['seen_fraction'] for x in ev)/len(ev) if ev else None,
      'principle':'A context should retain only offsets necessary to preserve verifier-distinct futures on training; transfer then tests whether the resulting quotient recurs.',
      'routing':'If recurrence/recall improves materially, continue quotient minimization with source-distinct controls. If not, local pixel context is the wrong identity object and lift to relational/object correspondence.'}
    out=HERE/'results_v38_minimal_context_projection';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
