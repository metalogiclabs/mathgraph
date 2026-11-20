#!/usr/bin/env python3
"""Enumerate every axiom in the selected theorem's lean4export closure.

A separately accepted external checker checks this same NDJSON. This census
does not claim independence of the exporter's dependency-closure algorithm.
"""
import hashlib
import io
import json
import sys
from pathlib import Path

ALLOWED = {"propext", "Classical.choice", "Quot.sound"}

def axiom_records(lines):
    names = {0: ""}
    axioms = []
    meta = None
    records = 0
    for line in lines:
        if not line.strip():
            continue
        records += 1
        record = json.loads(line)
        if "meta" in record:
            if meta is not None:
                raise ValueError("duplicate metadata")
            meta = record["meta"]
        for kind in ("str", "num"):
            if kind in record:
                r = record[kind]
                parent = names.get(r["pre"])
                if parent is None:
                    raise ValueError("unresolved name prefix: " + str(r["pre"]))
                suffix = r["str"] if kind == "str" else str(r["i"])
                names[record["in"]] = (parent + "." if parent else "") + suffix
        if "axiom" in record:
            declaration = record["axiom"]
            if declaration["name"] not in names:
                raise ValueError("unresolved axiom name")
            axioms.append((names[declaration["name"]],
                           bool(declaration["isUnsafe"])))
    if meta is None:
        raise ValueError("missing export metadata")
    return meta, records, axioms

def test_parser():
    fixture = "\n".join(map(json.dumps, [
        {"meta": {"format": {"version": "3.1.0"}}},
        {"str": {"pre": 0, "str": "Classical"}, "in": 1},
        {"str": {"pre": 1, "str": "choice"}, "in": 2},
        {"axiom": {"name": 2, "isUnsafe": False}},
    ]))
    meta, n, actual = axiom_records(io.StringIO(fixture))
    assert meta["format"]["version"] == "3.1.0"
    assert n == 4 and actual == [("Classical.choice", False)]
    try:
        axiom_records(io.StringIO(
            '{"meta":{}}\n{"axiom":{"name":9,"isUnsafe":false}}\n'))
    except ValueError:
        pass
    else:
        raise AssertionError("fail-closed name resolution failed")

def main(path):
    test_parser()
    with path.open(encoding="utf-8") as stream:
        meta, total, observed = axiom_records(stream)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    bad = sorted({name for name, unsafe in observed
                  if name not in ALLOWED or unsafe})
    output = {
        "target": "RHBridge.independentRHIffMathlib",
        "export_sha256": digest,
        "format": meta.get("format", {}).get("version"),
        "records": total,
        "axioms": [{"name": n, "unsafe": unsafe} for n, unsafe in observed],
        "unexpected": bad,
        "assurance_boundary": "con-ron-accepted NDJSON closure; exporter completeness assumed"
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if output["format"] != "3.1.0":
        raise SystemExit("FAIL: unexpected export format")
    if not observed:
        raise SystemExit("FAIL: no exported axiom records")
    if bad:
        raise SystemExit("FAIL: unexpected axiom in exported proof closure")
    print("PASS: only permitted foundational axioms in exported proof closure", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_axioms.py FILE.ndjson")
    main(Path(sys.argv[1]))
