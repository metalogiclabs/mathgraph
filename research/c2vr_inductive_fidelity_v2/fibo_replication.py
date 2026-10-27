"""Second authentic inductive case: finite non-uniqueness even with a lemma.

This is a *bounded model comparison*, not a whole-integer equivalence proof.
The upstream source already *admits* monotonicity; that trusted premise is
included in the finite target-compatible model, not silently discarded.
"""

import argparse
import json
from pathlib import Path

from checker import SOURCE_REVISION, native_verdict, sha256


SOURCE = 'data/tutorial_wp/ex-N-fibo.c'
TARGET = 'RQ3_result/Full_Fixed/ex-N-fibo.rs'
SOURCE_SHA256 = '258c311b2e665fab0ffa67c78981ccaa5689b3cad613a560298f6ce7fb5c50ec'
TARGET_SHA256 = 'e207d24b404f8964bc42bf8a67245ac78dd94c6ace9cd64e04e63a47b3456849'


def _least_fibo(bound: int) -> set[tuple[int, int]]:
    n0, n1 = 1, 1
    out = set()
    for n in range(bound + 1):
        out.add((n, n0))
        n0, n1 = n1, n0 + n1
    return out


def _satisfies_bounded_axioms(relation: set[tuple[int, int]], bound: int) -> bool:
    # These checks interpret introduction and the admitted monotonic lemma
    # over n in [-1..bound]; no inference about outside-domain semantics.
    if (0, 1) not in relation or (1, 1) not in relation:
        return False
    for n in range(2, bound + 1):
        prior2 = [r for i, r in relation if i == n - 2]
        prior1 = [r for i, r in relation if i == n - 1]
        if any((n, r1 + r2) not in relation for r1 in prior2 for r2 in prior1):
            return False
    return all(r1 <= r2 for i, r1 in relation for j, r2 in relation if i <= j)


def audit_fibo(bound: int = 5) -> dict:
    if not 2 <= bound <= 20:
        raise ValueError('bound must lie in [2, 20]')
    least = _least_fibo(bound)
    alternative = least | {(-1, 0)}
    witness = (-1, 0)
    if (witness in least or witness not in alternative or
            not _satisfies_bounded_axioms(least, bound) or
            not _satisfies_bounded_axioms(alternative, bound)):
        raise AssertionError('finite countermodel obligations failed')
    return {
        'verdict': 'FINITE_COUNTERMODEL',
        'claim_refuted': 'INTRODUCTION_PLUS_ADMITTED_MONOTONICITY_IDENTIFY_LEAST_FIBO_RELATION_BOUNDED',
        'domain_n': [-1, bound],
        'source_least_relation_size': len(least),
        'target_compatible_relation_size': len(alternative),
        'separating_query': list(witness),
        'source_query': witness in least,
        'target_compatible_query': witness in alternative,
        'both_satisfy_introduction_and_monotonic_axioms_bounded': True,
        'source_admits_monotonicity': True,
        'universal_equivalence_proof': False,
    }


def check_fibo(source_root: Path, evidence: Path | None = None, tool: Path | None = None) -> dict:
    root = Path(source_root)
    source, target = root / SOURCE, root / TARGET
    if not source.is_file() or not target.is_file():
        return {'semantic_verdict': 'WITHDRAWN_MISSING_FIBO_SOURCE'}
    if sha256(source) != SOURCE_SHA256:
        return {'semantic_verdict': 'WITHDRAWN_CHANGED_FIBO_C'}
    if sha256(target) != TARGET_SHA256:
        return {'semantic_verdict': 'WITHDRAWN_CHANGED_FIBO_VERUS'}
    c, rs = source.read_text(), target.read_text()
    if not all(k in c for k in ('inductive is_fibo(', 'case fib_0:', 'case fib_1:',
                                'case fib_N:', 'admit lemma fib_monotonic:')):
        return {'semantic_verdict': 'REJECTED_UNEXPECTED_FIBO_ACSL'}
    if not all(k in rs for k in ('pub uninterp spec fn is_fibo(',
                                 'pub broadcast proof fn is_fibo_inductive()',
                                 'pub broadcast proof fn fib_monotonic()')) or rs.count('#[verifier::external_body]') != 2:
        return {'semantic_verdict': 'REJECTED_UNEXPECTED_FIBO_VERUS'}
    return {
        'source': SOURCE_REVISION,
        'source_sha256': SOURCE_SHA256,
        'target_sha256': TARGET_SHA256,
        'semantic_verdict': 'FINITE_COUNTERMODEL',
        'finite_model': audit_fibo(),
        'source_admitted_monotonic_lemma_retained_as_assumption': True,
        'native_verdict': native_verdict(evidence, tool, SOURCE_SHA256, TARGET_SHA256) if evidence is not None else 'UNKNOWN_NOT_EXECUTED',
        'limitations': [
            'Finite index domain; the model does not establish universal ACSL/Verus inequivalence.',
            'Source fib_monotonic is explicitly admitted; target transfer is explicitly trusted.',
            'Witness concerns predicate overacceptance, not a demonstrated runtime Fibonacci bug.',
            'An equally informed conventional reviewer also identifies the mismatch.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source_root', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--tool', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = check_fibo(args.source_root, args.evidence, args.tool)
    output = json.dumps(report, sort_keys=True, indent=2) + '\n'
    print(output)
    if args.output:
        args.output.write_text(output)
    if report.get('semantic_verdict') != 'FINITE_COUNTERMODEL' or (
        args.evidence is not None and report.get('native_verdict') != 'VERUS_ACCEPTED_CONDITIONALLY_ON_EXTERNAL_BODY'
    ):
        raise SystemExit(1)
