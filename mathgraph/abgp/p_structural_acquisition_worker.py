"""Source-only acquisition image for structural P. Never copied into future invocation."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime import canonical, digest, serve, validate_request


CAPABILITIES = (
    'CONST0_DIFFERENCE',
    'CONST1_DIFFERENCE',
    'LASTXX_DIFFERENCE',
    'ANYXXX_DIFFERENCE',
    'ALLXXX_DIFFERENCE',
    'MAJORY_DIFFERENCE',
    'PARITY_DIFFERENCE',
    'EVENXX_DIFFERENCE',
)
RETAINED_CAPABILITIES = ('PARITY_DIFFERENCE', 'EVENXX_DIFFERENCE', 'WRONGX_DIFFERENCE', 'VERBAL_FIRST_LAST')
SCHEMA = 'abgp.retained-structural-parity.v1'
SCOPE = 'future-symbol-sequence-v1/even-length'


def _validate_examples(raw):
    if not isinstance(raw, list) or len(raw) != 16:
        raise ValueError('structural P acquisition requires the complete 16-row length-4 source carrier')
    result = []
    for row in raw:
        if not isinstance(row, dict) or set(row) != {'sequence', 'label'}:
            raise ValueError('invalid source example schema')
        seq = row['sequence']
        label = row['label']
        if not isinstance(seq, list) or len(seq) != 4 or any(not isinstance(x, str) for x in seq):
            raise ValueError('source sequence must have four string symbols')
        if len(set(seq)) > 2 or label not in (0, 1):
            raise ValueError('source example outside binary structural carrier')
        result.append((tuple(seq), int(label)))
    if len({seq for seq, _ in result}) != 16:
        raise ValueError('source carrier must contain sixteen distinct sequences')
    return result


def _difference_count(seq):
    first = seq[0]
    return sum(value != first for value in seq)


def _apply(name, seq):
    d = _difference_count(seq)
    if name == 'CONST0_DIFFERENCE':
        return 0
    if name == 'CONST1_DIFFERENCE':
        return 1
    if name == 'LASTXX_DIFFERENCE':
        return int(seq[-1] != seq[0])
    if name == 'ANYXXX_DIFFERENCE':
        return int(d > 0)
    if name == 'ALLXXX_DIFFERENCE':
        return int(d == len(seq) - 1)
    if name == 'MAJORY_DIFFERENCE':
        return int(d >= len(seq) // 2)
    if name == 'PARITY_DIFFERENCE':
        return d & 1
    if name == 'EVENXX_DIFFERENCE':
        return 1 - (d & 1)
    if name == 'WRONGX_DIFFERENCE':
        return int(d > 0)
    if name == 'VERBAL_FIRST_LAST':
        return int(seq[-1] != seq[0])
    raise ValueError('unknown structural candidate')


def _retained(capability, lineage):
    if capability not in RETAINED_CAPABILITIES:
        raise ValueError('capability not serializable')
    body = {'schema': SCHEMA, 'capability': capability, 'scope': SCOPE, 'lineage': lineage}
    return dict(body, checksum=digest(body))


def acquire_structural(request):
    validate_request(request, 'acquire_structural', ('examples',))
    examples = _validate_examples(request['examples'])
    survivors = []
    checks = 0
    for candidate in CAPABILITIES:
        ok = True
        for seq, label in examples:
            checks += 1
            if _apply(candidate, seq) != label:
                ok = False
                break
        if ok:
            survivors.append(candidate)
    source_digest = digest(request['examples'])
    retained = _retained('PARITY_DIFFERENCE', source_digest) if survivors == ['PARITY_DIFFERENCE'] else None
    return {
        'retained': retained,
        'sham': _retained('EVENXX_DIFFERENCE', source_digest),
        'wrong_class': _retained('WRONGX_DIFFERENCE', source_digest),
        'verbal_rule': _retained('VERBAL_FIRST_LAST', source_digest),
        'candidate_count': len(CAPABILITIES),
        'survivor_count': len(survivors),
        'survivors': survivors,
        'candidate_checks': checks,
        'source_example_reads': checks,
        'source_history_digest': source_digest,
    }


def old_posterior_from_source(request):
    validate_request(request, 'old_posterior_from_source', ('examples',))
    examples = _validate_examples(request['examples'])
    counts = {'equal': [0, 0], 'different': [0, 0]}
    for seq, label in examples:
        state = 'equal' if seq[0] == seq[-1] else 'different'
        counts[state][label] += 1
    return {
        'old_state': 'FIRST_LAST_EQUALITY',
        'posterior_counts': counts,
        'source_history_digest': digest(request['examples']),
        'source_example_reads': len(examples),
        'candidate_checks': 0,
    }


if __name__ == '__main__':
    serve({'acquire_structural': acquire_structural,
           'old_posterior_from_source': old_posterior_from_source}, __file__)
