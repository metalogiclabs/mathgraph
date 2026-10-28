#!/usr/bin/env python3
"""Replay two framed research decisions through the actual pinned Metatron log.

This bridge checks lineage and selective withdrawal, not source truth, a human
policy grant, or permission to perform an external action. No new trust kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE_COMMIT = "b9d1b5cc10477188be6e55617699be60e70f6dad"
NUCLEUS_SHA256 = "13f840fa61ef28803a17a7a7266f80e19fdcbdde90703969dbd83f232f44300d"
EXPECTED = {
    "goeth_v19": (
        "b6ee6aee99405607e924b8eba6a6b668522b0c40fdace4c7f0d9ecb3bf2e50cd",
        "metalogiclabs/go-ethereum#19@a04aa77aaebd81d11274560e8d24d90c6f417589",
    ),
    "goccy_pr958": (
        "0f36816614d9b7464a437f60680b663e25783161f9831c2bff6067f912c1736c",
        "goccy/go-yaml#958@a34b94ecb553bb5a693296c30232a89026db79ca",
    ),
}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def load_pinned_nucleus(checkout: Path):
    source = checkout / "runtime" / "metatron" / "nucleus.py"
    require(source.is_file(), "METATRON_SOURCE_UNAVAILABLE")
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    require(actual == NUCLEUS_SHA256, "METATRON_PIN_MISMATCH")
    run = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False, timeout=10,
    )
    require(run.returncode == 0 and run.stdout.strip() == SOURCE_COMMIT,
            "METATRON_PIN_MISMATCH")
    # The source was byte-hashed and commit-pinned *before* importing it.
    sys.path.insert(0, str(checkout))
    from runtime.metatron import nucleus  # type: ignore[import-not-found]

    return nucleus


def live_names(nucleus, log) -> list[str]:
    active = set(nucleus.live_ids(log))
    return [node.payload["label"] for node in log
            if node.id in active and isinstance(node.payload, dict)
            and "label" in node.payload]


def execute(nucleus, data: dict) -> dict:
    require(data.get("schema") == "mathgraph.two-target-replay.v1" and
            data.get("research_only") is True, "INVALID_RESEARCH_SCHEMA")
    cases = data.get("cases")
    require(isinstance(cases, list) and len(cases) == 2 and
            {c.get("id") for c in cases if isinstance(c, dict)} == set(EXPECTED),
            "INVALID_RESEARCH_CASE_SET")
    for case in cases:
        require(case.get("decision") in {"ADMIT", "ABSTAIN", "REFUSE"},
                "INVALID_RESEARCH_DECISION")
        expected_sha, expected_source = EXPECTED[case["id"]]
        require(case.get("frame_sha256") == expected_sha and
                case.get("source") == expected_source,
                "UNPINNED_RESEARCH_SOURCE")

    log = ()
    records = {}
    for case in cases:
        ident = case["id"]
        src = nucleus.Node("source", {
            "label": ident + "_source", "subject": case["source"],
            "frame_sha256": case["frame_sha256"],
            "authority": "RESEARCH_FRAME_ONLY",
        })
        log = nucleus.append(log, src)
        receipt = nucleus.Node("historical_native_receipt", {
            "label": ident + "_receipt", "scope": "PINNED_HISTORICAL_METADATA",
            "native_rerun": False,
        }, (src.id,))
        log = nucleus.append(log, receipt)
        decision = nucleus.Node("derived_research_assessment", {
            "label": ident + "_decision", "decision": case["decision"],
            "external_action_authorization": "NONE",
        }, (receipt.id,))
        log = nucleus.append(log, decision)
        records[ident] = (src, receipt, decision)
    initial = live_names(nucleus, log)

    # Revoking source A removes all dependent records; case B is unrelated.
    log = nucleus.append(log, nucleus.Node("revoke", {
        "target": records["goeth_v19"][0].id,
    }))
    after_first = live_names(nucleus, log)
    # A second, more local withdrawal cuts only case B receipt and decision.
    log = nucleus.append(log, nucleus.Node("revoke", {
        "target": records["goccy_pr958"][1].id,
    }))
    after_second = live_names(nucleus, log)

    history = nucleus.dumps(log)
    cold = nucleus.loads(history)
    require(nucleus.ids(cold) == nucleus.ids(log), "COLD_REPLAY_IDENTITY_MISMATCH")
    require(live_names(nucleus, cold) == after_second,
            "COLD_REPLAY_LIVENESS_MISMATCH")
    return {
        "source_commit": SOURCE_COMMIT, "nucleus_sha256": NUCLEUS_SHA256,
        "initial_live": initial,
        "after_goeth_source_withdrawal": after_first,
        "after_goccy_receipt_withdrawal": after_second,
        "after_cold_restart": live_names(nucleus, cold),
        "history_count": len(log), "history_jsonl": history,
        "history_sha256": hashlib.sha256(history.encode()).hexdigest(),
        "no_external_authorization": True,
    }


def replay(nucleus, data: dict) -> dict:
    require(data.get("schema") == "mathgraph.metatron-cold-replay.v1" and
            isinstance(data.get("history_jsonl"), str), "INVALID_COLD_REPLAY_SCHEMA")
    log = nucleus.loads(data["history_jsonl"])
    history = nucleus.dumps(log)
    require(history == data["history_jsonl"], "COLD_REPLAY_BYTES_CHANGED")
    return {"live_names": live_names(nucleus, log),
            "history_sha256": hashlib.sha256(history.encode()).hexdigest(),
            "history_count": len(log)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True)
    args = parser.parse_args()
    try:
        nucleus = load_pinned_nucleus(Path(args.checkout).resolve())
        raw = sys.stdin.buffer.read(100001)
        require(len(raw) <= 100000, "RESEARCH_INPUT_TOO_LARGE")
        data = json.loads(raw)
        require(isinstance(data, dict), "INVALID_RESEARCH_INPUT")
        result = (replay(nucleus, data) if
                  data.get("schema") == "mathgraph.metatron-cold-replay.v1"
                  else execute(nucleus, data))
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
