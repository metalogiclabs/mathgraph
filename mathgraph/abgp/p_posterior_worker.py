"""Ordinary Bayesian invocation: posterior weights, not a capability object.

The policy language is fixed before acquisition. All-four success is the utility.
This worker has neither source examples nor an acquisition handler.
"""
import os
import sys
import itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime import validate_request, serve

POLICIES = tuple(itertools.permutations(range(4)))


def posterior_invoke(request):
    validate_request(request, 'posterior_invoke', ('posterior_weights', 'contexts'))
    weights = request['posterior_weights']
    if not isinstance(weights, list) or len(weights) != 24 or any(type(w) is not int or w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError('need a nonempty exact posterior over the fixed 24-policy prior')
    if request['contexts'] != [0, 1, 2, 3]:
        raise ValueError('this utility is defined for the frozen all-four probe vector')
    # Joint MAP is Bayes optimal for the all-four 0/1 utility. No target label
    # enters, and no new observable or new policy is constructed.
    index = max(range(24), key=lambda i: (weights[i], -i))
    return {'actions': list(POLICIES[index]), 'posterior_policy_count': 24,
            'posterior_weight_reads': 24, 'input_fields': sorted(request)}


if __name__ == '__main__':
    serve({'posterior_invoke': posterior_invoke}, __file__)
