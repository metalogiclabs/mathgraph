"""Mechanical evidence admission, independent of calibration labels."""
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
    if not base.get('complete') or not head.get('complete'): return 'UNKNOWN'
    b, h = issues(base), issues(head)
    if h: return 'INHERITED_FAILURE' if b == h else 'INTRODUCED_OR_CHANGED_FAILURE'
    return 'RESOLVED_FAILURE' if b else 'BOUNDED_PASS'
