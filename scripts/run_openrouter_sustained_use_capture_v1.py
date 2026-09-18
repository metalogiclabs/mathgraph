#!/usr/bin/env python3
"""Run the frozen sustained-use prompt pack through OpenRouter.

Default configuration intentionally mirrors SAIR Stage 2's published Gemma route
as closely as the public OpenRouter API permits:
- model: google/gemma-4-31b-it
- provider: DeepInfra only
- temperature: 0
- seed: 0
- JSON-object response format

The script never judges mathematics. It only freezes provider responses, token
usage, latency, requested/resolved model IDs, and provider metadata. MathGraph's
independent replay step decides which candidates are mathematically valid.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it"
DEFAULT_PROVIDER = "deepinfra"


def _parse_candidate(raw: str) -> dict[str, Any]:
    text = raw.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {"invalid_response": text[:2000]}


def _usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage") or {}
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    return {
        "input_tokens": int(prompt) if prompt is not None else None,
        "output_tokens": int(completion) if completion is not None else None,
        "total_tokens": int(total) if total is not None else None,
        "raw_openrouter_usage": usage,
    }


def _call(
    *,
    api_key: str,
    prompt: str,
    model: str,
    provider: str,
    max_tokens: int,
    timeout: float,
    max_attempts: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "provider": {
            "order": [provider],
            "allow_fallbacks": False,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://mathgraph.org",
        "X-Title": "MathGraph Open Math Model Sustained Use V1",
    }

    errors: list[dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
            latency_ms = (time.perf_counter() - started) * 1000.0
            response = json.loads(raw_bytes.decode("utf-8"))
            choices = response.get("choices") or []
            message = choices[0].get("message") if choices else {}
            raw_text = str((message or {}).get("content") or "")
            return {
                "ok": True,
                "attempt": attempt,
                "latency_ms": latency_ms,
                "response": response,
                "raw_text": raw_text,
                "candidate": _parse_candidate(raw_text),
                "usage": _usage(response),
            }
        except urllib.error.HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            errors.append(
                {
                    "attempt": attempt,
                    "kind": "HTTPError",
                    "status": int(exc.code),
                    "detail": detail[:4000],
                    "latency_ms": latency_ms,
                }
            )
            retryable = exc.code in {408, 409, 429, 500, 502, 503, 504}
            if not retryable or attempt >= max_attempts:
                break
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            errors.append(
                {
                    "attempt": attempt,
                    "kind": type(exc).__name__,
                    "detail": str(exc)[:4000],
                    "latency_ms": latency_ms,
                }
            )
            if attempt >= max_attempts:
                break
        time.sleep(min(2 ** (attempt - 1), 8))

    return {
        "ok": False,
        "attempt": len(errors),
        "latency_ms": sum(float(row.get("latency_ms") or 0.0) for row in errors),
        "response": {},
        "raw_text": "",
        "candidate": {"transport_error": errors[-1] if errors else "unknown"},
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "raw_openrouter_usage": {},
        },
        "errors": errors,
    }


def _read_requests(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("request JSONL row is not an object")
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")

    requests_path = Path(args.requests)
    responses_path = Path(args.responses)
    responses_path.parent.mkdir(parents=True, exist_ok=True)

    requests = _read_requests(requests_path)
    out_rows = []
    for index, request in enumerate(requests, start=1):
        prompt = str(request["prompt"])
        result = _call(
            api_key=api_key,
            prompt=prompt,
            model=args.model,
            provider=args.provider,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
        )
        response = result.get("response") or {}
        usage = result["usage"]
        row = {
            "request_id": request["request_id"],
            "mode": request["mode"],
            "task_id": request["task_id"],
            "model": str(response.get("model") or args.model),
            "requested_model": args.model,
            "requested_provider": args.provider,
            "provider": response.get("provider"),
            "generation_id": response.get("id"),
            "candidate": result["candidate"],
            "raw": result["raw_text"],
            "usage": {
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "total_tokens": usage.get("total_tokens"),
            },
            "openrouter_usage": usage.get("raw_openrouter_usage"),
            "latency_ms": result["latency_ms"],
            "attempts": result["attempt"],
            "transport_ok": result["ok"],
            "transport_errors": result.get("errors", []),
        }
        out_rows.append(row)
        print(
            json.dumps(
                {
                    "i": index,
                    "n": len(requests),
                    "request_id": row["request_id"],
                    "transport_ok": row["transport_ok"],
                    "model": row["model"],
                    "provider": row["provider"],
                    "usage": row["usage"],
                    "candidate_keys": sorted(row["candidate"].keys()),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    responses_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in out_rows),
        encoding="utf-8",
    )

    complete_usage = all(
        row["usage"].get("total_tokens") is not None for row in out_rows
    )
    manifest = {
        "protocol": "MATHGRAPH_OPENROUTER_CAPTURE_V1",
        "request_count": len(requests),
        "response_count": len(out_rows),
        "requested_model": args.model,
        "requested_provider": args.provider,
        "temperature": 0,
        "seed": 0,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
        "transport_success_count": sum(bool(row["transport_ok"]) for row in out_rows),
        "transport_failure_count": sum(not bool(row["transport_ok"]) for row in out_rows),
        "provider_token_usage_complete": complete_usage,
        "claim_boundary": (
            "This file freezes OpenRouter responses and provider metadata only. "
            "It makes no mathematical correctness claim. Independent MathGraph replay "
            "must verify every counted terminal result."
        ),
    }
    manifest_path = responses_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["transport_failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
