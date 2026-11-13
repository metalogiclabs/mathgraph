"""Exact-source upstream transfer: real native tests, deliberately injected defects.

This does NOT assert any defect in pallets/itsdangerous upstream.
Model proposals are NOT used here; synthetic mutations are predeclared.
Never run against an unpinned checkout or with privileged environment secrets.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

UPSTREAM_REPO = "pallets/itsdangerous"
UPSTREAM_COMMIT = "672971d66a2ef9f85151e53283113f33d642dabd"
ENCODING_PATH = "src/itsdangerous/encoding.py"
TEST_PATH = "tests/test_itsdangerous/test_encoding.py"
ENCODING_BLOB = "f5ca80f905c9bb29b993c437a89174e668704658"
TEST_BLOB = "268367e6b10b33c846beb6c60eeae64ce1c3072d"
EXPRESSION = 'return base64.urlsafe_b64encode(string).rstrip(b"=")'
MUTANTS = {
    "standard_alphabet": 'return base64.b64encode(string).rstrip(b"=")',
    "unstripped_padding": 'return base64.urlsafe_b64encode(string)',
    "trailing_zero_loss": (
        'return base64.urlsafe_b64encode('
        'string.rstrip(b"\\x00") if len(string) % 3 == 0 else string).rstrip(b"=")'
    ),
}
NATIVE_COMMAND = (sys.executable, "-B", "-m", "pytest", "-q", "-p",
                  "no:cacheprovider", "-o", "addopts=", "test_encoding.py")
EXPANDED_COMMAND = NATIVE_COMMAND + ("test_mathgraph_acquired.py",)
NAMES = ("src/itsdangerous/encoding.py", "test_encoding.py",
         "test_mathgraph_acquired.py")

def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def git_value(checkout: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(checkout), *args], text=True, timeout=15
    ).strip()

def pinned_source(checkout: Path) -> dict:
    if git_value(checkout, "rev-parse", "HEAD") != UPSTREAM_COMMIT:
        raise ValueError("UPSTREAM_COMMIT_NOT_PINNED")
    evidence = {}
    for relative, expected in ((ENCODING_PATH, ENCODING_BLOB),
                               (TEST_PATH, TEST_BLOB)):
        path = checkout / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("UPSTREAM_FILE_NOT_REGULAR")
        actual = git_value(checkout, "hash-object", relative)
        if actual != expected:
            raise ValueError("UPSTREAM_GIT_BLOB_MISMATCH:" + relative)
        evidence[relative] = {"git_blob_sha1": actual,
                              "sha256": digest(path.read_bytes())}
    return evidence

def copy_package(checkout: Path, root: Path, source: bytes, acquired: bytes | None = None):
    package = checkout / "src" / "itsdangerous"
    if not package.is_dir() or package.is_symlink():
        raise ValueError("INVALID_PACKAGE_DIR")
    shutil.copytree(package, root / "src" / "itsdangerous",
                    symlinks=False, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "src" / "itsdangerous" / "encoding.py").write_bytes(source)
    shutil.copyfile(checkout / TEST_PATH, root / "test_encoding.py")
    if acquired is not None:
        (root / "test_mathgraph_acquired.py").write_bytes(acquired)

def mutate(original: bytes, name: str) -> bytes:
    raw = original.decode("utf-8")
    if raw.count(EXPRESSION) != 1 or name not in MUTANTS:
        raise ValueError("UPSTREAM_MUTATION_PRECONDITION_FAILED")
    return raw.replace(EXPRESSION, MUTANTS[name]).encode("utf-8")

def domain() -> tuple[bytes, ...]:
    """Frozen allowed bytes; synthetic finite query cost = 1 + input length."""
    items = [b"", b"infinite", "無限".encode("utf-8")]
    items += [bytes((i,)) for i in range(256)]
    items += [bytes((i, 0)) for i in range(256)]
    items += [bytes((0, i)) for i in range(256)]
    items += [bytes((i, 0, 0)) for i in range(256)]
    return tuple(sorted(set(items), key=lambda b: (len(b), b)))

def oracle(value: bytes) -> bytes:
    """Independent reference: standard-library URL-safe encoding contract."""
    return base64.urlsafe_b64encode(value).rstrip(b"=")

def call_native_code(root: Path, inputs: tuple[bytes, ...]) -> list[bytes]:
    """Execute pinned source with isolated import path; no generated model code."""
    payload = [item.hex() for item in inputs]
    program = (
        "import json,sys;"
        "from itsdangerous.encoding import base64_encode;"
        "x=json.load(sys.stdin);"
        "json.dump([base64_encode(bytes.fromhex(v)).hex() for v in x],sys.stdout)"
    )
    env = process_env(root)
    run = subprocess.run([sys.executable, "-B", "-c", program],
                         input=json.dumps(payload), text=True, capture_output=True,
                         cwd=root, env=env, timeout=20, check=False)
    if run.returncode != 0:
        raise RuntimeError("NATIVE_SOURCE_EVALUATION_FAILED:" + run.stderr[-300:])
    result = json.loads(run.stdout)
    if len(result) != len(inputs):
        raise AssertionError("incomplete native evaluation")
    return [bytes.fromhex(item) for item in result]

def process_env(root: Path) -> dict[str, str]:
    # No untrusted caller secrets propagated to subprocess.
    return {"PATH": os.environ.get("PATH", ""),
            "HOME": str(root), "PYTHONPATH": str(root / "src"),
            "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "LANG": "C.UTF-8"}

def snapshot(root: Path) -> str:
    rows = []
    for relative in NAMES:
        path = root / relative
        if path.is_symlink():
            raise ValueError("SYMLINK_IN_EVIDENCE_ENVELOPE")
        raw = path.read_bytes() if path.is_file() else None
        rows.append([relative, None if raw is None else len(raw),
                     None if raw is None else digest(raw)])
    return digest(canonical(rows))

@dataclass(frozen=True)
class Receipt:
    source_commit: str
    source_sha256: str
    before_snapshot: str
    after_snapshot: str
    command: tuple[str, ...]
    exit_code: int | None
    stdout_sha256: str
    outcome: str
    acquired_at: str

def execute(root: Path, original_source_sha: str,
            command: tuple[str, ...]) -> Receipt:
    if command not in (NATIVE_COMMAND, EXPANDED_COMMAND):
        raise ValueError("TEST_RUNNER_NOT_ALLOWLISTED")
    before = snapshot(root)
    try:
        result = subprocess.run(command, cwd=root, env=process_env(root),
                                text=True, capture_output=True, timeout=45,
                                check=False)
        code, outcome = result.returncode, "finished"
        out = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        code, outcome, out = None, "timeout", "test timeout"
    return Receipt(UPSTREAM_COMMIT, original_source_sha, before,
                   snapshot(root), command, code, digest(out.encode()),
                   outcome, datetime.now(timezone.utc).isoformat())

def qualify(root: Path, receipt: Receipt | None,
            original_sha: str, expected_command: tuple[str, ...]) -> tuple[str, str]:
    if receipt is None:
        return "UNKNOWN", "no test receipt: acquire evidence"
    if receipt.source_commit != UPSTREAM_COMMIT or receipt.source_sha256 != original_sha:
        return "REJECTED", "source authority does not match pinned upstream"
    if receipt.command != expected_command:
        return "REJECTED", "unapproved or stale test envelope"
    actual = snapshot(root)
    if actual != receipt.before_snapshot or actual != receipt.after_snapshot:
        return "REJECTED", "test receipt does not bind exact current source and tests"
    if receipt.outcome != "finished":
        return "UNKNOWN", "runner incomplete"
    if receipt.exit_code != 0:
        return "REJECTED", "independently executed native tests failed"
    return "WARRANTED", "only the explicitly declared tests for these bytes"

def minimum_separator(inputs: tuple[bytes, ...],
                      observations: dict[str, list[bytes]]) -> dict:
    reference = observations["reference"]
    rivals = tuple(sorted(name for name in observations if name != "reference"))
    if not rivals or len(rivals) > 16:
        raise ValueError("must have 1..16 declared rivals")
    if len(reference) != len(inputs) or any(len(observations[n]) != len(inputs) for n in rivals):
        raise ValueError("incomplete observations")
    cover = []
    for i, value in enumerate(inputs):
        mask = sum(1 << j for j, name in enumerate(rivals)
                   if observations[name][i] != reference[i])
        if mask:
            cover.append((value, mask, 1 + len(value)))
    best: dict[int, tuple[int, int, tuple[bytes, ...]]] = {0: (0, 0, ())}
    for value, mask, cost in cover:
        nxt = best.copy()
        for current, (total, count, cases) in best.items():
            target = current | mask
            proposal = (total + cost, count + 1, cases + (value,))
            if target not in nxt or proposal < nxt[target]:
                nxt[target] = proposal
        best = nxt
    allmask = (1 << len(rivals)) - 1
    optimum = best.get(allmask)
    return {"status": "MINIMUM_BASIS" if optimum else "OBSTRUCTION",
            "domain_size": len(inputs), "rivals": list(rivals),
            "tests_hex": [x.hex() for x in optimum[2]] if optimum else [],
            "total_synthetic_cost": optimum[0] if optimum else None,
            "unsplittable": [name for j, name in enumerate(rivals)
                            if not any(m & (1 << j) for _, m, _ in cover)],
            "cover_records": [[x.hex(), m, c] for x, m, c in cover]}

def independent_minimum_bound(records: list[list]) -> int | None:
    """Source-distinct pairwise exhaustive search, not the DP implementation."""
    from itertools import combinations
    maximum = 7  # exactly the three frozen mutations
    candidates = [(int(mask), int(price)) for _, mask, price in records]
    winning = [price for mask, price in candidates if mask == maximum]
    for (a, ca), (b, cb) in combinations(candidates, 2):
        if a | b == maximum:
            winning.append(ca + cb)
    return min(winning) if winning else None

def acquired_tests(cases: tuple[bytes, ...]) -> bytes:
    source = ["from itsdangerous.encoding import base64_encode", "",
              "def test_mathgraph_separating_evidence():"]
    for value in cases:
        expected = oracle(value)
        source.append("    assert base64_encode(bytes.fromhex(%r)) == bytes.fromhex(%r)"
                      % (value.hex(), expected.hex()))
    return ("\n".join(source) + "\n").encode()

def experiment(checkout: Path) -> dict:
    pins = pinned_source(checkout)
    source = (checkout / ENCODING_PATH).read_bytes()
    source_sha = digest(source)
    inputs = domain()
    observations = {}
    with TemporaryDirectory(prefix="mathgraph-upstream-source-") as base:
        root = Path(base)
        for name in ("reference",) + tuple(sorted(MUTANTS)):
            work = root / name
            work.mkdir()
            candidate = source if name == "reference" else mutate(source, name)
            copy_package(checkout, work, candidate)
            observations[name] = call_native_code(work, inputs)
            if name == "reference" and observations[name] != [oracle(v) for v in inputs]:
                raise AssertionError("UPSTREAM_SOURCE_DISAGREES_WITH_INDEPENDENT_ORACLE")
        chosen = minimum_separator(inputs, observations)
        exhaustive = independent_minimum_bound(chosen["cover_records"])
        if chosen["status"] != "MINIMUM_BASIS" or exhaustive != chosen["total_synthetic_cost"]:
            raise AssertionError("SELECTOR_NOT_INDEPENDENTLY_MINIMAL")
        if len(chosen["tests_hex"]) < 2:
            raise AssertionError("INSUFFICIENT_ABLATION_STRESS")
        # Native upstream tests are executed, not assumed from fixture simulation.
        for name in sorted(MUTANTS):
            work = root / name
            original = work / "src" / "itsdangerous" / "encoding.py"
            baseline_receipt = execute(work, source_sha, NATIVE_COMMAND)
            baseline, _ = qualify(work, baseline_receipt, source_sha, NATIVE_COMMAND)
            if baseline != "WARRANTED":
                raise AssertionError("MUTATION_NOT_NATIVE_TEST_INVISIBLE:" + name)
        broken = root / "standard_alphabet"
        old = execute(broken, source_sha, NATIVE_COMMAND)
        baseline = qualify(broken, old, source_sha, NATIVE_COMMAND)[0]
        selected = tuple(bytes.fromhex(x) for x in chosen["tests_hex"])
        (broken / "test_mathgraph_acquired.py").write_bytes(acquired_tests(selected))
        withdraw = qualify(broken, old, source_sha, NATIVE_COMMAND)[0]
        missing = qualify(broken, None, source_sha, EXPANDED_COMMAND)[0]
        new_receipt = execute(broken, source_sha, EXPANDED_COMMAND)
        rejected = qualify(broken, new_receipt, source_sha, EXPANDED_COMMAND)[0]
        (broken / "src" / "itsdangerous" / "encoding.py").write_bytes(source)
        stale = qualify(broken, new_receipt, source_sha, EXPANDED_COMMAND)[0]
        repaired_receipt = execute(broken, source_sha, EXPANDED_COMMAND)
        repaired = qualify(broken, repaired_receipt, source_sha, EXPANDED_COMMAND)[0]
        if [baseline, withdraw, missing, rejected, stale, repaired] != [
                "WARRANTED", "REJECTED", "UNKNOWN", "REJECTED", "REJECTED", "WARRANTED"]:
            raise AssertionError("AUTHORITY_TRANSITION_FAILED")
        if new_receipt.exit_code == 0 or repaired_receipt.exit_code != 0:
            raise AssertionError("NATIVE_TEST_ABLATION_FAILED")
        result = {
            "schema":"mathgraph.upstream-evidence-acquisition.v1",
            "mode":"PINNED_UPSTREAM_WITH_SCRIPTED_MUTATIONS_NOT_LIVE_NEBIUS",
            "origin":{"repository":UPSTREAM_REPO,"commit":UPSTREAM_COMMIT,
                      "file_evidence":pins,
                      "upstream_bug_claim":False,
                      "source_policy":"checkout exact commit and compare Git blob hashes"},
            "experiment":{"original_suite":"source-native pytest test_encoding.py",
                          "mutation_names":sorted(MUTANTS),
                          "testcase_domain":len(inputs),
                          "reference":"Python stdlib urlsafe_b64encode without padding",
                          "cost":"1 + number of encoded input bytes; synthetic",
                          "minimum_tests_hex":chosen["tests_hex"],
                          "minimum_synthetic_cost":chosen["total_synthetic_cost"],
                          "independent_brute_force_cost":exhaustive,
                          "rivals_separated":chosen["rivals"]},
            "comparison":{"baseline_original_tests":baseline,
                          "with_new_test":rejected,
                          "after_scripted_repair":repaired,
                          "native_mutant_tests_pass":sorted(MUTANTS)},
            "transitions":[
                {"step":"native_original_tests","state":baseline,"receipt":asdict(old)},
                {"step":"test_source_changed","state":withdraw},
                {"step":"missing_evidence","state":missing},
                {"step":"new_test_fails","state":rejected,"receipt":asdict(new_receipt)},
                {"step":"candidate_changed","state":stale},
                {"step":"fresh_expanded_tests","state":repaired,
                 "receipt":asdict(repaired_receipt)}]}
        return result

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--upstream-checkout", type=Path, required=True)
    p.add_argument("--report", type=Path, default=Path("upstream-transfer-report.json"))
    args = p.parse_args()
    report = experiment(args.upstream_checkout.resolve())
    args.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"origin":report["origin"]["commit"],
        "comparison":report["comparison"],"experiment":report["experiment"]},
        sort_keys=True,indent=2))

if __name__ == "__main__":
    main()
