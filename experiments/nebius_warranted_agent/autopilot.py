"""Bounded coding agent whose actions are qualified by independently acquired test evidence.

This demonstrates test-scoped warrant, not a proof of general program correctness.
Offline fixture output is always marked as scripted, NEVER a Nebius API call.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Protocol
from urllib import request

SOURCE = '''def clamp(value, minimum, maximum):
    """Return value constrained to the inclusive interval [minimum, maximum]."""
    return max(minimum, min(value, maximum - 1))
'''
TESTS = '''import unittest
from calculator import clamp

class ClampTests(unittest.TestCase):
    def test_inside(self):
        self.assertEqual(clamp(5, 0, 10), 5)
    def test_lower(self):
        self.assertEqual(clamp(-3, 0, 10), 0)
    def test_upper(self):
        self.assertEqual(clamp(14, 0, 10), 10)
    def test_exact_upper(self):
        self.assertEqual(clamp(10, 0, 10), 10)
'''
ALLOWED = ("calculator.py", "test_calculator.py")
TEST_COMMAND = (sys.executable, "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v")
GOAL = "Repair clamp so it enforces inclusive lower and upper limits. Preserve function name and signature."


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot(root: Path) -> str:
    """Stable file-byte snapshot over the declared two-file test envelope."""
    entries = []
    for name in ALLOWED:
        p = root / name
        if p.is_symlink() or not p.is_file():
            raise ValueError(f"missing or nonregular evidence file: {name}")
        raw = p.read_bytes()
        entries.append([name, len(raw), digest(raw)])
    return digest(canonical(entries))


@dataclass(frozen=True)
class Receipt:
    source_sha256: str
    candidate_sha256: str
    after_sha256: str
    runner: str
    exit_code: int | None
    output_sha256: str
    outcome: str  # finished, timeout, or error
    acquired_at: str


def execute_tests(root: Path, source_sha256: str) -> tuple[Receipt, str]:
    before = snapshot(root)
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    try:
        result = subprocess.run(TEST_COMMAND, cwd=root, text=True, capture_output=True,
                                env=env, timeout=15, check=False)
        output = (result.stdout + "\n" + result.stderr)[:16000]
        exit_code, outcome = result.returncode, "finished"
    except subprocess.TimeoutExpired:
        output, exit_code, outcome = "bounded test execution timed out", None, "timeout"
    after = snapshot(root)
    return Receipt(source_sha256, before, after, " ".join(TEST_COMMAND),
                   exit_code, digest(output.encode()), outcome, timestamp()), output


def qualify(root: Path, source_sha256: str, receipt: Receipt | None) -> tuple[str, str]:
    """Strictly scoped to the declared test command and fixed source/test files."""
    if receipt is None:
        return "UNKNOWN", "no independent test receipt; acquire evidence"
    if receipt.source_sha256 != source_sha256:
        return "REJECTED", "receipt bound to another starting source"
    try:
        actual = snapshot(root)
    except ValueError as exc:
        return "REJECTED", str(exc)
    if actual != receipt.candidate_sha256 or receipt.after_sha256 != receipt.candidate_sha256:
        return "REJECTED", "test evidence does not describe current candidate bytes"
    if receipt.runner != " ".join(TEST_COMMAND):
        return "REJECTED", "unapproved test runner"
    if receipt.outcome != "finished" or receipt.exit_code is None:
        return "UNKNOWN", "test run failed to complete; reacquire evidence"
    if receipt.exit_code != 0:
        return "REJECTED", "declared tests did not pass"
    return "WARRANTED", "declared local tests passed for exactly these file bytes"


@dataclass(frozen=True)
class Proposal:
    code: str
    provider: str
    model: str
    response_sha256: str
    request_id: str | None
    generated_at: str


class Provider(Protocol):
    def propose(self, current: str, test_output: str, attempt: int) -> Proposal: ...


class ScriptedProvider:
    """Offline fixture; deliberately fails first so iteration is observable."""
    def propose(self, current: str, test_output: str, attempt: int) -> Proposal:
        code = ('''def clamp(value, minimum, maximum):
    return value
''' if attempt == 1 else '''def clamp(value, minimum, maximum):
    """Return value constrained to the inclusive interval [minimum, maximum]."""
    return max(minimum, min(value, maximum))
''')
        return Proposal(code, "SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS", "none",
                        digest(code.encode()), None, timestamp())


class NebiusProvider:
    BASE = "https://api.tokenfactory.nebius.com/v1/chat/completions"

    def __init__(self, model: str):
        self.key = os.environ.get("NEBIUS_API_KEY", "")
        if not self.key:
            raise RuntimeError("NEBIUS_API_KEY missing; configure a secret, never commit a key")
        self.model = model

    def propose(self, current: str, test_output: str, attempt: int) -> Proposal:
        messages = [
            {"role": "system", "content": "You are a coding agent. Respond ONLY with a JSON object containing one string field 'file_content'. Replace calculator.py completely. Do not change tests, run commands, or other files."},
            {"role": "user", "content": f"Goal: {GOAL}\nAttempt: {attempt}\nCurrent calculator.py:\n{current}\nIndependent test output:\n{test_output[:6000]}\nReturn the complete corrected calculator.py as JSON."}
        ]
        payload = canonical({"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": 2000})
        req = request.Request(self.BASE, data=payload, method="POST",
                              headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key})
        try:
            with request.urlopen(req, timeout=60) as res:
                raw = res.read(1048576)
                header_id = res.headers.get("x-request-id")
        except Exception as exc:
            raise RuntimeError(f"Nebius inference did not complete ({type(exc).__name__}); no live inference evidence") from exc
        response = json.loads(raw)
        if response.get("model") and response["model"] != self.model:
            raise ValueError("response model identity differs from requested NVIDIA model")
        text = response["choices"][0]["message"]["content"]
        if not isinstance(text, str):
            raise ValueError("Nebius returned no text content")
        # Strict JSON; never execute model-provided shell, Python or arbitrary paths.
        content = json.loads(text)
        if set(content) != {"file_content"} or not isinstance(content["file_content"], str):
            raise ValueError("model must return exactly one file_content string")
        return Proposal(content["file_content"], "nebius-token-factory", self.model,
                        digest(raw), str(header_id or response.get("id") or ""), timestamp())


def validate_repair_ast(code: str) -> None:
    """Only permit a pure clamp function for this *bounded* coding demonstration.

    A general-purpose coding agent needs a separately isolated execution runtime;
    the CLI intentionally does not execute unrestricted model-generated code.
    """
    try:
        module = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError("model proposal is not valid Python") from exc
    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        raise ValueError("expected exactly one clamp function")
    fun = module.body[0]
    if (fun.name != "clamp" or fun.decorator_list or fun.returns is not None
            or bool(getattr(fun, "type_params", []))):
        raise ValueError("unexpected function definition")
    params = fun.args
    if (params.posonlyargs or params.kwonlyargs or params.vararg or params.kwarg
            or params.defaults or params.kw_defaults or
            [a.arg for a in params.args] != ["value", "minimum", "maximum"] or
            any(a.annotation is not None for a in params.args)):
        raise ValueError("clamp signature changed")
    statements = fun.body
    if (len(statements) == 2 and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Constant)
            and isinstance(statements[0].value.value, str)):
        statements = statements[1:]
    if len(statements) != 1 or not isinstance(statements[0], ast.Return):
        raise ValueError("only a pure single-return clamp is permitted")
    allowed = (ast.Call, ast.Name, ast.Load, ast.Constant)
    for n in ast.walk(statements[0].value):
        if not isinstance(n, allowed):
            raise ValueError(f"unsupported expression node: {type(n).__name__}")
        if isinstance(n, ast.Call) and (not isinstance(n.func, ast.Name)
                or n.func.id not in ("min", "max") or n.keywords):
            raise ValueError("only min/max calls allowed")
        if isinstance(n, ast.Name) and n.id not in ("value", "minimum", "maximum", "min", "max"):
            raise ValueError("unknown expression identifier")
        if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float)):
            raise ValueError("unsupported literal type")


def apply_code(root: Path, proposal: Proposal, frozen_test_sha: str) -> None:
    raw = proposal.code.encode("utf-8")
    if len(raw) > 16_000 or b"\x00" in raw:
        raise ValueError("patch exceeds bounded text policy")
    validate_repair_ast(proposal.code)
    # Guard that the model's text cannot edit tests or change test-file authority.
    if digest((root / "test_calculator.py").read_bytes()) != frozen_test_sha:
        raise ValueError("protected test file changed")
    (root / "calculator.py").write_bytes(raw)


def drive(provider: Provider, max_attempts: int = 3) -> dict:
    with TemporaryDirectory(prefix="mathgraph-nebius-") as directory:
        root = Path(directory)
        (root / "calculator.py").write_text(SOURCE)
        (root / "test_calculator.py").write_text(TESTS)
        source_sha = snapshot(root)
        test_sha = digest(TESTS.encode())
        events = []
        old_receipt, last_output = execute_tests(root, source_sha)
        events.append({"step": "initial_failure", "state": qualify(root, source_sha, old_receipt)[0],
                       "receipt": asdict(old_receipt)})
        success = False
        for attempt in range(1, max_attempts + 1):
            proposal = provider.propose((root / "calculator.py").read_text(), last_output, attempt)
            apply_code(root, proposal, test_sha)
            before_check = qualify(root, source_sha, old_receipt)
            # A change MUST revoke the old receipt, even if the previous tests passed.
            if before_check[0] != "REJECTED":
                raise AssertionError("changed code improperly retained prior warrant")
            missing = qualify(root, source_sha, None)
            receipt, last_output = execute_tests(root, source_sha)
            state, reason = qualify(root, source_sha, receipt)
            events.append({"step": "repair_attempt", "attempt": attempt,
                           "proposal": asdict(proposal), "old_evidence_state": before_check[0],
                           "missing_evidence_state": missing[0], "state": state,
                           "reason": reason, "receipt": asdict(receipt)})
            old_receipt = receipt
            if state == "WARRANTED":
                success = True
                break
        if success:
            # Threat regression: invalidate warranted receipt by modifying the code.
            current = (root / "calculator.py").read_bytes()
            (root / "calculator.py").write_bytes(current + b"\n# post-test edit\n")
            stale = qualify(root, source_sha, old_receipt)
            if stale[0] != "REJECTED":
                raise AssertionError("post-test edit was not detected")
            events.append({"step": "post_test_mutation", "state": stale[0], "reason": stale[1]})
            (root / "calculator.py").write_bytes(current)
            reacquired, _ = execute_tests(root, source_sha)
            recovered = qualify(root, source_sha, reacquired)
            if recovered[0] != "WARRANTED":
                raise AssertionError("reacquired independent evidence not accepted")
            events.append({"step": "reacquire", "state": recovered[0], "receipt": asdict(reacquired)})
        return {"schema": "mathgraph.autopilot.local-demo.v1", "scope": "trusted local Python fixture and declared unittest suite; not a proof of general correctness",
                "source_sha256": source_sha, "provider": provider.__class__.__name__,
                "final_state": "WARRANTED" if success else "REJECTED", "events": events}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["scripted", "nebius"], default="scripted")
    parser.add_argument("--model", default="nvidia/nemotron-3-super-120b-a12b")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--report", help="Write structured report here")
    args = parser.parse_args()
    if not 1 <= args.max_attempts <= 5:
        parser.error("max-attempts must be 1..5")
    provider = ScriptedProvider() if args.provider == "scripted" else NebiusProvider(args.model)
    output = drive(provider, args.max_attempts)
    data = json.dumps(output, indent=2, sort_keys=True)
    if args.report:
        Path(args.report).write_text(data + "\n")
    print(data)
    if output["final_state"] != "WARRANTED":
        sys.exit(1)


if __name__ == "__main__":
    main()
