#!/usr/bin/env python3
"""Assemble a frozen sustained-use transcript from a prompt pack and model responses."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL row in {path} is not an object")
            rows.append(obj)
    return rows


def candidate_from_response(row: dict[str, Any]) -> dict[str, Any]:
    candidate = row.get("candidate")
    if isinstance(candidate, dict):
        return candidate
    raw = str(row.get("raw") or row.get("text") or "").strip()
    if not raw:
        raise ValueError("response requires candidate or raw/text")
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        obj = json.loads(raw[start : end + 1])
        if isinstance(obj, dict):
            return obj
    raise ValueError("response raw/text did not contain a JSON object")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    requests = read_jsonl(args.requests)
    responses = read_jsonl(args.responses)
    by_id = {}
    for row in responses:
        rid = str(row.get("request_id") or "")
        if not rid:
            raise ValueError("every response requires request_id")
        if rid in by_id:
            raise ValueError(f"duplicate response for {rid}")
        by_id[rid] = row

    missing = [row["request_id"] for row in requests if row["request_id"] not in by_id]
    extras = sorted(set(by_id) - {str(row["request_id"]) for row in requests})
    if missing or extras:
        raise ValueError(f"request/response mismatch: missing={missing[:5]} extras={extras[:5]}")

    transcript = []
    models = set()
    token_complete = True
    for request in requests:
        response = by_id[str(request["request_id"])]
        model = str(response.get("model") or "")
        if not model:
            raise ValueError(f"response {request['request_id']} requires model")
        models.add(model)
        usage = response.get("usage") or {}
        if not all(usage.get(k) is not None for k in ("input_tokens", "output_tokens", "total_tokens")):
            token_complete = False
        candidate = candidate_from_response(response)
        raw = str(response.get("raw") or response.get("text") or json.dumps(candidate, sort_keys=True))
        transcript.append(
            {
                "mode": request["mode"],
                "task_id": request["task_id"],
                "model": model,
                "candidate": candidate,
                "raw": raw,
                "usage": usage,
                "latency_ms": response.get("latency_ms"),
                "request_id": request["request_id"],
            }
        )

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    transcript_path = out / "transcript.jsonl"
    transcript_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in transcript),
        encoding="utf-8",
    )
    manifest = {
        "protocol": "MATHGRAPH_EXTERNAL_MODEL_TRANSCRIPT_V1",
        "request_count": len(requests),
        "response_count": len(responses),
        "models": sorted(models),
        "provider_token_usage_complete": token_complete,
        "transcript_sha256": hashlib.sha256(transcript_path.read_bytes()).hexdigest(),
        "claim_boundary": (
            "Assembly validates completeness and freezes responses only. Mathematical correctness "
            "is not established until this transcript is replayed through the independent evaluator."
        ),
    }
    (out / "transcript_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({**manifest, "transcript_path": str(transcript_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
