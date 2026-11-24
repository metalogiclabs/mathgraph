#!/usr/bin/env python3
"""Independent Python arithmetic replay of downloaded native Java observations."""
import csv
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPTS = ROOT / "yamcs-consumer-receipts"

def floating(value, bits):
    d = float(value)
    return struct.unpack("!f", struct.pack("!f", d))[0] if bits == 32 else d

def as_bits(value):
    return struct.pack("!d", value)

def fits(n, bits, signed):
    return -(1 << (bits - 1)) <= n < (1 << (bits - 1)) if signed else 0 <= n < (1 << bits)

def check_row(name, row):
    n = int(row["input"])
    actual = row["actual"]
    if name == "integers.tsv":
        admissible = fits(n, int(row["targetBits"]), row["targetSigned"] == "true")
        assert admissible == (row["oracleFits"] == "true")
        match = not admissible if actual.startswith("REJECT:") else admissible and int(actual.split(":")[1]) == n
    elif name == "floats.tsv":
        expected = floating(n, int(row["targetBits"]))
        assert as_bits(expected) == as_bits(float(row["oracle"]))
        match = as_bits(expected) == as_bits(float(actual))
    elif name == "to-long.tsv":
        admissible = 0 <= n <= (1 << 63) - 1
        assert admissible == (row["oracleFitsSignedLong"] == "true")
        match = not admissible if actual.startswith("REJECT:") else admissible and int(actual) == n
    else:
        target = row["target"]
        if target == "float64":
            assert row["oracleFits"] == "true"
            match = not actual.startswith("REJECT:") and as_bits(float(actual)) == as_bits(float(n))
        else:
            signed = target.startswith("signed")
            bits = int(target[6:] if signed else target[8:])
            admissible = fits(n, bits, signed)
            assert admissible == (row["oracleFits"] == "true")
            match = not admissible if actual.startswith("REJECT:") else admissible and int(actual) == n
    assert match == (row["match"] == "true"), (name, row)
    return match

digests = {
    "yamcs-numerics-receipts.zip": "d531eb6d0c57bf173c34003ef7926329249e0f84b1b26385ccd879c0bb0f5883",
    "yamcs-numerics-consumer-receipts.zip": "8f61a67b8aab53df34572790c30f29a0edd6b353e5eb7e7912daaa6789ff597d",
    "antaris-namespace-evidence.zip": "ea0eecf1f808d73b209e72e5e5c693c46411428fff02d6e50d3ee10860ac4851",
    "cosmos-evidence.zip": "f9791f568c835895ba85446453fa224d50c4f5f84eb601f8ba39e9fb5917fe57",
    "sedaro-evidence.zip": "15c255e78d02a3b1f1f16b55a83e189205f030b25fef80cdc02e749f330d699d",
}
for name, expected in digests.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
manifest = json.loads((RECEIPTS / "manifest.json").read_text())
assert set(manifest) == {str(p.relative_to(RECEIPTS)) for p in RECEIPTS.rglob("*") if p.is_file() and p.name != "manifest.json"}
for name, expected in manifest.items():
    assert hashlib.sha256((RECEIPTS / name).read_bytes()).hexdigest() == expected

result = {"archive_hashes": digests, "manifest_entries_verified": len(manifest),
          "oracle": "Python arbitrary-precision integer ranges and IEEE float conversion, separate from Java probe", "matrices": {}}
for name in ["integers.tsv", "floats.tsv", "to-long.tsv", "consumer.tsv"]:
    result["matrices"][name] = {}
    assert (RECEIPTS / "before" / name).read_bytes() == (RECEIPTS / "withdraw" / name).read_bytes()
    for stage in ["before", "after", "withdraw"]:
        rows = list(csv.DictReader((RECEIPTS / stage / name).open(), delimiter="\t"))
        mismatches = sum(not check_row(name, row) for row in rows)
        if stage == "after":
            assert mismatches == 0
        result["matrices"][name][stage] = {"cases": len(rows), "mismatches": mismatches}

for stage, failures in [("before", 4), ("after", 0), ("withdraw", 4)]:
    path = RECEIPTS / stage / "TEST-org.yamcs.mdb.MathGraphNumericalProbeTest.xml"
    e = ET.parse(path).getroot()
    assert int(e.get("tests")) == 4 and int(e.get("failures")) == failures
    assert int(e.get("errors")) == 0 and int(e.get("skipped")) == 0
for stage in ["author-baseline", "after"]:
    total = 0
    for p in (RECEIPTS / stage).glob("TEST-*.xml"):
        if "MathGraph" in p.name:
            continue
        e = ET.parse(p).getroot()
        assert all(int(e.get(x)) == 0 for x in ["failures", "errors", "skipped"])
        total += int(e.get("tests"))
    assert total == 9
result["author_tests"] = 9
result["dependency_jar_hashes_recorded"] = len(json.loads((RECEIPTS / "dependency-sha256.json").read_text()))
(ROOT / "independent-verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
