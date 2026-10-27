"""Run authentic published Verus file and retain every verification byte."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from checker import SOURCE_FILE, SOURCE_SHA256, TARGET_FILE, TARGET_SHA256, VERUS_RELEASE, sha256


CASES = {
    'gcd': (SOURCE_FILE, SOURCE_SHA256, TARGET_FILE, TARGET_SHA256),
    'max_subarray': (
        'data/tutorial_wp/max_subarray-1.c',
        'ff66b503c6074877c5a764e521d7fbfa15901abfe6e1a70d71d7176a9e4a7e63',
        'RQ3_result/Full_Fixed/max_subarray-1.rs',
        '0f62e42e58ba8a0c1c95c4825cad3859123436fd0f99466a5d1eabb45eeec468',
    ),
}


def run_verus(source_root: Path, verus_binary: Path, evidence_root: Path,
              case: str = 'gcd') -> dict:
    source_root = Path(source_root).resolve()
    verus_binary = Path(verus_binary).resolve()
    evidence_root = Path(evidence_root)
    source_file, source_sha, target_file, target_sha = CASES[case]
    source, target = source_root / source_file, source_root / target_file
    if sha256(source) != source_sha or sha256(target) != target_sha:
        raise ValueError('upstream source/target bytes differ from pinned release')
    if not verus_binary.is_file():
        raise FileNotFoundError(verus_binary)
    evidence_root.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([str(verus_binary), '--version'], capture_output=True, text=True, check=False)
    process = subprocess.run([str(verus_binary), str(target)], cwd=source_root,
                             capture_output=True, text=True, check=False, timeout=180)
    log = ('# stdout\n' + process.stdout + '\n# stderr\n' + process.stderr)
    (evidence_root / 'verus.log').write_text(log)
    (evidence_root / 'verus.exit').write_text(str(process.returncode) + '\n')
    receipt = {
        'protocol': 'SOURCE_BOUND_C2VR_INDUCTIVE_FIDELITY_V2',
        'case': case,
        'release': VERUS_RELEASE,
        'source_sha256': source_sha,
        'target_sha256': target_sha,
        'tool_sha256': sha256(verus_binary),
        'verus_version_output': (version.stdout + version.stderr).strip(),
        'exit': process.returncode,
        'log_sha256': hashlib.sha256((evidence_root / 'verus.log').read_bytes()).hexdigest(),
    }
    (evidence_root / 'native-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('source_root', type=Path)
    cli.add_argument('verus_binary', type=Path)
    cli.add_argument('evidence_root', type=Path)
    cli.add_argument('--case', choices=sorted(CASES), default='gcd')
    args = cli.parse_args()
    print(json.dumps(run_verus(args.source_root, args.verus_binary, args.evidence_root, case=args.case), indent=2))
