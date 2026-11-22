#!/usr/bin/env python3
"""Prospective claim/evidence probe runner; does not discover hypotheses itself."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

def sha(data):
    return hashlib.sha256(data).hexdigest()

def execute(command, cwd, timeout):
    started = time.monotonic()
    try:
        p = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout, check=False)
        return {"kind": "EXECUTED", "exit": p.returncode,
                "stdout_sha256": sha(p.stdout), "stderr_sha256": sha(p.stderr),
                "stdout": p.stdout.decode("utf-8", errors="replace"),
                "stderr": p.stderr.decode("utf-8", errors="replace"),
                "seconds": round(time.monotonic() - started, 3)}
    except subprocess.TimeoutExpired as e:
        return {"kind": "UNKNOWN", "reason": "TIMEOUT",
                "stdout_sha256": sha(e.stdout or b""), "stderr_sha256": sha(e.stderr or b"")}
    except OSError as e:
        return {"kind": "UNKNOWN", "reason": type(e).__name__}

def evaluate(spec, cwd, timeout):
    observations = []
    for case in spec["cases"]:
        actual = execute(case["command"], cwd, timeout)
        expected = case["expected"]
        if actual["kind"] != "EXECUTED":
            status = "UNKNOWN"
        elif actual["exit"] != expected["exit"]:
            status = "DISCREPANCY"
        elif "stdout_sha256" in expected and actual["stdout_sha256"] != expected["stdout_sha256"]:
            status = "DISCREPANCY"
        elif "stderr_sha256" in expected and actual["stderr_sha256"] != expected["stderr_sha256"]:
            status = "DISCREPANCY"
        else:
            status = "AGREEMENT"
        observations.append({"id": case["id"], "status": status, "actual": actual})
    return observations

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True, help="Expected full 40-hex commit SHA")
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error("timeout outside 1..600")
    out = Path(args.out)
    if out.exists():
        parser.error("output already exists")
    spec_bytes = Path(args.spec).read_bytes()
    spec = json.loads(spec_bytes)
    if spec.get("schema") != "mathgraph.prospective-probes.v0":
        parser.error("unsupported schema")
    cases = spec.get("cases")
    if not isinstance(cases, list) or not cases:
        parser.error("nonempty cases required")
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids):
        parser.error("duplicate case IDs")
    for c in cases:
        if (not isinstance(c.get("command"), list) or not c["command"]
            or not all(isinstance(x, str) and x for x in c["command"])
            or not isinstance(c.get("expected", {}).get("exit"), int)):
            parser.error("invalid case")
    cwd = Path(args.repo).resolve()
    revision = execute(["git", "rev-parse", "HEAD"], str(cwd), args.timeout)
    if revision["kind"] != "EXECUTED" or revision["exit"] != 0:
        parser.error("source revision unavailable")
    if len(args.revision) != 40 or any(ch not in "0123456789abcdef" for ch in args.revision) or revision["stdout"].strip() != args.revision:
        parser.error("source revision does not match frozen target")
    dirty = execute(["git", "status", "--porcelain"], str(cwd), args.timeout)
    if dirty["kind"] != "EXECUTED" or dirty["exit"] != 0 or dirty["stdout"].strip():
        parser.error("repository must be clean")
    results = evaluate(spec, str(cwd), args.timeout)
    after = execute(["git", "rev-parse", "HEAD"], str(cwd), args.timeout)
    after_dirty = execute(["git", "status", "--porcelain"], str(cwd), args.timeout)
    source_stable = (after["kind"] == "EXECUTED" and after["exit"] == 0 and
                     after["stdout"].strip() == args.revision and
                     after_dirty["kind"] == "EXECUTED" and after_dirty["exit"] == 0 and
                     not after_dirty["stdout"].strip())
    status = ("UNKNOWN" if not source_stable or any(r["status"] == "UNKNOWN" for r in results)
              else "DISCREPANCIES" if any(r["status"] == "DISCREPANCY" for r in results)
              else "BOUNDED_AGREEMENT")
    out.mkdir(parents=True)
    receipt = {"schema": "mathgraph.prospective-receipt.v0", "status": status,
               "source_revision": revision["stdout"].strip(), "source_stable": source_stable,
               "spec_sha256": sha(spec_bytes),
               "cases": results, "blindness": "NOT_ESTABLISHED",
               "novelty": "UNKNOWN", "model_calls": 0,
               "boundary": "Operator-supplied commands and expected observations only; no hypothesis generation"}
    (out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "source_revision": receipt["source_revision"], "cases": len(results)}))
    return 2 if status == "UNKNOWN" else 1 if status == "DISCREPANCIES" else 0

if __name__ == "__main__":
    raise SystemExit(main())
