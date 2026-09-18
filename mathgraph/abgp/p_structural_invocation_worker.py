"""Future-only structural invocation image: no source parser and no acquisition search."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime import digest, serve, validate_request


SCHEMA = 'abgp.retained-structural-parity.v1'
SCOPE = 'future-symbol-sequence-v1/even-length'
CAPABILITIES = ('PARITY_DIFFERENCE', 'EVENXX_DIFFERENCE', 'WRONGX_DIFFERENCE', 'VERBAL_FIRST_LAST')


def _retained(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {'schema', 'capability', 'scope', 'lineage', 'checksum'}:
        raise ValueError('retained structural object has forbidden or missing fields')
    if raw['schema'] != SCHEMA or raw['scope'] != SCOPE or raw['capability'] not in CAPABILITIES:
        raise ValueError('retained structural object outside frozen interpreter')
    body = {key: raw[key] for key in ('schema', 'capability', 'scope', 'lineage')}
    if raw['checksum'] != digest(body):
        raise ValueError('retained structural checksum mismatch')
    return raw


def _task(raw):
    if not isinstance(raw, dict) or set(raw) != {'schema', 'instance_id', 'symbols'}:
        raise ValueError('future task schema mismatch')
    if raw['schema'] != 'future-symbol-sequence-v1' or not isinstance(raw['instance_id'], str):
        raise ValueError('future task outside retained scope')
    symbols = raw['symbols']
    if not isinstance(symbols, list) or len(symbols) < 6 or len(symbols) % 2 or any(not isinstance(x, str) for x in symbols):
        raise ValueError('future structural task requires an even string sequence of length at least six')
    if not 1 <= len(set(symbols)) <= 2:
        raise ValueError('future task outside binary structural carrier')
    return tuple(symbols)


def _action(capability, symbols):
    d = sum(value != symbols[0] for value in symbols)
    if capability is None:
        return 0
    if capability == 'PARITY_DIFFERENCE':
        return d & 1
    if capability == 'EVENXX_DIFFERENCE':
        return 1 - (d & 1)
    if capability == 'WRONGX_DIFFERENCE':
        return int(d > 0)
    if capability == 'VERBAL_FIRST_LAST':
        return int(symbols[-1] != symbols[0])
    raise ValueError('unsupported capability')


def invoke_structural(request):
    validate_request(request, 'invoke_structural', ('retained', 'task'))
    retained = _retained(request['retained'])
    symbols = _task(request['task'])
    return {
        'action': _action(None if retained is None else retained['capability'], symbols),
        'retained_checksum': None if retained is None else retained['checksum'],
        'applicability_used_target_label': False,
        'trace': {'candidate_checks': 0, 'source_example_reads': 0, 'verifier_calls': 0},
        'input_fields': sorted(request),
    }


def delete_structural(request):
    validate_request(request, 'delete_structural', ('retained', 'lineage'))
    retained = _retained(request['retained'])
    removed = retained is not None and retained['lineage'] == request['lineage']
    return {'retained': None if removed else retained, 'removed': removed,
            'before_checksum': None if retained is None else retained['checksum']}


if __name__ == '__main__':
    serve({'invoke_structural': invoke_structural, 'delete_structural': delete_structural}, __file__)
