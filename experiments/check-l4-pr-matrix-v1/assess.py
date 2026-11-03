"""Mechanical evidence admission, independent of calibration labels."""
import re

def qualified(arm):
    return (arm.get('complete') is True and type(arm.get('build_exit')) is int and arm['build_exit'] == 0
            and type(arm.get('gate_exit')) is int and arm['gate_exit'] in [0,1]
            and arm.get('contract') in ['PASS','FAIL']
            and arm.get('behavior') in ['PASS','FAIL']
            and arm.get('generation') in ['PASS','FAIL','NOT_REQUIRED']
            and type(arm.get('consumer_reached')) is bool
            and isinstance(arm.get('unapproved_axioms'),list)
            and all(isinstance(x,str) and x for x in arm['unapproved_axioms'])
            and isinstance(arm.get('hashes'),dict)
            and 'Subject.lean' in arm['hashes']
            and all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in arm['hashes'].values()))
def issues(arm):
    out = []
    for key, label in [('contract', 'REQUIRED_TYPE_FAILURE'), ('behavior', 'FINITE_BEHAVIOR_FAILURE'), ('generation', 'GENERATED_SOURCE_DRIFT')]:
        if arm.get(key) == 'FAIL': out.append(label)
    if arm.get('consumer_reached') is False: out.append('REQUIRED_CONSUMER_NOT_BUILT')
    if arm.get('unapproved_axioms'): out.append('ASSUMPTION_POLICY_FAILURE')
    if arm.get('gate_exit') not in [None, 0]: out.append('REPOSITORY_GATE_FAILURE')
    return out

def compare(base, head):
    if head.get('contract_changed'): return 'OWNER_REVIEW_REQUIRED'
    if not qualified(base) or not qualified(head): return 'UNKNOWN'
    b, h = issues(base), issues(head)
    if h:
        if not b: return 'INTRODUCED_OR_CHANGED_FAILURE'
        identical = base['hashes'] == head['hashes'] and base['unapproved_axioms'] == head['unapproved_axioms']
        return 'INHERITED_FAILURE' if b == h and identical else 'FAILURE_ON_BOTH_REVISIONS'
    return 'RESOLVED_FAILURE' if b else 'BOUNDED_PASS'
