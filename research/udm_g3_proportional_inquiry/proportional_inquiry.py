"""A deliberately small selector for verified Go-observer receipts.

The only protected decision here is: does a repeatable source-version
separating witness exist? This module does not inspect generated test code,
create permission, equate two distinct observations, or prove G2/G3.
"""
from __future__ import annotations

import json
import re
from typing import Any

WARRANT = 'WARRANTED_BOUNDED_GENERATED_NATIVE_WITNESS'
SCHEMA = 'mathgraph.g2.go-native-qualification.v1'
_SHA = re.compile(r'[0-9a-f]{40}\Z')
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')


def _well_qualified(record: dict[str, Any]) -> bool:
    if record.get('status') != WARRANT:
        return False
    if not _DIGEST.fullmatch(str(record.get('proposal_sha256', ''))):
        return False
    required = {
        'base': ('FAIL_NATIVE_ASSERTION', 1),
        'head': ('PASS_SOURCE_NATIVE', 1),
        'ablation': ('UNKNOWN_ZERO_NAMED_TESTS', 0),
        'restoration': ('FAIL_NATIVE_ASSERTION', 1),
    }
    return all(
        isinstance(record.get(field), dict)
        and record[field].get('status') == expected
        and record[field].get('count') == count
        for field, (expected, count) in required.items()
    )


def select_proportionate_observation(receipt: dict[str, Any]) -> dict[str, str]:
    """Fail closed, choosing no more observation language than required.

    Source-native evidence is necessary for a bounded witness; insufficiency
    of a model-generated direct proposal is *not* proof old grammar exhausted.
    """
    answer = {
        'schema': 'mathgraph.udm.proportionate-inquiry.v1',
        'protected_goal': 'independently_replayable_source_version_separator',
        'status': 'UNKNOWN_INVALID_RECEIPT',
        'selected_observer': 'NONE',
        'new_grammar_necessary_for_goal': 'UNKNOWN',
        'fair_comparison': 'UNKNOWN',
        'strict_g2': 'UNKNOWN',
        'strict_g3': 'UNKNOWN',
        'effect_authority': 'NOT_GRANTED',
    }
    if not isinstance(receipt, dict) or receipt.get('schema') != SCHEMA:
        return answer
    if not all(_SHA.fullmatch(str(receipt.get(k, ''))) for k in ('base_sha', 'head_sha')):
        return answer
    results = receipt.get('results')
    if not isinstance(results, list) or len(results) != 2:
        return answer
    by_mode = {r.get('mode'): r for r in results if isinstance(r, dict)}
    if len(by_mode) != 2 or set(by_mode) != {'bridge', 'direct'}:
        return answer
    # A report that asserts warrant while lacking native controls is invalid,
    # not merely a weaker inconclusive result.
    if any(r.get('status') == WARRANT and not _well_qualified(r) for r in results):
        return answer
    direct = _well_qualified(by_mode['direct'])
    bridge = _well_qualified(by_mode['bridge'])
    if direct:
        answer.update({
            'status': 'WARRANTED_BOUNDED_DIRECT_SUFFICIENT_FOR_DECLARED_GOAL',
            'selected_observer': 'direct',
            'new_grammar_necessary_for_goal': 'NO',
            'fair_comparison': ('BOTH_WITNESSED_SAME_VERSION_BOUNDARY'
                                if bridge else 'DIRECT_ONLY_WITNESS'),
        })
    elif bridge:
        answer.update({
            'status': 'CANDIDATE_EXTENSION_WITH_NATIVE_WITNESS',
            'selected_observer': 'bridge',
            'new_grammar_necessary_for_goal': 'UNKNOWN',
            'fair_comparison': 'NO_QUALIFIED_EQUAL_INFORMATION_DIRECT_WITNESS',
        })
    else:
        answer['status'] = 'UNKNOWN_NO_VERIFIED_SOURCE_WITNESS'
    return answer


def token_counts(receipt: dict[str, Any]) -> dict[str, dict[str, int] | str]:
    """Only token counts, never invented dollar conversion or net economics."""
    if not isinstance(receipt, dict) or receipt.get('schema') != 'mathgraph.g2.go-observer-proposals.v1':
        return {'status': 'UNKNOWN_USAGE_RECEIPT'}
    calls = receipt.get('calls', [])
    if not isinstance(calls, list) or set(c.get('mode') for c in calls if isinstance(c, dict)) != {'direct', 'bridge'} or len(calls) != 2:
        return {'status': 'UNKNOWN_USAGE_RECEIPT'}
    out: dict[str, dict[str, int] | str] = {'status': 'OBSERVED_TOKEN_COUNTS_ONLY'}
    for c in calls:
        u = c.get('usage', {})
        inp, otp = u.get('input_tokens'), u.get('output_tokens')
        if not all(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 100_000 for n in (inp, otp)):
            return {'status': 'UNKNOWN_USAGE_RECEIPT'}
        out[c['mode']] = {'input_tokens': inp, 'output_tokens': otp}
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('native_receipt')
    ap.add_argument('--tokens')
    ns = ap.parse_args()
    r = json.load(open(ns.native_receipt))
    print(json.dumps({'selection': select_proportionate_observation(r),
                      'tokens': token_counts(json.load(open(ns.tokens))) if ns.tokens else {'status': 'UNKNOWN_USAGE_RECEIPT'}},
                     indent=2, sort_keys=True))