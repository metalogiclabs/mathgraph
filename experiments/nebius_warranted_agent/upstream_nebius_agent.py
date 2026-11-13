"""Bounded live Nebius repair of a pinned, deliberately mutated upstream function.

Offline mode uses scripted proposals, NEVER Nebius inference. Live mode sends
the fixed, predeclared source-native encoding task to NVIDIA Nemotron via Nebius.
The separate pinned upstream tests determine permission; model output does not.
No arbitrary model-generated imports, function bodies, shell or paths are allowed.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib import request

from upstream_encoding_transfer import (
    ENCODING_PATH, EXPANDED_COMMAND, NATIVE_COMMAND, UPSTREAM_COMMIT,
    MUTANTS, acquired_tests, call_native_code, copy_package, digest, domain,
    execute, independent_minimum_bound, minimum_separator, mutate,
    oracle, pinned_source, qualify, snapshot
)

DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
TASK = ("Repair the URL-safe unpadded Base64 encoder in the pinned Pallets "
        "itsdangerous source. Keep its public function name and signature; "
        "preserve input conversion, return bytes, and satisfy additional "
        "counterexamples selected by an independent checker.")
ORIGINAL_FUNCTION = '''def base64_encode(string: str | bytes) -> bytes:
    """Base64 encode a string of bytes or text. The resulting bytes are
    safe to use in URLs.
    """
    string = want_bytes(string)
    return base64.urlsafe_b64encode(string).rstrip(b"=")
'''
WRONG_FIRST = '''def base64_encode(string: str | bytes) -> bytes:
    string = want_bytes(string)
    return base64.urlsafe_b64encode(string)
'''


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Proposal:
    source: str
    provider: str
    model: str
    response_sha256: str
    request_id: str | None
    created_at: str


class ScriptedProvider:
    """A controlled baseline; does not claim model generation."""
    def propose(self, current: str, evidence: list[tuple[str, str]],
                attempt: int, feedback: str = "") -> Proposal:
        source = WRONG_FIRST if attempt == 1 else ORIGINAL_FUNCTION
        return Proposal(source, "SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS", "none",
                        digest(source.encode()), None, utc())


class NebiusProvider:
    def __init__(self, model: str = DEFAULT_MODEL):
        key = os.environ.get("NEBIUS_API_KEY")
        if not key:
            raise RuntimeError("NEBIUS_API_KEY not configured in private environment")
        if not model.startswith("nvidia/"):
            raise ValueError("NVIDIA_OPEN_MODEL_REQUIRED")
        self._key = key
        self.model = model

    def propose(self, current: str, evidence: list[tuple[str, str]],
                attempt: int, feedback: str = "") -> Proposal:
        messages = [
            {"role": "system", "content":
             "You are a code repair agent. Reply with one JSON object with exactly "
             "one string key 'function_source'. The value must be a Python function "
             "with this exact two-statement body: "
             "def base64_encode(string: str | bytes) -> bytes; "
             "statement one: string = want_bytes(string); "
             "statement two: return EXPRESSION. "
             "Choose EXPRESSION from base64.urlsafe_b64encode(string) or "
             "base64.b64encode(string), optionally followed by .rstrip(b'='). "
             "No extra statements, comments, docstrings, helpers, markdown or tests. "
             "Encode newline characters as escaped JSON newlines."},
            {"role": "user", "content":
             f"Source authority: {UPSTREAM_COMMIT}\n"
             f"Objective: {TASK}\nAttempt: {attempt}\n"
             f"Current function:\n{current}\n"
             f"Independently generated failing counterexamples (input hex, expected output hex): "
             f"{json.dumps(evidence, separators=(',', ':'))}\n"
             f"Verifier feedback on previous proposal: {feedback or 'none'}\\n"
             "Return only the exact two-statement function source in JSON."},
        ]
        # Nemotron 3 Super reasons by default. With a small max_tokens budget,
        # all output can be spent on reasoning, leaving message.content null.
        # Disable thinking explicitly for this short, strictly bounded repair.
        # NVIDIA documents chat_template_kwargs.enable_thinking=False.
        # Token Factory guided JSON schema (per its official cookbook):
        # grammar-constrain the one-field response before AST validation.
        output_schema = {
            "type": "object",
            "properties": {"function_source": {"type": "string"}},
            "required": ["function_source"],
            "additionalProperties": False,
        }
        payload = json.dumps({"model": self.model, "messages": messages,
                              "temperature": 0.1, "max_tokens": 2048,
                              "chat_template_kwargs": {"enable_thinking": False},
                              "guided_json": output_schema,
                              "response_format": {"type": "json_object"}},
                             sort_keys=True).encode()
        req = request.Request(
            ENDPOINT, data=payload, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self._key},
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read(1024 * 1024)
                header_id = response.headers.get("x-request-id")
        except Exception as exc:
            # Intentionally redact exception text (may include request URL/headers).
            raise RuntimeError("NEBIUS_INFERENCE_UNVERIFIED:" + type(exc).__name__) from None
        result = json.loads(raw)
        if result.get("model") and result["model"] != self.model:
            raise ValueError("NEBIUS_MODEL_ID_MISMATCH")
        choice = result["choices"][0]
        message = choice["message"].get("content")
        if not isinstance(message, str) or not message.strip():
            # Never print the returned raw text or reasoning. These allowlisted
            # diagnostics identify empty generation without disclosing content.
            finish = choice.get("finish_reason")
            finish = finish if finish in ("stop", "length", "content_filter",
                                          "tool_calls", "function_call") else "other"
            has_reasoning = bool(choice["message"].get("reasoning_content"))
            raise ValueError(
                f"NEBIUS_RESPONSE_NOT_TEXT:finish={finish}:"
                f"reasoning_present={int(has_reasoning)}"
            )
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            # Model output is untrusted; never repair malformed JSON by guesses.
            raise ValueError("NEBIUS_PROPOSAL_INVALID_JSON") from None
        if not isinstance(parsed, dict) or set(parsed) != {"function_source"}:
            raise ValueError("NEBIUS_PROPOSAL_WRONG_SCHEMA")
        function = parsed["function_source"]
        if not isinstance(function, str):
            raise ValueError("NEBIUS_PROPOSAL_NOT_STRING")
        return Proposal(function, "nebius-token-factory", self.model,
                        digest(raw), str(header_id or result.get("id") or "") or None, utc())


def validate_function(source: str) -> None:
    """Restricted function language; not a general-purpose Python sandbox.

    The only executable call graph allowed is want_bytes -> standard-library
    base64.{urlsafe_b64encode,b64encode} -> optional bytes.rstrip(b'=').
    The verifier, not this grammar, detects semantic failures in that graph.
    """
    if len(source.encode("utf-8")) > 12000 or "\x00" in source:
        raise ValueError("MODEL_SOURCE_SIZE_OR_NUL")
    try:
        parsed = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError("MODEL_SOURCE_NOT_PYTHON") from exc
    if len(parsed.body) != 1 or not isinstance(parsed.body[0], ast.FunctionDef):
        raise ValueError("MODEL_SOURCE_NOT_SINGLE_FUNCTION")
    f = parsed.body[0]
    a = f.args
    if (f.name != "base64_encode" or f.decorator_list or
        a.posonlyargs or a.kwonlyargs or a.vararg or a.kwarg or
        a.defaults or a.kw_defaults or len(a.args) != 1 or
        a.args[0].arg != "string" or
        (a.args[0].annotation is not None and
         ast.unparse(a.args[0].annotation) != "str | bytes") or
        (f.returns is not None and ast.unparse(f.returns) != "bytes") or
        bool(getattr(f, "type_params", []))):
        raise ValueError("MODEL_FUNCTION_SIGNATURE_REJECTED")
    body = f.body
    if (body and isinstance(body[0], ast.Expr) and
        isinstance(body[0].value, ast.Constant) and
        isinstance(body[0].value.value, str)):
        body = body[1:]
    if len(body) != 2 or not isinstance(body[0], ast.Assign) or not isinstance(body[1], ast.Return):
        raise ValueError("MODEL_BODY_NOT_PURE_ASSIGN_RETURN")
    first = body[0]
    if (len(first.targets) != 1 or not isinstance(first.targets[0], ast.Name) or
        first.targets[0].id != "string" or not isinstance(first.value, ast.Call) or
        not isinstance(first.value.func, ast.Name) or
        first.value.func.id != "want_bytes" or first.value.keywords or
        len(first.value.args) != 1 or
        not isinstance(first.value.args[0], ast.Name) or
        first.value.args[0].id != "string"):
        raise ValueError("MODEL_INPUT_CONVERSION_REJECTED")

    def encoded(node: ast.expr) -> bool:
        return (isinstance(node, ast.Call) and not node.keywords and
                isinstance(node.func, ast.Attribute) and
                node.func.attr in ("urlsafe_b64encode", "b64encode") and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == "base64" and
                len(node.args) == 1 and
                isinstance(node.args[0], ast.Name) and node.args[0].id == "string")

    result = body[1].value
    safe = encoded(result)
    if (isinstance(result, ast.Call) and not result.keywords and
        isinstance(result.func, ast.Attribute) and
        result.func.attr == "rstrip" and encoded(result.func.value) and
        len(result.args) == 1 and isinstance(result.args[0], ast.Constant) and
        type(result.args[0].value) is bytes and result.args[0].value == b"="):
        safe = True
    if not safe:
        raise ValueError("MODEL_RETURN_CALL_GRAPH_REJECTED")


def only_function(code: bytes) -> str:
    lines = code.decode("utf-8").splitlines(keepends=True)
    tree = ast.parse(code)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == "base64_encode"]
    if len(functions) != 1:
        raise ValueError("PINNED_SOURCE_FUNCTION_NOT_UNIQUE")
    f = functions[0]
    return "".join(lines[f.lineno-1:f.end_lineno])


def normalize_function_text(proposal: str) -> str:
    """Remove only an exact outer Python code fence, never extract arbitrary code."""
    raw = proposal.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) < 3 or lines[0] not in ("```", "```python", "```py") or lines[-1] != "```":
            raise ValueError("MODEL_CODE_FENCE_NOT_EXACT")
        raw = "\n".join(lines[1:-1]).strip()
    return raw + "\n"


def replace_function(code: bytes, proposal: str) -> bytes:
    proposal = normalize_function_text(proposal)
    validate_function(proposal)
    lines = code.decode("utf-8").splitlines(keepends=True)
    tree = ast.parse(code)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == "base64_encode"]
    if len(functions) != 1:
        raise ValueError("PINNED_SOURCE_FUNCTION_NOT_UNIQUE")
    f = functions[0]
    normalized = proposal.strip("\n") + "\n"
    return ("".join(lines[:f.lineno-1]) + normalized +
            "".join(lines[f.end_lineno:])).encode("utf-8")


def perform(checkout: Path, provider, max_attempts: int = 3) -> dict:
    if not 1 <= max_attempts <= 5:
        raise ValueError("ATTEMPTS_OUTSIDE_FINITE_BUDGET")
    pins = pinned_source(checkout)
    original = (checkout / ENCODING_PATH).read_bytes()
    start_sha = digest(original)
    inputs = domain()
    with TemporaryDirectory(prefix="mathgraph-live-nebius-upstream-") as directory:
        root = Path(directory)
        reference = root / "reference"
        reference.mkdir()
        copy_package(checkout, reference, original)
        expected = call_native_code(reference, inputs)
        if expected != [oracle(v) for v in inputs]:
            raise AssertionError("REFERENCE_ORACLE_MISMATCH")
        observations = {"reference": expected}
        for name in sorted(MUTANTS):
            mutant = root / name
            mutant.mkdir()
            copy_package(checkout, mutant, mutate(original, name))
            observations[name] = call_native_code(mutant, inputs)
        basis = minimum_separator(inputs, observations)
        if (basis["status"] != "MINIMUM_BASIS" or
            independent_minimum_bound(basis["cover_records"]) !=
                basis["total_synthetic_cost"]):
            raise AssertionError("MINIMUM_SEPARATOR_NOT_INDEPENDENTLY_VERIFIED")

        sandbox = root / "working"
        sandbox.mkdir()
        copy_package(checkout, sandbox, mutate(original, "standard_alphabet"))
        fixed = execute(sandbox, start_sha, NATIVE_COMMAND)
        native_state = qualify(sandbox, fixed, start_sha, NATIVE_COMMAND)[0]
        if native_state != "WARRANTED":
            raise AssertionError("NATIVE_BASELINE_WOULD_NOT_PASS")
        acquired = tuple(bytes.fromhex(x) for x in basis["tests_hex"])
        (sandbox / "test_mathgraph_acquired.py").write_bytes(acquired_tests(acquired))
        obsolete = qualify(sandbox, fixed, start_sha, NATIVE_COMMAND)[0]
        missing = qualify(sandbox, None, start_sha, EXPANDED_COMMAND)[0]
        failing = execute(sandbox, start_sha, EXPANDED_COMMAND)
        discovered = qualify(sandbox, failing, start_sha, EXPANDED_COMMAND)[0]
        if [obsolete, missing, discovered] != ["REJECTED", "UNKNOWN", "REJECTED"]:
            raise AssertionError("EVIDENCE_ACQUISITION_NO_FAILURE")
        events = [
            {"step":"native_baseline", "state":native_state, "receipt":asdict(fixed)},
            {"step":"old_tests_invalidated", "state":obsolete},
            {"step":"missing_evidence", "state":missing},
            {"step":"new_evidence_detects_defect", "state":discovered,
             "receipt":asdict(failing)},
        ]
        success = False
        last_feedback = ""
        for attempt in range(1, max_attempts+1):
            current = (sandbox / "src" / "itsdangerous" / "encoding.py").read_bytes()
            evidence = [(x.hex(), oracle(x).hex()) for x in acquired]
            proposal = provider.propose(only_function(current), evidence, attempt, last_feedback)
            last_feedback = ""
            # A bad proposal is recorded as REJECTED, but cannot alter the source.
            try:
                proposed_bytes = replace_function(current, proposal.source)
            except ValueError as exc:
                last_feedback = str(exc)
                events.append({"step":"rejected_proposal","attempt":attempt,
                               "state":"REJECTED","reason":str(exc),
                               "provider":proposal.provider,"model":proposal.model,
                               "response_sha256":proposal.response_sha256,
                               "request_id":proposal.request_id})
                continue
            (sandbox / "src" / "itsdangerous" / "encoding.py").write_bytes(proposed_bytes)
            prior = qualify(sandbox, failing, start_sha, EXPANDED_COMMAND)[0]
            if prior != "REJECTED":
                raise AssertionError("OLD_TEST_RECEIPT_NOT_REVOKED")
            receipt = execute(sandbox, start_sha, EXPANDED_COMMAND)
            state, reason = qualify(sandbox, receipt, start_sha, EXPANDED_COMMAND)
            events.append({"step":"model_repair_attempt","attempt":attempt,
                           "state":state,"reason":reason,
                           "provider":proposal.provider,"model":proposal.model,
                           "response_sha256":proposal.response_sha256,
                           "request_id":proposal.request_id,
                           "candidate_sha256":digest(proposed_bytes),
                           "receipt":asdict(receipt)})
            failing = receipt
            if state != "WARRANTED":
                last_feedback = reason
            if state == "WARRANTED":
                success = True
                break
        if success:
            checked = (sandbox / "src" / "itsdangerous" / "encoding.py").read_bytes()
            (sandbox / "src" / "itsdangerous" / "encoding.py").write_bytes(
                checked + b"\n# post-test change\n")
            stale = qualify(sandbox, failing, start_sha, EXPANDED_COMMAND)[0]
            if stale != "REJECTED":
                raise AssertionError("POST_TEST_MUTATION_NOT_DETECTED")
            events.append({"step":"post_test_mutation","state":stale})
            (sandbox / "src" / "itsdangerous" / "encoding.py").write_bytes(checked)
            new = execute(sandbox, start_sha, EXPANDED_COMMAND)
            recovered = qualify(sandbox, new, start_sha, EXPANDED_COMMAND)[0]
            if recovered != "WARRANTED":
                raise AssertionError("FRESH_QUALIFICATION_MISSING")
            events.append({"step":"reacquire_exact_receipt","state":recovered,
                           "receipt":asdict(new)})
        return {
            "schema":"mathgraph.nebius.source-native-agent.v1",
            "provider":type(provider).__name__,
            "source":{"repository":"pallets/itsdangerous", "commit":UPSTREAM_COMMIT,
                      "file_blobs":pins, "upstream_bug_claim":False,
                      "injected_mutation":"standard_alphabet"},
            "frozen_experiment":{"domain_count":len(inputs),
                                 "tests_hex":basis["tests_hex"],
                                 "minimum_synthetic_cost":basis["total_synthetic_cost"],
                                 "independent_minimum_cost":
                                     independent_minimum_bound(basis["cover_records"]),
                                 "surviving_mutants":basis["rivals"]},
            "fixed_suite_baseline":native_state,
            "evidence_seeking_detection":discovered,
            "final_state":"WARRANTED" if success else "REJECTED",
            "scope":"source-native pinned mutation repair; only exact declared tests",
            "events":events,
        }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--upstream-checkout", required=True, type=Path)
    p.add_argument("--provider", choices=["scripted","nebius"], default="scripted")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--report", type=Path, default=Path("upstream-agent-report.json"))
    args = p.parse_args()
    provider = ScriptedProvider() if args.provider=="scripted" else NebiusProvider(args.model)
    outcome = perform(args.upstream_checkout.resolve(), provider, args.max_attempts)
    args.report.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"provider":outcome["provider"],
                      "model_attempts":[{"state":e["state"],"model":e.get("model")}
                          for e in outcome["events"] if "attempt" in e],
                      "final_state":outcome["final_state"]},indent=2))
    if outcome["final_state"]!="WARRANTED":
        raise SystemExit(1)

if __name__=="__main__":
    main()
