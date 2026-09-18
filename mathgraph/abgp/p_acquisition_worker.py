"""Acquisition image. Never copied into the invocation directory."""
import os
import sys
# Only this newly created directory of fixed runtime files is admitted.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime import (CONTEXTS, canonical, digest, make_retained, validated_retained,
                     validate_request, serve)
import itertools
from fractions import Fraction
POLICIES = tuple(itertools.permutations(CONTEXTS))

def examples_from(request):
    raw = request['examples']
    if not isinstance(raw, list) or len(raw) > 64:
        raise ValueError('examples must be a bounded list')
    for row in raw:
        if not isinstance(row, list) or len(row) != 2 or any(type(x) is not int or x not in CONTEXTS for x in row):
            raise ValueError('example outside finite language')
    return raw

def acquire(request):
    validate_request(request, 'acquire', ('examples',))
    examples = examples_from(request)
    checks, reads, matches = 0, 0, []
    for candidate in POLICIES:
        checks += 1
        consistent = True
        for context, label in examples:
            reads += 1
            if candidate[context] != label:
                consistent = False
                break
        if consistent:
            matches.append(candidate)
    if len(matches) != 1:
        return {'retained': None, 'candidate_checks': checks, 'source_example_reads': reads,
                'version_space_size': len(matches), 'outcome': 'UNKNOWN'}
    return {'retained': make_retained(matches[0], digest(examples)), 'candidate_checks': checks,
            'source_example_reads': reads, 'version_space_size': 1, 'outcome': 'ACQUIRED'}

def posterior(request):
    validate_request(request, 'posterior', ('examples',))
    examples = examples_from(request)
    # Same data and prior as acquisition. No labels are omitted to manufacture a
    # structural advantage. The utility is ALL FOUR probes correct.
    compatible = [p for p in POLICIES if all(p[c] == y for c, y in examples)]
    if not compatible:
        raise ValueError('empty posterior')
    actions = min(compatible)
    return {'posterior_size': len(compatible), 'joint_actions': list(actions),
            'joint_success_probability': str(Fraction(1, len(compatible))),
            'posterior_weights': [int(p in compatible) for p in POLICIES],
            'information_digest': digest(examples)}

if __name__ == '__main__':
    serve({'acquire': acquire, 'posterior': posterior}, __file__)
