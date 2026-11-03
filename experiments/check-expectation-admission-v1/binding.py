"""Restricted source-bound expectation admission; paired repair is a separate gate."""
import json
import hashlib
import os
import argparse
from pathlib import Path
import run as reference

ROOT = Path(__file__).resolve().parent
POLICY = json.loads((ROOT / 'binding.json').read_text())


def bind(proposal, source_sha256):
    result = {'status':'UNKNOWN', 'reason':'PROPOSAL_CHANGED', 'repair_authorized':False}
    frozen = next((p for p in POLICY['proposals'] if p['id'] == proposal.get('id')), None)
    if frozen is None or proposal != frozen:
        return result
    if source_sha256 != POLICY['subject']['sha256']:
        return {**result, 'reason':'SOURCE_CHANGED'}
    ref = reference.evaluate(proposal['reference_id'])
    result['reference'] = ref
    if ref['Conclusion']['status'] != 'SUPPORTED':
        return {**result, 'reason':'REFERENCE_NOT_SUPPORTED'}
    calls = ref['Verification']['execution']['calls']
    projection = POLICY['adopted_projection'].get(proposal['reference_id'])
    if projection == 'inline-prefix-unquoted-v1' and calls == [['-c']]:
        expected = [{'kind':'inline','value':'python3 -c'}]
    elif projection == 'no-interpreter-invocation-v1' and calls == []:
        expected = []
    else:
        return {**result, 'reason':'PROJECTION_NOT_QUALIFIED'}
    command = ref['Obligation']['command']
    constructors = ', '.join('.' + x['kind'] + ' ' + json.dumps(x['value']) for x in expected)
    expression = 'pyCallsOfLine ' + json.dumps(command) + ' == [' + constructors + ']'
    result.update(canonical_expression=expression, expected=expected,
                  expression_sha256=hashlib.sha256(expression.encode()).hexdigest(),
                  subject=POLICY['subject'], policy_sha256=reference.digest(POLICY))
    if proposal['expected'] != expected:
        return {**result, 'status':'REJECTED', 'reason':'EXPECTED_VALUE_MISMATCH'}
    if proposal['expression'] != expression:
        return {**result, 'reason':'EXPRESSION_BINDING_MISMATCH'}
    return {**result, 'status':'ADMITTED', 'reason':'EXACT_FINITE_REFERENCE_BINDING'}


def qualify(inspection):
    bindings = {p['id']:bind(p, POLICY['subject']['sha256']) for p in POLICY['proposals']}
    admitted = [i for i, b in bindings.items() if b['status'] == 'ADMITTED']
    result = {'status':'UNKNOWN', 'repair_targets':[],
              'excluded_probes':[i for i in bindings if i not in admitted],
              'bindings':bindings, 'scope':POLICY['scope'], 'hosted_repair_authorized':False}
    policy_hash=hashlib.sha256(json.dumps(POLICY,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if not (inspection.get('complete') is True and inspection.get('subject') == POLICY['subject']
            and inspection.get('policy_sha256') == policy_hash and inspection.get('source_guard_count') == 160
            and inspection.get('repository_gate_exits') == [0,0,0,0]):
        return result
    try:
        arms=[inspection[k]['rows'] for k in ['initial','original','repaired','withdrawn']]
        ids=sorted(bindings)
        if any(sorted(r['id'] for r in rows) != ids for rows in arms):
            return result
        if not (arms[0] == arms[1] == arms[3]):
            return result
        old={r['id']:r['execution'] for r in arms[0]}
        fixed={r['id']:r['execution'] for r in arms[2]}
        failures=[i for i in admitted if old[i] == 'CANDIDATE_ASSERTION_FAILURE']
        if failures and all(fixed[i] == 'GUARD_PASSED' for i in admitted):
            result.update(status='QUALIFIED_FINITE_CANDIDATE',repair_targets=failures)
    except (KeyError,TypeError):
        pass
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    args=parser.parse_args()
    inspection=json.loads((args.root/'inspection.json').read_text())
    expected={'verifier_sha':os.environ['GITHUB_SHA'],'run_id':int(os.environ['GITHUB_RUN_ID']),
              'attempt':int(os.environ['GITHUB_RUN_ATTEMPT'])}
    if inspection.get('context') != expected:
        raise ValueError('INSPECTION_CONTEXT_MISMATCH')
    result=qualify(inspection)
    result['context']=expected
    (args.root/'binding-assessment.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'repair_targets':result['repair_targets'],
                      'excluded_probes':result['excluded_probes']}))
