"""Equally informed conventional reviewer: no MathGraph model code imported."""

import hashlib
import math
import argparse
import json
from pathlib import Path


SOURCE = 'data/tutorial_wp/ex-2-gcd.c'
TARGET = 'RQ3_result/Full_Fixed/ex-2-gcd.rs'
SOURCE_SHA256 = 'acd6ca718d61d14d709599d7961436ec136c13a94261d40f38911a190bc20d2d'
TARGET_SHA256 = '2536507f61a2fe83a1356c969093be18cd7aee4511c5155cf70753daa4506cab'


def compare(source_root: Path) -> dict:
    source_root = Path(source_root)
    try:
        c_data = (source_root / SOURCE).read_bytes()
        rs_data = (source_root / TARGET).read_bytes()
    except FileNotFoundError:
        return {'verdict': 'UNKNOWN_MISSING_SOURCE'}
    if (hashlib.sha256(c_data).hexdigest() != SOURCE_SHA256 or
            hashlib.sha256(rs_data).hexdigest() != TARGET_SHA256):
        return {'verdict': 'WITHDRAWN_SOURCE_CHANGED'}
    c = c_data.decode()
    rs = rs_data.decode()
    if not all(part in c for part in ('inductive is_gcd(', 'case gcd_zero:', 'case gcd_succ:')):
        return {'verdict': 'UNKNOWN_SOURCE_SEMANTICS'}
    if not all(part in rs for part in ('uninterp spec fn is_gcd(', '#[verifier::external_body]', 'broadcast proof fn is_gcd_inductive')):
        return {'verdict': 'UNKNOWN_TARGET_SEMANTICS'}
    # Reference algorithm, independent of finite closure implementation.
    a, b, d = (2, 0, 1)
    original_gcd_semantics = math.gcd(a, b) == d
    uninterpreted_total_predicate_allows_query = True
    return {
        'verdict': 'BASELINE_TIE' if not original_gcd_semantics and uninterpreted_total_predicate_allows_query else 'UNKNOWN',
        'query': [a, b, d],
        'source_least_query': original_gcd_semantics,
        'target_compatible_query': uninterpreted_total_predicate_allows_query,
        'method': 'source-aware contract reading plus independent Python math.gcd reference',
        'cost_comparison_measured': False,
    }


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('source_root', type=Path)
    cli.add_argument('--output', type=Path)
    args = cli.parse_args()
    result = compare(args.source_root)
    content = json.dumps(result, indent=2, sort_keys=True) + '\n'
    print(content)
    if args.output:
        args.output.write_text(content)
    if result['verdict'] != 'BASELINE_TIE':
        raise SystemExit(1)
