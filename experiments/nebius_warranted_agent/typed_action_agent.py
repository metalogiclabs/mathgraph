"""Typed finite repair selection through Nebius Nemotron.

The model chooses a constrained intervention. A deterministic local compiler
produces the patch; independent pinned upstream tests, not model prose,
determine bounded qualification. This is NOT unrestricted code generation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib import request

from upstream_encoding_transfer import digest
from upstream_nebius_agent import (
    DEFAULT_MODEL, ENDPOINT, Proposal, perform, validate_function,
)

ENCODERS = ("urlsafe_b64encode", "b64encode")
PADDING = ("strip", "retain")
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "encoder": {"type": "string", "enum": list(ENCODERS)},
        "padding": {"type": "string", "enum": list(PADDING)},
    },
    "required": ["encoder", "padding"],
    "additionalProperties": False,
}


def compile_typed_action(action: object) -> str:
    """Four possible patches, without ever interpreting model code."""
    if not isinstance(action, dict) or set(action) != {"encoder", "padding"}:
        raise ValueError("MODEL_ACTION_WRONG_SCHEMA")
    encoder, padding = action["encoder"], action["padding"]
    if encoder not in ENCODERS or padding not in PADDING:
        raise ValueError("MODEL_ACTION_OUTSIDE_GRAMMAR")
    tail = '.rstrip(b"=")' if padding == "strip" else ""
    source = (
        "def base64_encode(string: str | bytes) -> bytes:\n"
        "    string = want_bytes(string)\n"
        f"    return base64.{encoder}(string){tail}\n"
    )
    validate_function(source)
    return source


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ScriptedTypedProvider:
    """Offline ablation, never claims external model inference."""
    def __init__(self) -> None:
        self.actions: list[dict] = []

    def propose(self, current: str, evidence: list[tuple[str, str]],
                attempt: int) -> Proposal:
        action = {"encoder": "b64encode", "padding": "retain"} if attempt == 1 else {
            "encoder": "urlsafe_b64encode", "padding": "strip"
        }
        source = compile_typed_action(action)
        meta = {"attempt": attempt, "action": action,
                "compiler_output_sha256": digest(source.encode()),
                "provider": "SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS"}
        self.actions.append(meta)
        return Proposal(source, meta["provider"], "none", digest(json.dumps(action,
                        sort_keys=True).encode()), None, utc())


class NebiusTypedProvider:
    """Live typed choice; authenticated response is untrusted until native tests."""
    def __init__(self, model: str = DEFAULT_MODEL):
        key = os.environ.get("NEBIUS_API_KEY")
        if not key:
            raise RuntimeError("NEBIUS_API_KEY_NOT_CONFIGURED")
        if not model.startswith("nvidia/"):
            raise ValueError("NVIDIA_OPEN_MODEL_REQUIRED")
        self._key = key
        self.model = model
        self.actions: list[dict] = []

    def propose(self, current: str, evidence: list[tuple[str, str]],
                attempt: int) -> Proposal:
        if not 1 <= attempt <= 2:
            raise ValueError("MODEL_ATTEMPT_OUT_OF_BUDGET")
        messages = [
            {"role": "system", "content":
             "You are selecting a bounded, safe code-repair action, not writing code. "
             "Return ONLY a JSON object with keys encoder and padding. "
             "encoder must be one of 'urlsafe_b64encode' or 'b64encode'. "
             "padding must be 'strip' or 'retain'. "
             "A separate deterministic compiler applies your action. "
             "Independent native Python tests determine acceptance."},
            {"role": "user", "content":
             "A Python package's base64_encode(str or bytes) currently fails "
             "contract-derived examples. Choose a repair action that makes "
             "URL-safe Base64 encoding produce unpadded bytes while preserving "
             "str-to-bytes conversion.\n"
             f"Current code:\n{current}\n"
             f"Observed counterexamples as input/required-output hex: "
             f"{json.dumps(evidence, separators=(',', ':'))}\n"
             f"Attempt: {attempt}. Reply with only the two-field JSON action."},
        ]
        body = {
            "model": self.model, "messages": messages,
            "temperature": 0.1, "max_tokens": 512,
            "chat_template_kwargs": {"enable_thinking": False},
            "guided_json": ACTION_SCHEMA,
            "response_format": {"type": "json_object"},
        }
        req = request.Request(
            ENDPOINT, data=json.dumps(body, sort_keys=True).encode(),
            method="POST", headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self._key,
            })
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read(1_048_576)
                header_id = response.headers.get("x-request-id")
        except Exception as exc:
            # No exception details, URL, headers, or API response text in logs.
            raise RuntimeError("NEBIUS_INFERENCE_UNVERIFIED:"
                               + type(exc).__name__) from None
        try:
            result = json.loads(raw)
            if result.get("model") and result["model"] != self.model:
                raise ValueError("NEBIUS_MODEL_ID_MISMATCH")
            choice = result["choices"][0]
            text = choice["message"].get("content")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("NEBIUS_EMPTY_TYPED_RESPONSE")
            if choice.get("finish_reason") not in ("stop", None):
                raise ValueError("NEBIUS_TYPED_RESPONSE_INCOMPLETE")
            action = json.loads(text)
            source = compile_typed_action(action)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ValueError("NEBIUS_ACTION_RESPONSE_MALFORMED") from None

        request_id = str(header_id or result.get("id") or "") or None
        hash_ = digest(raw)
        self.actions.append({
            "attempt": attempt,
            "action": action,
            "compiler_output_sha256": digest(source.encode()),
            "provider": "nebius-token-factory",
            "model": self.model,
            "request_id": request_id,
            "response_sha256": hash_,
        })
        return Proposal(source, "nebius-token-factory", self.model,
                        hash_, request_id, utc())


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout", required=True, type=Path)
    p.add_argument("--provider", choices=("scripted", "nebius"), default="scripted")
    p.add_argument("--max-attempts", type=int, default=2)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--report", type=Path,
                   default=Path("upstream-typed-agent-report.json"))
    args=p.parse_args()
    if not 1 <= args.max_attempts <= 2:
        p.error("typed agent is bounded to at most two attempts")
    provider = (ScriptedTypedProvider() if args.provider=="scripted"
                else NebiusTypedProvider(args.model))
    report=perform(args.upstream_checkout.resolve(), provider, args.max_attempts)
    report["typed_repair_actions"]=provider.actions
    report["repair_semantics"]=(
        "Model chooses a two-field constrained action; local compiler creates "
        "exact function source; independently executed source-native pytest "
        "qualifies only declared tests. This is not arbitrary code generation."
    )
    args.report.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
    print(json.dumps({
        "provider": report["provider"],
        "final_state": report["final_state"],
        "action_choices": [
            {"attempt":x["attempt"],"action":x["action"],"model":x.get("model")}
            for x in provider.actions],
    },indent=2))
    if report["final_state"] != "WARRANTED":
        raise SystemExit(1)


if __name__=="__main__":
    main()
