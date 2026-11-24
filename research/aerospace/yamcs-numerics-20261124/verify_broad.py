#!/usr/bin/env python3
"""Separate arithmetic and JUnit replay of all downloaded paired reactor receipts."""
import collections
import csv
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
BASE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
PROBE = "org.yamcs.mdb.MathGraphNumericalProbeTest"
REQUIRED = {"org.yamcs.mdb.UnsignedComparisonTest", "org.yamcs.mdb.DataEncodingUtilsTest",
            "org.yamcs.mdb.DataTypeProcessorTest", "org.yamcs.xtce.IntegerDataTypeTest"}

def fits(n, width, signed):
    return -(1 << (width - 1)) <= n < (1 << (width - 1)) if signed else 0 <= n < (1 << width)

def bits(d):
    return struct.pack("!d", d)

def replay(name, row):
    n = int(row["input"])
    actual = row["actual"]
    if name == "integers.tsv":
        ok = fits(n, int(row["targetBits"]), row["targetSigned"] == "true")
        assert ok == (row["oracleFits"] == "true")
        match = not ok if actual.startswith("REJECT:") else ok and int(actual.split(":")[1]) == n
    elif name == "floats.tsv":
        expected = float(n)
        if row["targetBits"] == "32":
            expected = struct.unpack("!f", struct.pack("!f", expected))[0]
        assert bits(expected) == bits(float(row["oracle"]))
        match = bits(expected) == bits(float(actual))
    elif name == "to-long.tsv":
        ok = 0 <= n <= (1 << 63) - 1
        assert ok == (row["oracleFitsSignedLong"] == "true")
        match = not ok if actual.startswith("REJECT:") else ok and int(actual) == n
    elif row["target"] == "float64":
        match = not actual.startswith("REJECT:") and bits(float(actual)) == bits(float(n))
    else:
        target = row["target"]
        signed = target.startswith("signed")
        width = int(target[6:] if signed else target[8:])
        ok = fits(n, width, signed)
        assert ok == (row["oracleFits"] == "true")
        match = not ok if actual.startswith("REJECT:") else ok and int(actual) == n
    assert match and row["match"] == "true", (name, row)

def inventory(directory):
    cases, required = [], set()
    for p in directory.glob("*/TEST-*.xml"):
        e = ET.parse(p).getroot()
        assert int(e.get("failures")) == 0 and int(e.get("errors")) == 0, str(p)
        if e.get("name") in REQUIRED:
            assert int(e.get("tests")) > 0 and int(e.get("skipped")) == 0
            required.add(e.get("name"))
        for t in e.findall("testcase"):
            assert t.find("failure") is None and t.find("error") is None
            state = "skipped" if t.find("skipped") is not None else "passed"
            cases.append((p.parent.name, t.get("classname"), t.get("name"), state))
    assert required == REQUIRED, (required, str(directory))
    assert len(cases) > 9
    return cases

results = []
for jdk in ["17", "21", "25"]:
    root = BASE / ("yamcs-broad-jdk-" + jdk)
    manifest = json.loads((root / "manifest.json").read_text())
    assert set(manifest) == {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "manifest.json"}
    for name, digest in manifest.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    assert (root / "source.txt").read_text().strip() == "4af5abd2b5d8535f77e902de717c77d657f0093e"
    assert (root / "upstream-restored.txt").read_text().strip() == (root / "source.txt").read_text().strip()
    baseline = inventory(root / "baseline")
    repair = inventory(root / "repair")
    original = [x for x in repair if x[1] != PROBE]
    probe = [x for x in repair if x[1] == PROBE]
    assert collections.Counter(baseline) == collections.Counter(original)
    assert len(probe) == 4 and all(x[3] == "passed" for x in probe)
    counts = {}
    for name, count in [("integers.tsv", 1512), ("floats.tsv", 168), ("to-long.tsv", 21), ("consumer.tsv", 50)]:
        rows = list(csv.DictReader((root / "repair" / name).open(), delimiter="\t"))
        assert len(rows) == count, name
        for row in rows:
            replay(name, row)
        counts[name] = count
    for stage in ["baseline", "repair"]:
        summary = json.loads((root / stage / "summary.json").read_text())
        assert summary["exit"] == 0
    results.append({"jdk": jdk, "manifest_entries_verified": len(manifest),
                    "original_cases": len(baseline), "original_passed": sum(x[3] == "passed" for x in baseline),
                    "original_skipped": sum(x[3] == "skipped" for x in baseline),
                    "new_probe_tests": 4, "native_matrices_independently_replayed": counts})
receipt = {"status": "INDEPENDENT_REPLAY_PASS", "boundary": "same default selected core reactor on Linux, three JDKs; outside repository modules and operational behavior unassessed", "results": results}
(OUT / "independent-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2), flush=True)
