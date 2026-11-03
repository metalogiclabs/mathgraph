"""Configure the existing exact-expression and paired-native admission adapter."""
from pathlib import Path
import sys,importlib.util,json,re,copy
ROOT=Path(__file__).resolve().parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

reference=module('leading_reference',ROOT/'reference.py')
sys.path.insert(0,str(ROOT.parent/'check-expectation-admission-v1'))
base=module('leading_binding_base',ROOT.parent/'check-expectation-admission-v1'/'binding.py')
POLICY=json.loads((ROOT/'binding.json').read_text())
base.POLICY=POLICY;base.reference=reference
bind=base.bind
qualify=base.qualify

def policy_for_subject(subject):
    if not (subject.get('repository')==POLICY['subject']['repository'] and subject.get('path')==POLICY['subject']['path']
            and re.fullmatch('[a-f0-9]{40}',subject.get('revision','')) and re.fullmatch('[a-f0-9]{64}',subject.get('sha256',''))):
        raise ValueError('RECHECK_SUBJECT_INVALID')
    policy=copy.deepcopy(POLICY);policy['subject']=copy.deepcopy(subject)
    for p in policy['proposals']:p['subject']=copy.deepcopy(subject)
    return policy

if __name__=='__main__':
    import argparse,os
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--paired',action='store_true');p.add_argument('--candidate',action='store_true');args=p.parse_args()
    if args.candidate:
        POLICY=policy_for_subject(json.loads((ROOT/'candidate.json').read_text())['subject']);base.POLICY=POLICY
    context={'verifier_sha':os.environ['GITHUB_SHA'],'run_id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT'])}
    bindings={p['id']:bind(p,POLICY['subject']['sha256'])for p in POLICY['proposals']}
    result={'context':context,'bindings':bindings,'reference':reference.run_cohort(),'scope':POLICY['scope'],'hosted_repair_authorized':False}
    if args.paired:
        patch=json.loads((ROOT/'patch.json').read_text());base.POLICY={**POLICY,'patch':patch}
        inspection=json.loads((args.root/'inspection.json').read_text())
        if inspection.get('context')!=context:raise ValueError('INSPECTION_CONTEXT_CHANGED')
        result.update(qualify(inspection))
    else:result['status']='EXPECTATIONS_ADMITTED' if all(b['status']=='ADMITTED'for b in bindings.values())else 'UNKNOWN'
    (args.root/('binding-assessment.json'if args.paired else 'expectation-admission.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status']}))
