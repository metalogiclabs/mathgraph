#!/usr/bin/env python3
"""Read-only independent adjudication replay of the frozen paired trial.

Usage: PYTHONPATH=ROOT/deps python -B verify_independently.py --root ROOT --out OUT
Only OUT is written. ROOT/trial and ROOT/sources are never modified.
Requires pinned PyYAML 6.0.3, Z3 4.15.4 and git; no network or native monitor.
Independent facts are checked without trusting investigator labels or resolver.
"""
from __future__ import annotations
import argparse, collections, hashlib, itertools, json, os, pathlib, re, subprocess, sys, time
from fractions import Fraction as Q
sys.dont_write_bytecode = True
P=pathlib.Path
ap=argparse.ArgumentParser(); ap.add_argument('--root',type=P,default=P(__file__).resolve().parent.parent);ap.add_argument('--out',type=P,required=True);args=ap.parse_args()
ROOT=args.root.resolve();OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
assert OUT!=ROOT and ROOT/'trial' not in OUT.parents and ROOT/'sources' not in OUT.parents
T=ROOT/'trial';S=ROOT/'sources';F=ROOT/'repo/research/semantic_discovery_six'
START=time.perf_counter();IO=collections.Counter();COMMANDS=[]
def read(p):
 b=P(p).read_bytes();IO['file_reads']+=1;IO['bytes_read']+=len(b);return b
def jread(p):return json.loads(read(p))
def digest(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
 p=P(p);p.parent.mkdir(parents=True,exist_ok=True);b=v if isinstance(v,bytes) else (json.dumps(v,indent=2,sort_keys=True)+'\n').encode();p.write_bytes(b);IO['file_writes']+=1;IO['bytes_written']+=len(b)
def cmd(argv,cwd=None,env=None):
 st=time.perf_counter();p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=60)
 COMMANDS.append({'argv':argv,'cwd':str(cwd) if cwd else None,'returncode':p.returncode,'seconds':time.perf_counter()-st,'stdout_bytes':len(p.stdout),'stderr_bytes':len(p.stderr)})
 return p
def git(domain,rev,path=None):
 p=cmd(['git','show',rev+(':'+path if path else '')],S/domain);assert p.returncode==0,p.stderr;return p.stdout

def exact(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
 return a==b

# Deliberately independent S-expression scanner; original commands are normative.
def forms(text):
 tokens=[];i=0
 while i<len(text):
  c=text[i]
  if c.isspace():i+=1;continue
  if c==';':
   e=text.find('\n',i);i=len(text) if e<0 else e;continue
  if c in '()':tokens.append(c);i+=1;continue
  start=i
  if c=='"':
   i+=1
   while i<len(text):
    if text[i]=='"':
     i+=1
     if i<len(text) and text[i]=='"':i+=1;continue
     break
    i+=1
   else:raise ValueError('unterminated SMT string')
  elif c=='|':
   i=text.index('|',i+1)+1
  else:
   while i<len(text) and not text[i].isspace() and text[i] not in '();':i+=1
  tokens.append(text[start:i])
 stack=[];out=[]
 for token in tokens:
  if token=='(':stack.append([])
  elif token==')':
   assert stack;v=stack.pop();(stack[-1] if stack else out).append(v)
  else:assert stack;stack[-1].append(token)
 assert not stack
 return out

def problem(fs):
 names=[];hard=[];soft=[];queries=0;queried=False
 for f in fs:
  op=f[0]
  if op in ['set-info']:continue
  if op in ['declare-fun','declare-const']:
   assert not queried
   if op=='declare-fun':assert len(f)==4 and f[2:]==[[],'Bool']
   else:assert len(f)==3 and f[2]=='Bool'
   assert f[1] not in names;names.append(f[1])
  elif op in ['assert','assert-soft']:
   assert not queried and len(f)==2
   (hard if op=='assert' else soft).append(f[1])
  elif op=='check-sat':assert f==[op];queries+=1;queried=True
  elif op=='set-option':assert f==['set-option',':produce-models','true']
  else:assert f in [['get-objectives'],['get-model'],['exit']],f
 assert queries==1
 return names,hard,soft

def val(e,a):
 if isinstance(e,str):
  if e in ['true','false']:return e=='true'
  assert e in a and type(a[e]) is bool;return a[e]
 op=e[0];vs=[val(x,a) for x in e[1:]]
 if op=='not':assert len(vs)==1;return not vs[0]
 if op=='or':return any(vs)
 if op=='and':return all(vs)
 if op=='=>':assert len(vs)==2;return (not vs[0]) or vs[1]
 raise ValueError(e)

def modelcheck(a,names,hard,soft):
 assert set(a)==set(names) and all(type(x) is bool for x in a.values())
 return all(val(e,a) for e in hard),sum(not val(e,a) for e in soft)

selection=jread(T/'selection_receipt.json');inv=jread(T/'invocation_receipt.json');audit=jread(T/'mechanical_audit.json')
protocol=read(F/'protocol.json');pins=json.loads(protocol)['repositories'];freeze=selection['freeze_commit']
assert digest(protocol)==selection['protocol_sha256']
identities={'frozen_files':{},'source_pins':{},'cases':{},'selection':{},'invocation':{}}
for name in ['protocol.json','common_prompt.txt','mathgraph_prompt.txt','conventional_prompt.txt','select_cases.py','broker.py','adjudication_prompt.txt']:
 p=cmd(['git','show',freeze+':research/semantic_discovery_six/'+name],ROOT/'repo');assert p.returncode==0
 assert p.stdout==read(F/name);identities['frozen_files'][name]=digest(p.stdout)
core=cmd(['git','show',freeze+':mathgraph_check/warrant_resolution.py'],ROOT/'repo');assert core.returncode==0
for domain,pin in pins.items():
 p=cmd(['git','rev-parse','HEAD'],S/domain);assert p.stdout.decode().strip()==pin['commit'];identities['source_pins'][domain]=pin['commit']
roster=jread(T/'private/selection_roster.json')
for domain,rows in roster.items():
 assert len(rows)==selection['eligible'][domain]
 ranks=[]
 for row in rows:
  rank=digest(protocol+domain.encode()+row['origin'].encode());assert rank==row['rank'];ranks.append(rank)
 assert ranks==sorted(ranks)
 identities['selection'][domain]={'eligible':len(rows),'first_two':rows[:2],'rank_formula_verified':True,'eligibility_independence':'frozen eligibility executable separately replayed below'}
# Replay frozen eligibility to verify full roster, without invoking selector's writing entrypoint.
import importlib.util
spec=importlib.util.spec_from_file_location('frozen_selector_independent_replay',F/'select_cases.py');selector=importlib.util.module_from_spec(spec);spec.loader.exec_module(selector)
st=time.perf_counter();pool=selector.eligible(S);eligibility_seconds=time.perf_counter()-st
for domain,rows in pool.items():
 reconstructed=sorted([{'origin':r['origin'],'source_sha256':digest(r['raw']),'rank':digest(protocol+domain.encode()+r['origin'].encode())} for r in rows],key=lambda x:x['rank'])
 assert reconstructed==roster[domain]
identities['eligibility_replay_seconds']=eligibility_seconds
originals={x['case_id']:x for x in jread(T/'private/originals.json')};cards={};finals={};metrics={}
for arm in ['mathgraph','conventional']:
 A=T/arm; finals[arm]=jread(A/'results/final.json')
 common=read(F/'common_prompt.txt');role=read(F/(arm+'_prompt.txt'))
 assert digest(common)==inv[arm]['common_source_sha256'] and digest(role)==inv[arm]['role_source_sha256']
 assert digest(read(A/'kit/instructions.txt'))==inv[arm]['instructions_sha256']
 assert read(A/'kit/warrant_resolution.py')==core.stdout
 identities['invocation'][arm]={'common_and_role_hashes_match':True,'instructions_hash_matches':True,'identical_resolver_matches_public_freeze':True}
 for c in selection['cases']:
  b=read(A/'inputs'/(c['case_id']+'.json'));assert digest(b)==c['input_sha256'];d=json.loads(b)
  assert d['case_id']==c['case_id']
  if c['case_id'] in cards:assert d==cards[c['case_id']]
  cards[c['case_id']]=d
 h=digest(read(A/'results/final.json'));assert h==read(A/'results/final.sha256').decode().split()[0]==read(A/'results/.final.lock').decode().strip()==audit['arms'][arm]['final_sha256']
 assert {c['case_id'] for c in finals[arm]['cases']}==set(cards)
 # Recompute mechanical totals and verify request, output, snapshot and blob identities.
 events=[json.loads(l) for l in read(A/'journal.jsonl').splitlines()];starts={e['request_id']:e for e in events if e['phase']=='start'};ends={e['request_id']:e for e in events if e['phase']=='end'}
 assert starts.keys()==ends.keys() and 2*len(starts)==len(events)
 for p in (A/'results/.broker-audit/blobs').iterdir():assert digest(read(p))==p.name
 for p in (A/'results/.broker-audit/runs').glob('*.json'):
  snap=jread(p);assert snap['complete']
  for name,entry in snap['entries'].items():
   if entry['type']=='file':assert digest(read(A/entry['path']))==entry['sha256']
 for rid,e in ends.items():
  req=jread(A/e['request_artifact']['path']);assert digest(read(A/e['request_artifact']['path']))==e['request_artifact']['sha256']
  assert req['request_id']==rid and req['action']==e['action']
  assert digest(read(A/req['payload']['path']))==req['payload']['sha256']
  if e['action']=='run':
   for stream in ['stdout','stderr']:assert read(A/e[stream+'_path'])==read(A/e[stream+'_artifact']['path'])
 credit=collections.Counter()
 for e in starts.values():credit[e['case']]+=e['credits']
 recomputed={'requests':len(starts),'actions':dict(collections.Counter(e['action'] for e in starts.values())),'credits_by_case':dict(credit),'total_credits':sum(credit.values()),'failed_requests':sum(not e['ok'] for e in ends.values()),'input_bytes':sum(e['input_bytes'] for e in starts.values()),'output_bytes':sum(e['output_bytes'] for e in ends.values()),'written_bytes_including_versions':sum(e['written_bytes'] for e in ends.values()),'audit_written_bytes':sum(e['audit_written_bytes'] for e in ends.values()),'broker_execution_seconds':sum(e['elapsed_seconds'] for e in ends.values()),'journal_span_seconds':(max(e['wall_end_ns'] for e in ends.values())-min(e['wall_start_ns'] for e in starts.values()))/1e9}
 for k,v in recomputed.items():assert v==audit['arms'][arm][k],(arm,k,v,audit['arms'][arm][k])
 fin=next(e for e in ends.values() if e['action']=='finalize');lock_time=(A/'results/.final.lock').stat().st_mtime_ns;final_time=(A/'results/final.json').stat().st_mtime_ns
 assert fin['wall_start_ns']<=lock_time<=fin['wall_end_ns'] and fin['wall_start_ns']<=final_time<=fin['wall_end_ns']
 post=[e for e in ends.values() if e['wall_start_ns']>fin['wall_end_ns']]
 assert [e['action'] for e in post]==['read','run']
 assert post[0]['path']==fin['request_artifact']['path']
 assert post[1]['argv'][1]=='-c' and not any(x in post[1]['argv'][2] for x in ['inputs','yaml','z3','CoCoSpec','read_text','write_text'])
 versions=[]
 for p in (A/'results/.broker-audit/writes').glob('*.json'):
  w=jread(p);entry=w['new']
  if w['path'].startswith('work/') and w['path'].endswith('.py'):versions.append({'path':w['path'],'bytes':entry['bytes'],'sha256':entry['sha256'],'request_id':w['request_id']})
 recomputed.update(final_sha256=h,final_mtime_ns=final_time,lock_mtime_ns=lock_time,finalize_start_ns=fin['wall_start_ns'],finalize_end_ns=fin['wall_end_ns'],post_lock_actions=[{'request_id':e['request_id'],'action':e['action'],'argv':e.get('argv'),'path':e.get('path'),'credits':starts[e['request_id']]['credits'],'classification':'CLERICAL_FINAL_RECEIPT_ONLY'} for e in post],generated_code_write_versions=versions,generated_code_bytes_all_versions=sum(x['bytes'] for x in versions),generated_code_bytes_current=sum(p.stat().st_size for p in (A/'work').glob('*.py')),research_journal_span_through_final_lock_seconds=(fin['wall_end_ns']-min(e['wall_start_ns'] for e in starts.values()))/1e9,post_lock_credits=sum(starts[e['request_id']]['credits'] for e in post),native_subprocess_seconds=sum(e.get('run_seconds',0) for e in ends.values()))
 metrics[arm]=recomputed

# Independently authenticate selected source blobs and exact extraction, never only hashes.
for cid,d in cards.items():
 o=originals[cid];domain=d['domain'];origin=o['origin'];file=origin.split('#')[0];raw=git(domain,pins[domain]['commit'],file)
 assert raw==o['raw_source'].encode() and digest(raw)==o['source_sha256']==d['provenance']['source_sha256']
 ranked=roster[domain][0:2];ix=next(i for i,x in enumerate(ranked) if x['origin']==origin)
 assert cid==domain[0]+'-'+ranked[ix]['rank'][:12]
 assert d['context']['source_receipt']==('WITHDRAWN' if domain in ['aerospace','mathematics'] and ix==1 else 'CURRENT')
 findings={'origin':origin,'source_sha256':digest(raw),'raw_source_equals_private':True,'input_sha256':digest(read(T/'mathgraph/inputs'/(cid+'.json')))}
 if domain=='yaml':
  expected_raw=git(domain,pins[domain]['commit'],str(P(file).with_name('in.json')));assert expected_raw==o['raw_expected_json'].encode()
  assert d['candidate']['yaml'].encode()==raw and exact(d['requirement']['expected_json'],json.loads(expected_raw))
  findings['expected_json_sha256']=digest(expected_raw)
 elif domain=='aerospace':
  document=json.loads(raw);v=document
  for token in origin.split('#')[1].strip('/').split('/'):v=v[int(token)] if isinstance(v,list) else v[token.replace('~1','/').replace('~0','~')]
  assert d['source_record']==v and d['source_variables']==document['variables']
  assert d['requirement']['text']==v['fulltext'] and d['candidate']['formula']==v['semantics']['CoCoSpecCode']
 else:
  original_forms=forms(raw.decode());visible=forms(d['requirement']['smt2']);filtered=[f for f in original_forms if not (f[:2]==['set-info',':status'])]
  assert filtered==visible
  findings.update(original_commands_equals_visible_after_declared_metadata_removal=True,raw_and_extracted_bytes_differ=raw!=d['requirement']['smt2'].encode(),extracted_smt_sha256=digest(d['requirement']['smt2'].encode()),hidden_external_status=o['hidden_external_status'])
 identities['cases'][cid]=findings

# Native YAML replay against independently fetched official JSON, strict types.
import yaml,z3
assert yaml.__version__=='6.0.3' and z3.get_version_string()=='4.15.4'
yaml_results={};math_results={};tables={}
for cid,d in cards.items():
 if d['domain']=='yaml':
  value=yaml.load(d['candidate']['yaml'],Loader=yaml.SafeLoader);expected=json.loads(originals[cid]['raw_expected_json']);assert exact(value,expected)
  yaml_results[cid]={'native_version':yaml.__version__,'loader':'SafeLoader','actual':value,'expected':expected,'type':type(value).__name__,'strict_type_structure_value_equality':True,'codepoints':[ord(x) for x in value]}
  for arm in finals:
   c=next(x for x in finals[arm]['cases'] if x['case_id']==cid);assert c['verdict']=='WARRANTED'
   assert exact(c['witness'].get('actual',c['witness'].get('actual_and_expected')),value)
 if d['domain']=='mathematics':
  names,hard,soft=problem(forms(originals[cid]['raw_source']));assert (names,hard,soft)==problem(forms(d['requirement']['smt2']))
  rows=[]
  for mask in range(1<<len(names)):
   a={n:bool(mask&(1<<i)) for i,n in enumerate(names)};h,p=modelcheck(a,names,hard,soft);rows.append({'assignment':a,'hard_ok':h,'penalty':p})
  assert len({tuple(r['assignment'][n] for n in names) for r in rows})==2**len(names)
  feasible=[r for r in rows if r['hard_ok']];minimum=min(r['penalty'] for r in feasible)
  native=[]
  for label,text in [('original',originals[cid]['raw_source']),('investigator_input',d['requirement']['smt2'])]:
   opt=z3.Optimize();opt.from_string(text);status=str(opt.check());assert status=='sat';m=opt.model();a={n:z3.is_true(m.eval(z3.Bool(n),model_completion=True)) for n in names};h,p=modelcheck(a,names,hard,soft);assert h and p==minimum
   native.append({'text':label,'status':status,'model':a,'independently_valid_hard_constraints':h,'independently_computed_penalty':p,'objectives':[str(x) for x in opt.objectives()]})
  witnesses={}
  for arm in finals:
   c=next(x for x in finals[arm]['cases'] if x['case_id']==cid);h,p=modelcheck(c['witness'],names,hard,soft);assert h and p==minimum;witnesses[arm]={'hard_ok':h,'penalty':p,'optimal':True}
   suffix='-analysis-final.json' if arm=='mathgraph' else '_math.json';artifact=jread(T/arm/'results'/(cid+suffix))
   assert artifact['total_assignments' if arm=='mathgraph' else 'independent_assignments_examined']==len(rows)
   assert artifact['feasible_assignments' if arm=='mathgraph' else 'hard_satisfying_assignments']==len(feasible)
   if arm=='mathgraph':
    cert=artifact['enumeration_certificate'];assert len(cert)==len(rows);assert len({tuple(r['assignment'][n] for n in names) for r in cert})==len(rows)
    for row in cert:
     h,p=modelcheck(row['assignment'],names,hard,soft);assert row['hard_ok']==h and row['penalty']==p;assert row['hard_values']==[val(e,row['assignment']) for e in hard];assert row['soft_values']==[val(e,row['assignment']) for e in soft]
  # Elementary lower bounds independent of enumeration and native solver.
  if len(names)==4:
   assert hard==[['or',['not','n2'],['not','n3']]];argument='n2 and n3 cannot both be true; at least one positive soft clause fails. Final witness attains penalty 1.'
  else:
   for edge in [['or','A','B'],['or','C','D'],['or','E','F']]:assert edge in hard
   assert soft==[['not',x] for x in ['A','C','B','D','E','F','G']];argument='Disjoint hard edges (A,B), (C,D), (E,F) require at least three true variables. B,D,E cover all seven edges and attain penalty 3.'
  tables[cid]=rows;math_results[cid]={'native_engine':z3.get_version_string(),'declared_names':names,'hard_assertions':hard,'soft_preferences':soft,'assignments':len(rows),'feasible_assignments':len(feasible),'minimum_unit_soft_penalty':minimum,'feasible_penalty_histogram':dict(collections.Counter(r['penalty'] for r in feasible)),'native_replays':native,'final_witnesses':witnesses,'independent_elementary_argument':argument,'current_source_authority':d['context']['source_receipt']}

# Pinned source implementation, independent recurrence semantics, no C monitor claim.
libpath='fret-electron/support/CommonTemplates/LibraryOfOperators.ejs';lib=git('aerospace',pins['aerospace']['commit'],libpath);write(OUT/'source/LibraryOfOperators.ejs',lib)
compact=re.sub(r'\s+','',lib.decode())
for fragment in ['Y=X->(Xand(preY));','Y=false->preX;','D=delay(X,R);Y=OTlore(L-R,D);','C=ifXthen0else(-1->preC+(ifpreC<0then0else1));','Y=0<=CandC<=N;']:assert fragment in compact,fragment

def historically(xs):
 out=[];prev=True
 for x in xs:prev=bool(x and prev);out.append(prev)
 return out

def bounded_once_recurrence(xs,upper):
 counter=-1;out=[]
 for i,x in enumerate(xs):
  counter=0 if x else -1 if i==0 else counter+(0 if counter<0 else 1)
  out.append(0<=counter<=upper)
 return out

# Verify recurrence against separate window semantics on every Boolean sequence through length 6.
checks=0
for n in range(1,7):
 for bits in itertools.product([False,True],repeat=n):
  for bound in [0,1,2,4]:
   assert bounded_once_recurrence(bits,bound)==[any(bits[max(0,i-bound):i+1]) for i in range(n)];checks+=1
  assert historically(bits)==[all(bits[:i+1]) for i in range(n)];checks+=1

def alphabet(text):
 literals={Q(t) for t in re.findall(r'(?<![A-Za-z_0-9])[-+]?(?:\d+(?:\.\d*)?|\.\d+)',text)}
 vals={Q(-1),Q(0),Q(1)}
 for x in literals:vals.update([x-1,x,x+1])
 return sorted(vals)

def qjson(x):
 if isinstance(x,Q):return int(x) if x.denominator==1 else float(x)
 if isinstance(x,dict):return {k:qjson(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [qjson(v) for v in x]
 return x

aero={};aero_rows={}
for cid,d in cards.items():
 if d['domain']!='aerospace':continue
 text=d['requirement']['text'];a=alphabet(text);types={};bindings={};frame_names=[]
 if ' shall for ' in text:
  m=re.fullmatch(r'(\w+) shall for (\d+) secs satisfy (\w+)<=\s*([\d.]+) & (\w+) >= (-[\d.]+)',text);assert m
  component,duration,name,upper,name2,lower=m.groups();assert name==name2;duration=int(duration);upper=Q(upper);lower=Q(lower);frame_names=[name]
  expected=f'H((OT({duration},0,not(YtoPre(true)))=>(({name}<={float(upper)})and({name}>={float(lower)}))))'
  assert re.sub(r'\s+','',d['candidate']['formula'])==expected
  def source(trace,times=None):
   ts=list(range(len(trace))) if times is None else times
   return all(lower<=Q(str(f[name]))<=upper for f,t in zip(trace,ts) if 0<=t-ts[0]<=duration)
  def candidate(trace):
   # YtoPre(true) is false initially; OT(L,0,not(...)) uses R=0, so delay is identity.
   guard=bounded_once_recurrence([True]+[False]*(len(trace)-1),duration)
   return historically([(not g) or lower<=Q(str(f[name]))<=upper for f,g in zip(trace,guard)])[-1]
 else:
  m=re.fullmatch(r'(\w+) shall always satisfy (\w+) =(\d+) => (\w+) = ([\d.]+) \* \((\w+) \+(\w+)\)',text);assert m
  component,flag,trigger,out,factor,left,right=m.groups();trigger=Q(trigger);factor=Q(factor);frame_names=sorted([flag,out,left,right])
  expected=f'H((({flag}={int(trigger)})=>({out}=({float(factor)}*({left}+{right})))))'
  assert re.sub(r'\s+','',d['candidate']['formula'])==expected
  def frame_truth(f):return Q(str(f[flag]))!=trigger or Q(str(f[out]))==factor*(Q(str(f[left]))+Q(str(f[right])))
  def source(trace,times=None):return all(frame_truth(f) for f in trace)
  def candidate(trace):return historically([frame_truth(f) for f in trace])[-1]
 for name in frame_names:
  rows=[v for v in d['source_variables'] if v.get('component_name')==component and v.get('variable_name')==name and not v.get('modeldoc')];assert len(rows)==1;row=rows[0];dt=row['dataType'];assert dt in ['double','int32','boolean']
  types[name]=dt;bindings[name]={'declaration_id':row['_id'],'type':dt,'modeldoc_id':row['modeldoc_id'],'assignment':row['assignment'],'modelComponent':row['modelComponent']}
 domains={name:([False,True] if dt=='boolean' else [x for x in a if x.denominator==1] if dt=='int32' else a) for name,dt in types.items()}
 frames=[dict(zip(frame_names,v)) for v in itertools.product(*(domains[n] for n in frame_names))];counts={str(n):len(frames)**n for n in [1,2,3]};cohort=sum(counts.values());retained={};independent=[]
 if cohort<=4096:
  for n in [1,2,3]:
   for trace in itertools.product(frames,repeat=n):
    x=source(trace);y=candidate(trace);assert x==y;independent.append({'trace':qjson(trace),'source':x,'candidate':y})
  assert len(independent)==cohort
  assert len({json.dumps(x['trace'],sort_keys=True) for x in independent})==cohort
  aero_rows[cid]=independent
 for arm in ['mathgraph','conventional']:
  if arm=='mathgraph':
   rows=jread(T/arm/'results'/(cid+'-cohort.json'))
   if cohort<=4096:assert rows==independent
  else:
   obs=jread(T/arm/'results'/(cid+'_temporal.json'));rows=[]
   quotas={1:1366,2:1365,3:1365}
   for n in [1,2,3]:
    count=counts[str(n)];q=min(count,quotas[n]);indices=range(count) if cohort<=4096 else sorted({i*(count-1)//(q-1) for i in range(q)})
    for ix in indices:
     k=ix;trace=[None]*n
     for pos in range(n-1,-1,-1):trace[pos]=frames[k%len(frames)];k//=len(frames)
     rows.append({'trace':qjson(trace),'source':source(trace),'candidate':candidate(trace)})
   assert len(rows)==obs['examined'] and obs['cohort_total']==cohort
   assert dict(collections.Counter(str(len(r['trace'])) for r in rows))==obs['examined_by_length']
   assert sum(r['source'] for r in rows)==obs['source_true_count'] and sum(r['candidate'] for r in rows)==obs['candidate_true_count']
  keys=set();bylength=collections.Counter()
  for row in rows:
   trace=row['trace'];assert 1<=len(trace)<=3;bylength[len(trace)]+=1
   key=json.dumps(trace,sort_keys=True);assert key not in keys;keys.add(key)
   for frame in trace:
    assert set(frame)==set(frame_names)
    for name in frame_names:assert Q(str(frame[name])) in domains[name]
   assert type(row['source']) is bool and type(row['candidate']) is bool
   assert row['source']==source(trace) and row['candidate']==candidate(trace) and row['source']==row['candidate']
  assert len(rows)==min(cohort,4096)
  retained[arm]={'validated_unique_traces':len(rows),'by_length':dict(bylength),'complete_requested_value_cohort':len(rows)==cohort,'mismatches':0,'trace_type_and_alphabet_membership_validated':True,'source_and_candidate_values_independently_recomputed':True}
 clock=None
 if component=='NN':
  trace=[{frame_names[0]:0},{frame_names[0]:11}];times=[0,201];assert source(trace,times) and not candidate(trace)
  # This is not admitted into the untimestamped cohort as a refutation.
  clock={'trace':trace,'times_seconds':times,'source_elapsed_seconds':source(trace,times),'candidate_sample_positions':candidate(trace),'classification':'CONDITIONAL_CLOCK_SEPARATION_NOT_ADMITTED_REFUTATION'}
  relevant=[v for v in d['source_variables'] if v.get('component_name')=='NN' or v.get('fretComponent')=='NN'];clock_fields=[]
  def scan(v,path):
   if isinstance(v,dict):
    for k,x in v.items():
     if re.search(r'sampl|period|clock|time.?unit|time.?step',k,re.I):clock_fields.append({'path':path+[k],'value':x})
     scan(x,path+[k])
   elif isinstance(v,list):
    for i,x in enumerate(v):scan(x,path+[i])
  scan(relevant,['NN_declarations']);scan(d['source_record'],['source_record']);assert not clock_fields
  clock.update(relevant_source_rows=len(relevant),declared_clock_fields=clock_fields)
 aero[cid]={'operative_text':text,'candidate_formula':d['candidate']['formula'],'source_types':types,'bindings':bindings,'alphabet':qjson(a),'typed_domains':qjson(domains),'frame_count':len(frames),'cohort_by_length':counts,'cohort_total':cohort,'cap':4096,'independent_full_value_replay_traces':len(independent),'retained_arm_certificates':retained,'conditional_clock_witness':clock,'native_C_monitor':'NOT_RUN','source_library':{'path':libpath,'sha256':digest(lib),'checked_recurrence_tests':checks,'boundary':'Pinned source equations read and translated independently; no Lustre compiler or runtime monitor qualification.'}}

# Reconstruct every actual before-run environment from immutable snapshots,
# including code versions later overwritten, and rerun without repairing anything.
replays=[];env=dict(os.environ,PYTHONPATH=str(ROOT/'deps'),PYTHONDONTWRITEBYTECODE='1')
for arm in ['mathgraph','conventional']:
 A=T/arm;events=[json.loads(l) for l in read(A/'journal.jsonl').splitlines()]
 for event in events:
  if event['phase']!='end' or event['action']!='run':continue
  rid=event['request_id'];snap=jread(A/event['snapshots']['before']['path']);dest=OUT/'replays'/arm/rid;dest.mkdir(parents=True,exist_ok=True);codes={}
  for name,entry in snap['entries'].items():
   target=dest/name;assert dest in target.resolve().parents
   if entry['type']=='directory':target.mkdir(parents=True,exist_ok=True)
   elif entry['type']=='file':
    b=read(A/entry['path']);assert digest(b)==entry['sha256'];write(target,b);target.chmod(entry['mode'])
    if name.startswith('work/') and name.endswith('.py'):codes[name]=entry['sha256']
   else:raise ValueError(('unsupported snapshot entry',name,entry))
  p=cmd(event['argv'],dest/'work',env);write(dest/'independent-replay.stdout',p.stdout);write(dest/'independent-replay.stderr',p.stderr)
  assert p.returncode==event['process_exit'],(arm,rid,p.stderr)
  # Timestamps and absolute paths may vary; original byte comparisons are reported, not silently normalized.
  produced={}
  after=jread(A/event['snapshots']['after']['path'])
  for name,entry in after['entries'].items():
   if entry['type']=='file' and name.startswith('results/') and not name.startswith('results/runs/') and (dest/name).is_file():
    current=read(dest/name);before=snap['entries'].get(name)
    if before is None or before.get('sha256')!=entry['sha256']:produced[name]={'original_sha256':entry['sha256'],'replay_sha256':digest(current),'byte_equal':digest(current)==entry['sha256']}
  replays.append({'arm':arm,'request_id':rid,'case':event['case'],'argv':event['argv'],'before_snapshot':event['snapshots']['before'],'code_versions':codes,'expected_returncode':event['process_exit'],'actual_returncode':p.returncode,'stdout_byte_equal':p.stdout==read(A/event['stdout_path']),'stderr_byte_equal':p.stderr==read(A/event['stderr_path']),'changed_result_files':produced,'retained_replay_root':str(dest.relative_to(OUT))})

report={'identities':identities,'metrics':metrics,'versions':{'python':sys.version,'PyYAML':yaml.__version__,'Z3':z3.get_version_string()},'yaml':yaml_results,'mathematics':math_results,'aerospace':aero,'snapshot_replays':replays,'effort':{'measured_script_wall_seconds':time.perf_counter()-START,'instrumented_file_io':dict(IO),'subprocess_calls':len(COMMANDS),'subprocess_wall_seconds':sum(x['seconds'] for x in COMMANDS),'limitations':'Does not measure model reasoning/tokens, initial inspection commands or host provisioning; IO counters cover this script and snapshot copying, not OS/kernel or native Python library reads.'}}
write(OUT/'independent_math_truth_tables.json',tables);write(OUT/'independent_aerospace_complete_cohort.json',aero_rows);write(OUT/'subprocess_commands.json',COMMANDS);write(OUT/'verification_results.json',report)
print(json.dumps({'status':'PASSED','verified_case_count':len(cards),'native_yaml_cases':len(yaml_results),'independently_enumerated_boolean_assignments':sum(x['assignments'] for x in math_results.values()),'original_run_snapshots_replayed':len(replays),'failures_reproduced':sum(x['actual_returncode']!=0 for x in replays),'output':str(OUT/'verification_results.json'),'wall_seconds':time.perf_counter()-START},indent=2))
