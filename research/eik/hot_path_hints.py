"""Exact branch-hint experiments across the common RV32IM paths.

Hints change no C condition or arithmetic. Fixed families are chosen from the
published workload and the complete source control flow, not individual inputs.
The compiled whole-program score is the only performance evidence.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

BASE = '8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37'
FAMILIES = ('exp', 'sigmoid', 'tanh', 'guards')
TRAIN_SEED = 1284956104
HELDOUT_SEED = 318674905


def body_span(source, fn):
    start = source.index('static inline uint32_t r_eik_' + fn + '_r(')
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', lambda m: ' ' * len(m[0]), source, flags=re.S)
    opening = clean.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (clean[end] == '{') - (clean[end] == '}')
        end += 1
    return start, end


def change(source, flags):
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong published baseline')
    records = []
    result = source
    for fn in ('exp', 'tanh', 'sigmoid'):
        start, end = body_span(result, fn)
        body = result[start:end]
        targets = []
        if fn in flags:
            targets = {
                'exp': [('(int32_t)r_w < 0', 1), ('r_w <= 0xBF801000u', 0),
                        ('r_w <= 0xC07FF000u', 1), ('r_w <= 0xC0FFF000u', 1)],
                'sigmoid': [('(int32_t)r_t < 0', 0), ('r_t < 0x74D13000u', 0),
                            ('r_t < 0x7CC01000u', 0)],
                'tanh': [('(int32_t)r_t < 0', 0), ('r_t < 0x7C016000u', 0)],
            }[fn]
        for cond, hint in targets:
            old = 'if (' + cond + ')'
            if body.count(old) != 1:
                raise ValueError((fn, cond, body.count(old)))
            body = body.replace(old, 'if (__builtin_expect(!!(' + cond + '),' + str(hint) + '))')
            records.append({'function': fn, 'condition': cond, 'hint': hint})
        if 'guards' in flags:
            def guard(m):
                cond = m[2]
                if '&' not in cond or '__builtin_expect' in cond:
                    return m[0]
                records.append({'function': fn, 'condition': cond, 'hint': 1})
                return m[1] + 'if (__builtin_expect(!!(' + cond + '),1))\n' + m[3] + 'return'
            body = re.sub(r'(?m)^(\s*)if \(([^\n]+)\)\n(\s*)return', guard, body)
        result = result[:start] + body + result[end:]
    return result, {'baseline_sha256': BASE, 'families': list(flags),
                    'train_seed': TRAIN_SEED, 'heldout_seed_declared_before_measurement': HELDOUT_SEED,
                    'hints': records, 'source_sha256': hashlib.sha256(result.encode()).hexdigest()}


if __name__ == '__main__':
    original, output = map(Path, sys.argv[1:3])
    flags = tuple(sys.argv[3].split('+')) if sys.argv[3] != 'control' else ()
    if not set(flags) <= set(FAMILIES):
        raise ValueError(flags)
    transformed, manifest = change(original.read_text(), flags)
    output.write_text(transformed)
    print(json.dumps(manifest, indent=2))
