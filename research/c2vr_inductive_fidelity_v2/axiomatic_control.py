"""Narrow genuine positive control: source-authored axioms remain explicit trust.

The status means ONLY the declaration/assumption *kind* aligns. It does not
verify translation of every formula or the Rust executable's refinement.
"""

import argparse
import json
from pathlib import Path

from checker import SOURCE_REVISION, native_verdict, sha256


SOURCE = 'data/tutorial_wp/max_subarray-1.c'
TARGET = 'RQ3_result/Full_Fixed/max_subarray-1.rs'
SOURCE_SHA256 = 'ff66b503c6074877c5a764e521d7fbfa15901abfe6e1a70d71d7176a9e4a7e63'
TARGET_SHA256 = '0f62e42e58ba8a0c1c95c4825cad3859123436fd0f99466a5d1eabb45eeec468'


def check_axiomatic(source_root: Path, evidence: Path | None = None, tool: Path | None = None) -> dict:
    source_root = Path(source_root)
    cpath, rpath = source_root / SOURCE, source_root / TARGET
    if not cpath.is_file() or not rpath.is_file():
        return {'trust_kind_verdict': 'WITHDRAWN_MISSING_AXIOMATIC_CASE'}
    if sha256(cpath) != SOURCE_SHA256:
        return {'trust_kind_verdict': 'WITHDRAWN_CHANGED_AXIOMATIC_C'}
    if sha256(rpath) != TARGET_SHA256:
        return {'trust_kind_verdict': 'WITHDRAWN_CHANGED_AXIOMATIC_VERUS'}
    c, rs = cpath.read_text(), rpath.read_text()
    if not all(k in c for k in ('axiomatic Sum_array{', 'logic integer sum(', 'axiom empty:', 'axiom range:')):
        return {'trust_kind_verdict': 'REJECTED_UNEXPECTED_ACSL_AXIOMS'}
    if not all(k in rs for k in ('pub uninterp spec fn sum(', 'pub broadcast proof fn empty()',
                                'pub broadcast proof fn range()')) or rs.count('#[verifier::external_body]') != 2:
        return {'trust_kind_verdict': 'REJECTED_UNEXPECTED_VERUS_AXIOMS'}
    return {
        'source': SOURCE_REVISION,
        'source_sha256': SOURCE_SHA256,
        'target_sha256': TARGET_SHA256,
        'source_contract_kind': 'AXIOMATIC',
        'target_contract_kind': 'UNINTERPRETED_WITH_EXPLICIT_TRUSTED_AXIOMS',
        'matched_axiom_names': ['empty', 'range'],
        'trust_kind_verdict': 'MATCHED_AXIOMATIC_TRUST_KIND_BOUNDED',
        'native_verdict': native_verdict(evidence, tool, SOURCE_SHA256, TARGET_SHA256) if evidence is not None else 'UNKNOWN_NOT_EXECUTED',
        'full_specification_equivalence_warranted': False,
        'limitations': [
            'Positive control is for original and target trust/declaration kinds only.',
            'It is not a source-to-target formula translation proof or executable semantic equivalence claim.',
            'External_body remains an explicit assumption in Verus; the source was axiomatic already.',
        ],
    }


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('source_root', type=Path)
    cli.add_argument('--evidence', type=Path)
    cli.add_argument('--tool', type=Path)
    cli.add_argument('--output', type=Path)
    args = cli.parse_args()
    report = check_axiomatic(args.source_root, args.evidence, args.tool)
    doc = json.dumps(report, sort_keys=True, indent=2) + '\n'
    print(doc)
    if args.output:
        args.output.write_text(doc)
    if report.get('trust_kind_verdict') != 'MATCHED_AXIOMATIC_TRUST_KIND_BOUNDED' or (
        args.evidence is not None and report.get('native_verdict') != 'VERUS_ACCEPTED_CONDITIONALLY_ON_EXTERNAL_BODY'
    ):
        raise SystemExit(1)
