"""V37: does the minimum training-sufficient contextual quotient transfer?

V36 found a color-equivariant local radius (2..5) that removes all training
support-label collisions for every diagnostic task. Freeze the smallest such
radius per task, memorize only the verifier-induced signature -> support label
partition from training, and evaluate held-out support. Unseen signatures default
to unchanged. This tests whether adequacy-by-distinguishability is also sufficient
for transfer, versus merely separating the training history.
"""
import json,sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v34_raw_support_induction as v34, run_v36_context_radius_adequacy as v36
TARGET_IDS=sorted(v34.TARGET_IDS)

def learn(t):
    chosen=None
    for r in range(v36.MAX_R+1):
      q=v36.radius_stats(t,r)
      if q and q['separable']:
        chosen=r;break
    if chosen is None:return None
    lab={}
    for p in t['train']:
      yy=v34.changed(p['input'],p['output']);g=p['input'];h,w=v34.shape(g)
      for i in range(h):
       for j in range(w):
        lab[v36.canon_window(g,i,j,chosen)]=((i,j) in yy)
    return chosen,lab

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in TARGET_IDS:
      z=learn(tasks[tid])
      for qi,p in enumerate(tasks[tid]['test']):
        if 'output' not in p:continue
        if z is None:
          row={'task':tid,'test_index':qi,'status':'NO_SEPARATING_RADIUS'}
        elif v34.shape(p['input'])!=v34.shape(p['output']):
          row={'task':tid,'test_index':qi,'status':'SHAPE_CHANGE'}
        else:
          r,lab=z;g=p['input'];yy=v34.changed(g,p['output']);h,w=v34.shape(g);pred=set();seen=0;unseen=0
          for i in range(h):
           for j in range(w):
            s=v36.canon_window(g,i,j,r)
            if s in lab:
              seen+=1
              if lab[s]:pred.add((i,j))
            else:unseen+=1
          inter=len(pred&yy);prec=inter/len(pred) if pred else (1.0 if not yy else 0.0);rec=inter/len(yy) if yy else 1.0
          row={'task':tid,'test_index':qi,'status':'EVAL','radius':r,'predicted':len(pred),'target':len(yy),'intersection':inter,
               'precision':prec,'recall':rec,'exact_support':pred==yy,'seen_cells':seen,'unseen_cells':unseen,'seen_fraction':seen/(seen+unseen) if seen+unseen else 0}
        rows.append(row);print(json.dumps(row,sort_keys=True),flush=True)
    ev=[r for r in rows if r['status']=='EVAL']
    result={'schema':'verified-developmental-navigation.arc-agi2-context-support-transfer.v37','evidence_label':'TRAIN_ONLY_MINIMAL_CONTEXT_THEN_KNOWN_WORLD_EVAL',
      'rows':rows,'eval_tests':len(ev),'exact_support':sum(r['exact_support'] for r in ev),
      'mean_precision':sum(r['precision'] for r in ev)/len(ev) if ev else None,'mean_recall':sum(r['recall'] for r in ev)/len(ev) if ev else None,
      'mean_seen_fraction':sum(r['seen_fraction'] for r in ev)/len(ev) if ev else None,
      'principle':'Separating training futures is necessary for adequacy but transfer requires a quotient whose equivalence classes recur in new situations.',
      'routing':'If support transfers, induce effects next. If signatures are mostly unseen, compress relational context by future-equivalence across source-distinct histories rather than memorize literal windows.'}
    out=HERE/'results_v37_context_support_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
