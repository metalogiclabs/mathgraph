"""Frozen-old-representation posterior invocation for structural P."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime import serve, validate_request


def _task(raw):
    if not isinstance(raw, dict) or set(raw) != {'schema', 'instance_id', 'symbols'}:
        raise ValueError('future task schema mismatch')
    symbols = raw['symbols']
    if raw['schema'] != 'future-symbol-sequence-v1' or not isinstance(symbols, list) or len(symbols) < 6 or len(symbols) % 2:
        raise ValueError('future task outside old target carrier')
    if any(not isinstance(x, str) for x in symbols):
        raise ValueError('future symbols must be strings')
    return tuple(symbols)


def invoke_old_posterior(request):
    validate_request(request, 'invoke_old_posterior', ('posterior_counts', 'task'))
    counts = request['posterior_counts']
    if not isinstance(counts, dict) or set(counts) != {'equal', 'different'}:
        raise ValueError('old posterior states mismatch')
    for values in counts.values():
        if not isinstance(values, list) or len(values) != 2 or any(type(v) is not int or v < 0 for v in values):
            raise ValueError('old posterior counts invalid')
    symbols = _task(request['task'])
    state = 'equal' if symbols[0] == symbols[-1] else 'different'
    zeros, ones = counts[state]
    action = int(ones > zeros)
    return {
        'action': action,
        'old_state_observed': state,
        'trace': {'candidate_checks': 0, 'source_example_reads': 0, 'verifier_calls': 0},
        'input_fields': sorted(request),
    }


if __name__ == '__main__':
    serve({'invoke_old_posterior': invoke_old_posterior}, __file__)
