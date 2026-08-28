import hashlib, importlib.util, json, math, random, re, sys
from collections import Counter,defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v21=load('v21','run_v21_defeasible_cross_task_policy.py');v19=v21.v19;v20=v21.v20;v13=v21.v13
MAX_QUERIES=8;TARGET_ID='60c09cac';SHAM_SEED=20260828

def fp(k):
 out=[]
 for p in k.split(':'):
  if re.fullmatch(r'd\d+',p):out.append('d*')
  elif re.fullmatch(r'r\d+',p):out.append('r*')
  elif re.fullmatch(r'c\d+',p):out.append('c*')
  else:out.append(p)
 return ':'.join(out)
def audit(task):return v20.audit_task(task)
def legal(states,keys,demo,held):return bool(states) and not any(s['truncated'] for s in states) and 0<sum(demo)<len(states) and v19.unresolved(states,keys,demo)==0 and v19.unresolved(states,keys,held)==0

def profile(states,candidates):
 return Counter(fp(k) for k in candidates)
def cosine(a,b):
 keys=set(a)|set(b);dot=sum(a[k]*b[k] for k in keys);na=math.sqrt(sum(v*v for v in a.values()));nb=math.sqrt(sum(v*v for v in b.values()));return dot/(na*nb) if na and nb else 0.0

def source_examples(tasks):
 examples=[];literal=defaultdict(float);lcount=defaultdict(int);global_pref=Counter();rows=[]
 for tid in sorted(tasks):
  states,keys,demo,held=audit(tasks[tid])
  if not legal(states,keys,demo,held):continue
  chosen=[];hist=[];steps=[]
  for _ in range(MAX_QUERIES):
   if v19.unresolved(states,chosen,demo)==0:break
   cur=v19.collision(states,chosen,demo)
   if cur is None:break
   hist.append(cur);cand=[k for k in keys if k not in chosen and v19.separates(states,k,cur)]
   if not cand:break
   k,_=v19.history_atom(states,keys,chosen,cur,list(hist))
   if k is None:break
   ex={'profile':dict(profile(states,cand)),'selected_fp':fp(k),'history_len':len(hist)};examples.append(ex);steps.append((cur,k));global_pref[fp(k)]+=1;chosen.append(k)
  for k in keys:
   cov=sum(v19.separates(states,k,p) for p in hist);literal[k]+=cov;lcount[k]+=1
  rows.append({'task':tid,'steps':len(steps),'exact':v19.sufficient(states,chosen,demo)})
 return examples,{k:literal[k]/lcount[k] for k in literal},global_pref,rows

def conditional_scores(cur_profile,examples):
 scores=defaultdict(float)
 sims=sorted(((cosine(cur_profile,Counter(ex['profile'])),i) for i,ex in enumerate(examples)),reverse=True)[:12]
 for sim,i in sims:
  if sim>0:scores[examples[i]['selected_fp']]+=sim
 return scores

def run(states,keys,labels,examples=None,literal=None,sham=False):
 chosen=[];hist=[];trace=[]
 exs=examples or []
 if sham and exs:
  rng=random.Random(SHAM_SEED);sel=[e['selected_fp'] for e in exs];rng.shuffle(sel);exs=[dict(e,selected_fp=sel[i]) for i,e in enumerate(exs)]
 for step in range(MAX_QUERIES):
  before=v19.unresolved(states,chosen,labels)
  if before==0:break
  cur=v19.collision(states,chosen,labels)
  if cur is None:break
  hist.append(cur);cand=[k for k in keys if k not in chosen and v19.separates(states,k,cur)]
  if not cand:break
  cp=profile(states,cand);cs=conditional_scores(cp,exs) if exs else {}
  def score(k):
   support=sum(v19.separates(states,k,p) for p in hist)
   diversity=len(set((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in hist))
   cond=cs.get(fp(k),0.0);lit=0 if literal is None else literal.get(k,0.0)
   return (support,diversity,cond,lit,hashlib.sha256(k.encode()).hexdigest())
  k=max(cand,key=score);chosen.append(k);trace.append({'query':step+1,'pair':cur,'atom':k,'fingerprint':fp(k),'conditional_score':cs.get(fp(k),0.0),'before':before,'after':v19.unresolved(states,chosen,labels)})
 return chosen,trace

def main():
 if len(sys.argv)!=3:raise SystemExit('usage ... TRAIN EVAL')
 train=v13.v2.v1.load_tasks(sys.argv[1]);ev=v13.v2.v1.load_tasks(sys.argv[2])
 examples,raw,global_pref,source_rows=source_examples(train)
 states,keys,demo,held=audit(ev[TARGET_ID]);assert legal(states,keys,demo,held)
 specs={'WARM':(examples,None,False),'COLD':(None,None,False),'RAW_HISTORY':(None,raw,False),'SHAM':(examples,None,True),'ANCESTOR_ABLATION':(None,None,False)};arms={}
 for n,(ex,lit,sh) in specs.items():
  chosen,trace=run(states,keys,demo,ex,lit,sh);arms[n]={'queries_used':len(chosen),'exact':v19.sufficient(states,chosen,demo) and v19.sufficient(states,chosen,held),'unresolved':v19.unresolved(states,chosen,demo),'atoms':chosen,'trace':trace}
 controls=['COLD','RAW_HISTORY','SHAM','ANCESTOR_ABLATION'];frontier=arms['WARM']['exact'] and all(not arms[n]['exact'] for n in controls);eff=arms['WARM']['exact'] and all(arms[n]['exact'] for n in controls) and arms['WARM']['queries_used']<min(arms[n]['queries_used'] for n in controls);strict=frontier or eff
 result={'schema':'verified-developmental-navigation.arc-residual-conditional-transfer.v22','source':{'split':'training','legal_source_tasks':len(source_rows),'source_examples':len(examples)},'target':{'split':'evaluation','task':TARGET_ID,'selection':'sole legal fresh evaluation carrier established mechanically by V20b before transfer outcome was tested','states':len(states),'future_positive':sum(demo)},'precommit':{'max_queries':MAX_QUERIES,'policy':'live residual support > live diversity > nearest-neighbour vote from anonymous separator-profile to previously useful query fingerprint > raw literal tie > hash','sham':'deterministic permutation of learned source selected-fingerprint labels across identical source residual profiles','pass':'WARM-only exact frontier OR all-arm exact with WARM strictly fewer queries than every control'},'arms':arms,'source_rows':source_rows,'strict_gate':'PASS_RESIDUAL_CONDITIONAL_CROSS_SPLIT_DEVELOPMENT' if strict else 'FAIL_RESIDUAL_CONDITIONAL_CROSS_SPLIT_DEVELOPMENT','claim_boundary':'Single mechanically selected held-out ARC evaluation carrier. Residual-conditioned policy transfer only; no new observation language, constructor language, or formability claim.'}
 out=HERE/'results_v22_residual_conditional_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
