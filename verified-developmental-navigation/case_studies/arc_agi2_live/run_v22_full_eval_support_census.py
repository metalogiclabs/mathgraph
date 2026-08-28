import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v21=load('v21','run_v21_transfer_frontier_census.py')
v13=v21.v13
EXCLUDE=set(v13.TARGETS)


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v22_full_eval_support_census.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    ids=[x for x in sorted(ev) if x not in EXCLUDE]
    rows=[]
    for tid in ids:
        try: rows.append(v21.audit_task(tid,ev[tid]))
        except Exception as e: rows.append({'task':tid,'status':'UNSUPPORTED','error':type(e).__name__+': '+str(e)[:240]})
    audited=[r for r in rows if r.get('status')=='AUDITED']
    positive=[r for r in audited if r.get('future_positive',0)>0]
    eligible=[r for r in positive if r.get('oracle',{}).get('exact') and not r.get('any_truncation') and (r.get('headroom_queries') or 0)>0]
    eligible=sorted(eligible,key=lambda r:(-r['headroom_queries'],r['oracle']['queries'],r['task']))
    result={'schema':'verified-developmental-navigation.arc-full-eval-support-census.v22',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'pool':'all evaluation task IDs excluding the four V13-V20 lineage tasks','max_states':v21.MAX_STATES,'continuation_language':'unchanged V13 one-further-base continuation','warm_policy_evaluated':False},
      'summary':{'pool':len(ids),'audited':len(audited),'positive_support_tasks':len(positive),'eligible_frontier':len(eligible),'unsupported':sum(r.get('status')=='UNSUPPORTED' for r in rows),'state_capped':sum(r.get('status')=='STATE_CAP' for r in rows),'full_language_collisions':sum(r.get('status')=='FULL_LANGUAGE_COLLISION' for r in rows)},
      'positive_support':[{'task':r['task'],'future_positive':r['future_positive'],'states':r['states'],'cold':r['cold'],'oracle':r['oracle'],'headroom_queries':r['headroom_queries']} for r in positive],
      'eligible_frontier':[{'task':r['task'],'future_positive':r['future_positive'],'states':r['states'],'cold':r['cold'],'oracle':r['oracle'],'headroom_queries':r['headroom_queries']} for r in eligible],
      'decision':'TRANSFER_FRONTIER_FOUND' if eligible else ('POSITIVE_SUPPORT_BUT_NO_HEADROOM' if positive else 'CONTINUATION_SUPPORT_COLLAPSE')}
    out=HERE/'results_v22_full_eval_support_census';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
