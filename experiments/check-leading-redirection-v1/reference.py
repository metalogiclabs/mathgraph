"""Frozen adapter over the unchanged Bash interception implementation."""
from pathlib import Path
import importlib.util,json,hashlib,copy
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'check-expectation-admission-v1'/'run.py'
if hashlib.sha256(BASE.read_bytes()).hexdigest()!='47683258544a0b9a4e1697a9c8d9683184ccd7100da125aebbe999fb77cef12e':
    raise ValueError('REFERENCE_IMPLEMENTATION_CHANGED')
spec=importlib.util.spec_from_file_location('leading_bash_reference_base',BASE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
COHORT=json.loads((ROOT/'cohort.json').read_text())
# Trusted release configuration, never a model or source-PR command list.
base.COHORT=COHORT
base.TRUSTED_COMMANDS=frozenset(c['command'] for c in COHORT['cases'])|frozenset(c['command'] for c in COHORT['controls'].values())
capture=base.capture
digest=base.digest

def context():
    return {**base.context(),'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

def evaluate(case_id,proposal=None,required_context=None):
    result=base.evaluate(case_id,proposal)
    result['Dependencies']=context()
    if required_context is not None and required_context!=context():
        result['Conclusion'].update(status='UNKNOWN',reason='CONTEXT_CHANGED',repair_authorized=False)
    return result

def run_cohort():
    rows=[evaluate(c['id']) for c in COHORT['cases']]
    return {'calibration':COHORT['calibration'],'records':rows,
            'counts':{s:sum(r['Conclusion']['status']==s for r in rows)for s in ['SUPPORTED','REJECTED','UNKNOWN']}}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(run_cohort(),indent=2)+'\n')
