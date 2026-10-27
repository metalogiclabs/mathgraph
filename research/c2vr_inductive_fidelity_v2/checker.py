"""Source-fidelity checker for a *single*, SHA-pinned public C2VR case.

This never claims generic ACSL parsing or Verus proof soundness; the semantic
finding and the separately authenticated native run have different scopes.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from model import audit_models


SOURCE_REVISION = 'ZoneOut12/C2VerifiableRust@6c8b35b5dd8e94473b713b7edcf4bf4142f214e3'
SOURCE_FILE = 'data/tutorial_wp/ex-2-gcd.c'
TARGET_FILE = 'RQ3_result/Full_Fixed/ex-2-gcd.rs'
SOURCE_SHA256 = 'acd6ca718d61d14d709599d7961436ec136c13a94261d40f38911a190bc20d2d'
TARGET_SHA256 = '2536507f61a2fe83a1356c969093be18cd7aee4511c5155cf70753daa4506cab'
VERUS_RELEASE = '0.2025.06.14.9b557d7'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_verdict(evidence: Path, verus_binary: Path | None = None) -> str:
    filenames = ('verus.exit', 'verus.log', 'native-receipt.json')
    if not all((evidence / f).is_file() for f in filenames):
        return 'WITHDRAWN_NATIVE_RECEIPT'
    try:
        receipt = json.loads((evidence / 'native-receipt.json').read_text())
        log = (evidence / 'verus.log').read_text()
        exit_code = int((evidence / 'verus.exit').read_text().strip())
        if (receipt['exit'] != exit_code or
                receipt['source_sha256'] != SOURCE_SHA256 or
                receipt['target_sha256'] != TARGET_SHA256 or
                receipt['release'] != VERUS_RELEASE or
                receipt['log_sha256'] != sha256(evidence / 'verus.log') or
                not re.fullmatch(r'[a-f0-9]{64}', receipt['tool_sha256'])):
            return 'REJECTED_EVIDENCE'
        if not verus_binary or not verus_binary.is_file():
            return 'UNKNOWN_TOOL_BYTES'
        if sha256(verus_binary) != receipt['tool_sha256']:
            return 'REJECTED_EVIDENCE'
        if exit_code != 0:
            return 'UNKNOWN_NATIVE_FAILURE'
        if not re.search(r'verification results::\s*\d+ verified,\s*0 errors', log):
            return 'UNKNOWN_NO_VERUS_SUCCESS_MARKER'
    except (KeyError, ValueError, OSError, UnicodeError, json.JSONDecodeError):
        return 'REJECTED_EVIDENCE'
    return 'VERUS_ACCEPTED_CONDITIONALLY_ON_EXTERNAL_BODY'


def check(source_root: Path, evidence_root: Path | None = None, verus_binary: Path | None = None) -> dict:
    source_root = Path(source_root)
    source = source_root / SOURCE_FILE
    target = source_root / TARGET_FILE
    if not source.is_file() or not target.is_file():
        return {'semantic_verdict': 'WITHDRAWN_MISSING_SOURCE'}
    if sha256(source) != SOURCE_SHA256:
        return {'semantic_verdict': 'WITHDRAWN_CHANGED_C'}
    if sha256(target) != TARGET_SHA256:
        return {'semantic_verdict': 'WITHDRAWN_CHANGED_VERUS'}
    c = source.read_text()
    rs = target.read_text()
    if not all(part in c for part in ('inductive is_gcd(', 'case gcd_zero:', 'case gcd_succ:', 'ensures is_gcd(a, b, \\result)')):
        return {'semantic_verdict': 'REJECTED_UNEXPECTED_ACSL_CONTRACT'}
    if not all(part in rs for part in ('pub uninterp spec fn is_gcd(', '#[verifier::external_body]',
                                       'pub broadcast proof fn is_gcd_inductive()', 'ensures', 'is_gcd(a as int, b as int, result as int)')):
        return {'semantic_verdict': 'REJECTED_UNEXPECTED_VERUS_CONTRACT'}
    finite = audit_models(3)
    if verus_binary is None:
        binary_path = os.environ.get('C2VR_VERUS_BIN')
        verus_binary = Path(binary_path) if binary_path else None
    return {
        'source': SOURCE_REVISION,
        'source_file_sha256': SOURCE_SHA256,
        'target_file_sha256': TARGET_SHA256,
        'semantic_verdict': finite['verdict'],
        'trust_boundary': 'VERUS_EXTERNAL_BODY_ASSUMPTION',
        'native_verdict': native_verdict(Path(evidence_root), verus_binary) if evidence_root is not None else 'UNKNOWN_NOT_EXECUTED',
        'finite_model': finite,
        'limitations': [
            'Finite nonnegative domain and explicit modulo-zero totalization; not a universal ACSL equivalence theorem.',
            'The original C source is unchanged; this is a published migration contract-fidelity comparison, not a runtime defect.',
            'The Verus output explicitly declares a trusted external_body; conditional verification is not an unqualified proof of the C source contract.',
            'A fully informed conventional reviewer finds the same semantic gap; comparative advantage not shown.',
        ],
    }


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('source_root', type=Path)
    cli.add_argument('--evidence', type=Path)
    cli.add_argument('--output', type=Path)
    args = cli.parse_args()
    result = check(args.source_root, args.evidence)
    output = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(output)
    print(output)
    if result.get('semantic_verdict') != 'FINITE_COUNTERMODEL' or (
        args.evidence is not None and result.get('native_verdict') != 'VERUS_ACCEPTED_CONDITIONALLY_ON_EXTERNAL_BODY'
    ):
        raise SystemExit(1)
