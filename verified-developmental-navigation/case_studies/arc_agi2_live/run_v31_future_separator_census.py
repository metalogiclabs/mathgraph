"""V31: do candidate continuations become distinguishable by verified futures?

V30 showed residual-conditioned *local* selectors have evidence but do not close
held-out capability. Here we test the more fundamental hypothesis on source
training episodes only: when a minimized rule has multiple admissible matches,
score each candidate not by geometry but by the error remaining after applying
that candidate and then executing the rest of the learned program using only
unambiguous continuations. Ask whether minimum future error uniquely selects a
candidate that the verifier identifies as locally correct.

This is a census/diagnostic, not a held-out ARC claim.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26, run_v28_learned_selector as v28

MAX_EPISODES=250

def apply_choice(z,r,c):
    a,b,m=c
    for i in range(r['h']):
      for j in range(r['w']):
        if r['mask'][i][j]:
          q=r['out'][i][j];z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])

def continue_unique(z,rs,ks,skip_ri=None,rounds=8):
    z=[list(x) for x in z]
    for _ in range(rounds):
      before=tuple(map(tuple,z))
      for ri,(r,k) in enumerate(zip(rs,ks)):
        cs=v28.candidates(z,r,k)
        if len(cs)==1: apply_choice(z,r,cs[0])
      if tuple(map(tuple,z))==before:break
    return tuple(map(tuple,z))

def err(a,b):
    if v23.shape(a)!=v23.shape(b):return 10**9
    h,w=v23.shape(a)
    return sum(a[i][j]!=b[i][j] for i in range(h) for j in range(w))

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... TRAIN_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]
    for tid,t in sorted(tasks.items()):
      if len(rows)>=MAX_EPISODES:break
      rs,u=v23.learn_rules(t)
      if u!=len(t['train']) or not rs:continue
      strict=[v26.initial_keep(r) for r in rs]
      if not v26.exact_train(t,rs,strict):continue
      ks,_,_=v26.minimize(t,rs)
      for pi,pair in enumerate(t['train']):
       for ri,(r,k) in enumerate(zip(rs,ks)):
        cs=v28.candidates(pair['input'],r,k)
        if len(cs)<=1:continue
        good={(a,b) for a,b,m in cs if v28.local_correct(pair['input'],pair['output'],r,(a,b,m))}
        if not good:continue
        scored=[]
        for ci,c in enumerate(cs):
          z=[list(x) for x in pair['input']];apply_choice(z,r,c)
          pred=continue_unique(z,rs,ks)
          scored.append({'candidate':ci,'pos':[c[0],c[1]],'future_error':err(pred,pair['output']),'locally_correct':(c[0],c[1]) in good})
        me=min(x['future_error'] for x in scored); mins=[x for x in scored if x['future_error']==me]
        rows.append({'task':tid,'train_index':pi,'rule_index':ri,'matches':len(cs),'min_future_error':me,
          'min_count':len(mins),'unique_future_separator':len(mins)==1,
          'unique_future_correct':len(mins)==1 and mins[0]['locally_correct'],
          'any_min_correct':any(x['locally_correct'] for x in mins),'scores':scored})
        if len(rows)>=MAX_EPISODES:break
       if len(rows)>=MAX_EPISODES:break
    n=len(rows); uniq=sum(r['unique_future_separator'] for r in rows); uc=sum(r['unique_future_correct'] for r in rows); amc=sum(r['any_min_correct'] for r in rows)
    result={'schema':'verified-developmental-navigation.arc-agi2-future-separator-census.v31',
      'evidence_label':'SOURCE_TRAINING_VERIFIER_DIAGNOSTIC','max_episodes':MAX_EPISODES,'episodes':n,
      'unique_future_separator_count':uniq,'unique_future_correct_count':uc,'any_min_correct_count':amc,
      'unique_separator_precision':(uc/uniq if uniq else None),'correct_in_minset_rate':(amc/n if n else None),
      'principle':'Candidate actions are compared by the protected futures they leave reachable, not by local geometry.',
      'rows':rows}
    out=HERE/'results_v31_future_separator_census';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
