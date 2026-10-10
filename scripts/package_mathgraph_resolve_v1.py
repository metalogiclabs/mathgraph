#!/usr/bin/env python3
"""Deterministically package exact historical bytes; does not resolve any claims."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "record.json": (5290, "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87"),
    "history.md": (2281, "41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e"),
    "jpl-record.json": (4321, "7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703"),
}


def package(history, record, jpl_record):
    members = {}
    for name, path in {"record.json": record, "history.md": history, "jpl-record.json": jpl_record}.items():
        raw = path.read_bytes()
        size, digest = PINS[name]
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("SOURCE_BYTES_MISMATCH: " + name)
        members[name] = {"encoding": "base64", "data": base64.b64encode(raw).decode("ascii"), "size": size, "sha256": digest}
    bundle = {"schema": "mathgraph.resolve-bundle.v1", "members": members,
              "provenance": {
                  "producer": {"repository": "metalogiclabs/mathgraph", "commit": "040456fc8862c79c8b384ce63846628274b678be", "actions_run": "38025044631"},
                  "prior_independent_replay": {"repository": "heathsanchez/realitygraph", "commit": "9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3", "actions_run": "38025236380", "independently_owned": False}}}
    return (json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", required=True, type=Path)
    parser.add_argument("--record", type=Path, default=ROOT / "evidence/living_warrant_openai_jpl_20261010.json")
    parser.add_argument("--jpl-record", type=Path, default=ROOT / "website/public/evidence/mg-l4yaml-source-check-20261010/record.json")
    parser.add_argument("--out", type=Path, default=ROOT / "conformance/resolve_v1/fixtures/bundle.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        raw = package(args.history, args.record, args.jpl_record)
        if args.check:
            if args.out.read_bytes() != raw:
                raise ValueError("BUNDLE_BYTES_MISMATCH")
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(raw)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
    print("BUNDLE_SHA256=" + hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
