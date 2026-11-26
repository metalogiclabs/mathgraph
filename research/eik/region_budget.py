"""Exact-source counterfactual budgets on the two published champion draws.

All other instruction counts and code/table bytes stay fixed. This is a
conditional score-model calculation, not a measured optimization or a claim
about future draws. The no-change score is asserted against the official kit.
"""
import sys,json,math,argparse,hashlib,subprocess
from pathlib import Path
a=argparse.ArgumentParser(description="Fixed-size instruction-budget experiment; no optimized-program claim")
a.add_argument('--kit',type=Path,required=True);a.add_argument('--source',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
a=a.parse_args();kit=a.kit.resolve();src=a.source.resolve();p=a.out.resolve();p.mkdir(parents=True,exist_ok=True)
assert subprocess.check_output(['git','-C',kit,'rev-parse','HEAD'],text=True).strip()=='5a32428ad4aa23bce737d50a738ace24ddeeed2e'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37'
sys.path.insert(0,str(kit))
from eik import stages as ST,toolchain as T,inputs as I,score as S,config as K
from eik.emu import Core
regions=[('tanh-small-changed-family','tanh',0x3c000000,0x3e000000,False),('tanh-central','tanh',0x3e000000,0x40000000,False),('tanh-large','tanh',0x40000000,0x41103000,False),('sigmoid-central','sigmoid',0x3e800000,0x40800000,False),('exp-negative-common','exp',0xbe800000,0xc1000000,True),('exp-positive-common','exp',0x3e800000,0x41000000,True)]
all_results={}
for target,seed,champ in [('rv32im',1284956104,28.183514615086768),('thumbv6m',150897616,39.30415089582157)]:
 rep=ST.measure(src,seed,targets=[target],sample=False);(p/('budget-control-'+target+'.json')).write_text(json.dumps(rep,indent=2));assert rep['verdict']=='passed',rep
 b=rep['scores'][target]['S'];data={};c=Core(T.guest_image(src,target),target)
 for fn in K.FUNCTIONS:
  data[fn]={name:[(w,c.call(fn,w)[1]) for w in words] for name,words in I.draw(seed,fn).items()}
 def cost(region,cut):
  label,selected,lo,hi,signed=region;m={'functions':{}}
  for fn,sets in data.items():
   ss={}
   for name,words in sets.items():
    values=[n*(1-cut) if fn==selected and lo<=(w if signed else w&0x7fffffff)<hi else n for w,n in words]
    ss[name]={'mean':sum(values)/len(values),'p999':S._p(values,.999)}
   m['functions'][fn]=ss
  return S.score(m,rep['bytes'][target])[0]
 rows=[]
 for r in regions:
  assert abs(cost(r,0)-b)<1e-10
  scores={str(cut):cost(r,cut) for cut in [.25,.5,1.]};minimum=None
  if scores['1.0']<=.97*champ:
   low,high=0.,1.
   for _ in range(40):
    mid=(low+high)/2
    if cost(r,mid)<=.97*champ:high=mid
    else:low=mid
   minimum=high
  rows.append({'region':r[0],'zero_cost_score':scores['1.0'],'minimum_region_instruction_cut_to_bar':minimum,'scores_by_fraction_cut':scores})
 result={'source_sha256':rep['sha256'],'seed':seed,'baseline_S':b,'champion_S_on_same_published_seed':champ,'takeover_S':.97*champ,'fingerprint':rep['fingerprint'],'fixed_code_and_table_bytes':rep['bytes'][target],'boundary':'Counterfactual changes to instruction counts in the declared complete mathematical region; code/table bytes fixed. No optimized program or future-draw prediction is claimed.','regions':rows};all_results[target]=result
 (p/'region-budget.json').write_text(json.dumps(all_results,indent=2));print(target,json.dumps(result),flush=True)
