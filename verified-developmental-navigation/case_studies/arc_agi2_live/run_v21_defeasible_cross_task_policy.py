import hashlib, importlib.util, json, random, re, sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v20c=load('v20c','run_v20c_cross_split_policy_transfer.py');v19=v20c.v19;v20=v20c.v20;v13=v20c.v13
MAX_QUERIES=8;SHAM_SEED=20260828;SKIP_FIRST_LEGAL=6

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

def split_bucket(tid):
 # Frozen source/target split independent of labels or outcomes.
 return int(hashlib.sha256(tid.encode()).hexdigest()[0],16)%2

def source_history(states,keys,labels):
 chosen=[];hist=[]
 for _ in range(MAX_QUERIES):
  if v19.unresolved(states,chosen,labels)==0:break
  cur=v19.collision(states,chosen,labels)
  if cur is None:break
  hist.append(cur);k,_=v19.history_atom(states,keys,chosen,cur,list(hist))
  if k is None:break
  chosen.append(k)
 return chosen,hist

def compile_policy(source_rows,sham=False):
 total=defaultdict(float);count=defaultdict(int);literal=defaultdict(float);lcount=defaultdict(int)
 for si,(tid,states,keys,demo,held) in enumerate(source_rows):
  chosen,hist=source_history(states,keys,demo)
  if sham:
   rng=random.Random(SHAM_SEED+si+len(states));perm=list(range(len(states)));rng.shuffle(perm);hist=[(perm[a],perm[b]) for a,b in hist]
  for k in keys:
   cov=sum(v19.separates(states,k,p) for p in hist if max(p)<len(states));f=fp(k)
   total[f]+=cov;count[f]+=1;literal[k]+=cov;lcount[k]+=1
 return {f:total[f]/count[f] for f in total},{k:literal[k]/lcount[k] for k in literal}

def run(states,keys,labels,prior=None,literal=None):
 chosen=[];hist=[];trace=[]
 for step in range(MAX_QUERIES):
  before=v19.unresolved(states,chosen,labels)
  if before==0:break
  cur=v19.collision(states,chosen,labels)
  if cur is None:break
  hist.append(cur);cand=[k for k in keys if k not in chosen and v19.separates(states,k,cur)]
  if not cand:break
  def score(k):
   # MSI ordering: current certified residual evidence dominates inherited experience.
   support=sum(v19.separates(states,k,p) for p in hist)
   diversity=len(set((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in hist))
   inherited=0 if prior is None else prior.get(fp(k),0.0)
   lit=0 if literal is None else literal.get(k,0.0)
   return (support,diversity,inherited,lit,hashlib.sha256(k.encode()).hexdigest())
  k=max(cand,key=score);chosen.append(k);trace.append({'query':step+1,'pair':cur,'atom':k,'fingerprint':fp(k),'before':before,'after':v19.unresolved(states,chosen,labels)})
 return chosen,trace

def main():
 if len(sys.argv)!=2:raise SystemExit('usage ... TRAIN')
 tasks=v13.v2.v1.load_tasks(sys.argv[1]);legal_rows=[]
 for tid in sorted(tasks):
  states,keys,demo,held=audit(tasks[tid])
  if legal(states,keys,demo,held):legal_rows.append((tid,states,keys,demo,held))
 remaining=legal_rows[SKIP_FIRST_LEGAL:]
 source=[x for x in remaining if split_bucket(x[0])==0];target=[x for x in remaining if split_bucket(x[0])==1]
 warm,raw=compile_policy(source,False);sham,_=compile_policy(source,True)
 rows=[]
 for tid,states,keys,demo,held in target:
  specs={'WARM':(warm,None),'COLD':(None,None),'RAW_HISTORY':(None,raw),'SHAM':(sham,None),'ANCESTOR_ABLATION':(None,None)};arms={}
  for n,(p,l) in specs.items():
   chosen,trace=run(states,keys,demo,p,l);arms[n]={'queries_used':len(chosen),'exact':v19.sufficient(states,chosen,demo) and v19.sufficient(states,chosen,held),'unresolved':v19.unresolved(states,chosen,demo),'atoms':chosen,'trace':trace}
  rows.append({'task':tid,'states':len(states),'future_positive':sum(demo),'arms':arms})
 names=['WARM','COLD','RAW_HISTORY','SHAM','ANCESTOR_ABLATION']
 exact={n:sum(r['arms'][n]['exact'] for r in rows) for n in names};unresolved={n:sum(r['arms'][n]['unresolved'] for r in rows) for n in names};queries={n:sum(r['arms'][n]['queries_used'] for r in rows) for n in names}
 warm_only=[r['task'] for r in rows if r['arms']['WARM']['exact'] and not any(r['arms'][n]['exact'] for n in names[1:])]
 # Pass either by strict frontier expansion or equal maximal coverage at strictly lower cost than every control.
 max_control=max(exact[n] for n in names[1:]) if rows else 0
 frontier=bool(warm_only) and exact['WARM']>max_control and unresolved['WARM']<min(unresolved[n] for n in names[1:])
 efficiency=bool(rows) and exact['WARM']==len(rows) and all(exact[n]==len(rows) for n in names[1:]) and queries['WARM']<min(queries[n] for n in names[1:])
 strict=frontier or efficiency
 result={'schema':'verified-developmental-navigation.arc-defeasible-cross-task-policy.v21','selection':{'legal_carriers_total':len(legal_rows),'excluded_previously_observed_first_legal':SKIP_FIRST_LEGAL,'remaining':len(remaining),'source_split':'sha256(task_id) first hex parity even','target_split':'sha256(task_id) first hex parity odd','source_tasks':[x[0] for x in source],'target_tasks':[x[0] for x in target]},'precommit':{'max_queries':MAX_QUERIES,'policy_order':'live residual support > live residual diversity > inherited source fingerprint prior > literal/raw prior > deterministic hash','arms':names,'pass':'strict WARM-only frontier expansion OR all arms full coverage with WARM strictly lower total query cost than every control'},'tasks':rows,'summary':{'exact_tasks':exact,'unresolved_totals':unresolved,'query_totals':queries,'warm_only_exact_targets':warm_only,'frontier_gate':frontier,'efficiency_gate':efficiency},'strict_gate':'PASS_DEFEASIBLE_CROSS_TASK_DEVELOPMENT' if strict else 'FAIL_DEFEASIBLE_CROSS_TASK_DEVELOPMENT','claim_boundary':'Disjoint task transfer within frozen ARC training carrier after excluding the six tasks observed in V20c. Current verifier residuals dominate inherited experience. Policy/discovery efficiency or frontier only; no new observation language or formability.'}
 out=HERE/'results_v21_defeasible_cross_task_policy';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
