import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

v23 = load('v23','run_v23_observation_generator_transfer.py')
v13 = v23.v13
ARC2_COMMIT='f3283f727488ad98fe575ea6a5ac981e4a188e49'
TARGET_N=8
MAX_SCAN=300


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v24c_arcagi2_early_carriers.py ARC2_TRAIN')
    tasks=v13.v2.v1.load_tasks(sys.argv[1])
    found=[]; scanned=0; scan=[]
    for tid in sorted(tasks):
        if scanned>=MAX_SCAN or len(found)>=TARGET_N: break
        scanned+=1
        p=v23.audit_task(tid,tasks[tid])
        mixed=v23.mixed(p) and not p['truncated']
        row={'task':tid,'states':len(p['states']),'mixed':mixed,'truncated':p['truncated'],'future_positive':sum(p['demo']),'schemas':len(p['schemas']),'atoms':len(p['keys'])}
        if mixed:
            row['full_demo_unresolved']=v23.unresolved(p,p['schemas'])
            row['full_heldout_unresolved']=v23.unresolved(p,p['schemas'],p['held'])
            row['full_exact']=v23.full_sufficient(p)
            oracle5,trace=v23.oracle_select(p,v23.SCHEMA_BUDGET)
            row['oracle5_exact']=v23.sufficient(p,oracle5) and v23.sufficient(p,oracle5,p['held'])
            row['oracle5_schemas']=oracle5
            row['oracle5_trace']=trace
            found.append(row)
        scan.append(row)
    result={'schema':'verified-developmental-navigation.arcagi2-early-carriers.v24c','source':{'repository':'arcprize/ARC-AGI-2','commit':ARC2_COMMIT},'target_n':TARGET_N,'max_scan':MAX_SCAN,'scanned':scanned,'found':len(found),'carrier_tasks':[r['task'] for r in found],'full_exact_tasks':[r['task'] for r in found if r.get('full_exact')],'oracle5_exact_tasks':[r['task'] for r in found if r.get('oracle5_exact')],'decision':'ARC2_EARLY_CARRIERS_FOUND' if found else 'ARC2_NO_EARLY_CARRIERS','carriers':found,'scan':scan}
    out=HERE/'results_v24c_arcagi2_early_carriers';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k not in ('scan','carriers')},indent=2,sort_keys=True))
if __name__=='__main__': main()
