"""V30: residual-conditioned selector learning from source-distinct verified history.

V29 showed a global selector prior is underdetermined. V30 scans the full pinned
ARC-AGI-2 training set, collects ambiguous continuation episodes after V26
minimal-context quotienting, and conditions selector statistics on a compact
residual signature available without target outputs:
  - ambiguity multiplicity bucket
  - changed-support size bucket
  - retained-context size bucket
  - patch aspect class

For a target ambiguous episode, use the most specific source signature with
support >= MIN_SUPPORT; otherwise back off by progressively dropping fields,
finally abstaining rather than injecting an unsupported global preference.
Evaluation outputs are never used to learn or select the policy.
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26, run_v28_learned_selector as v28

TARGET_IDS=sorted(v26.FIT_IDS)
MIN_SUPPORT=2
SELECTORS=[s for s in v28.SELECTORS if s!='unique']

def bucket(n):
    if n<=1:return '1'
    if n<=3:return '2-3'
    if n<=7:return '4-7'
    if n<=15:return '8-15'
    if n<=31:return '16-31'
    return '32+'

def aspect(r):
    if r['h']==r['w']:return 'square'
    return 'tall' if r['h']>r['w'] else 'wide'

def signature(r,k,n):
    changed=sum(sum(1 for x in row if x) for row in r['mask'])
    return (bucket(n),bucket(changed),bucket(len(k)),aspect(r))

def keys_for(sig):
    a,b,c,d=sig
    # most specific to increasingly coarse residual classes; no unconditional global key
    return [(a,b,c,d),(a,b,c,'*'),(a,b,'*','*'),(a,'*','*','*')]

def train_bank(tasks):
    bank=defaultdict(lambda:{s:{'wins':0,'trials':0} for s in SELECTORS})
    summary={'scanned':0,'strict_fit_tasks':0,'compressed_tasks':0,'ambiguous_episodes':0}
    for tid,t in sorted(tasks.items()):
      summary['scanned']+=1
      rs,u=v23.learn_rules(t)
      if u!=len(t['train']) or not rs:continue
      strict=[v26.initial_keep(r) for r in rs]
      if not v26.exact_train(t,rs,strict):continue
      summary['strict_fit_tasks']+=1
      ks,_,_=v26.minimize(t,rs);summary['compressed_tasks']+=1
      for r,k in zip(rs,ks):
       for p in t['train']:
        cs=v28.candidates(p['input'],r,k)
        if len(cs)<=1:continue
        good={(a,b) for a,b,m in cs if v28.local_correct(p['input'],p['output'],r,(a,b,m))}
        if not good:continue
        summary['ambiguous_episodes']+=1
        sig=signature(r,k,len(cs))
        for key in keys_for(sig):
         st=bank[key]
         for s in SELECTORS:
          c=v28.choose(cs,s,p['input']);st[s]['trials']+=1
          if c is not None and (c[0],c[1]) in good:st[s]['wins']+=1
    return bank,summary

def choose_policy(bank,sig):
    for key in keys_for(sig):
      st=bank.get(key)
      if not st:continue
      eligible=[s for s in SELECTORS if st[s]['trials']>=MIN_SUPPORT]
      if not eligible:continue
      ranked=sorted(eligible,key=lambda s:(-(st[s]['wins']/st[s]['trials']),-st[s]['trials'],s))
      s=ranked[0]
      return s,key,st[s]
    return None,None,None

def prog(rs,ks,bank,telemetry):
 def f(g):
  z=[list(x) for x in g]
  for _ in range(16):
   before=tuple(map(tuple,z))
   for r,k in zip(rs,ks):
    cs=v28.candidates(z,r,k)
    if len(cs)==1:c=cs[0]
    elif len(cs)>1:
      sig=signature(r,k,len(cs));pol,key,support=choose_policy(bank,sig)
      telemetry.append({'matches':len(cs),'signature':sig,'policy':pol,'backoff_key':key,'support':support})
      c=v28.choose(cs,pol,z) if pol else None
    else:c=None
    if c is None:continue
    a,b,m=c
    for i in range(r['h']):
     for j in range(r['w']):
      if r['mask'][i][j]:
       q=r['out'][i][j];z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
   if tuple(map(tuple,z))==before:break
  return tuple(map(tuple,z))
 return f

def main():
 if len(sys.argv)!=3:raise SystemExit('usage ... TRAIN_DIR EVAL_DIR')
 train=run_v2.v1.load_tasks(sys.argv[1]);ev=run_v2.v1.load_tasks(sys.argv[2]);bank,source=train_bank(train)
 rows=[]; alltel=[]
 for tid in TARGET_IDS:
  t=ev[tid];rs,u=v23.learn_rules(t);ks,_,_=v26.minimize(t,rs);tel=[];p=prog(rs,ks,bank,tel)
  fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t));solved=False
  try:solved=bool(fit and run_v2.v1.task_solved(p,t))
  except Exception:pass
  rows.append({'task':tid,'train_fit':fit,'heldout_solved':solved,'selector_events':tel});alltel.extend(tel)
 result={'schema':'verified-developmental-navigation.arc-agi2-residual-conditioned-selector.v30',
  'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_TRANSFER_TEST','selection_uses_evaluation_outputs':False,
  'source_summary':source,'min_support':MIN_SUPPORT,'residual_signature':['match_count','changed_support','retained_context','aspect'],
  'target_train_fit_count':sum(r['train_fit'] for r in rows),'heldout_solved_ids':[r['task'] for r in rows if r['heldout_solved']],
  'target_selector_events':len(alltel),'target_supported_selector_events':sum(e['policy'] is not None for e in alltel),
  'principle':'Selector value is residual-relative. Back off only across verified source residual classes; abstain when source support is insufficient.',
  'rows':rows}
 out=HERE/'results_v30_residual_conditioned_selector';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));
 print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True));
 for r in rows: print(r)
if __name__=='__main__':main()
