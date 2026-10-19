#!/usr/bin/env python3
"""Contract tests for the verifier, not evidence of a repaired upstream L4YAML."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BROKEN = (
    "quoted_42_string", "quoted_true_string", "quoted_true_not_bool",
    "quoted_null_string_option", "quoted_null_struct",
    "distinct_dump_option_values", "round_trip_some_null",
)
POSITIVE = ("plain_null_option", "plain_true_bool", "plain_42_nat", "ordinary_string")
SHA = "a" * 40

def synthetic_log(fixed=False, fault=None):
    # A manufactured acceptance case checks the gate only. It is NOT a repair result.
    checks = {k: fixed for k in BROKEN}
    checks.update({k: True for k in POSITIVE})
    dumps = (
        {"true": "true", "none": "null", "qNone": "x: null",
         "qStringNull": 'x: "null"'}
        if fixed else
        {"true": '"true"', "none": '"null"', "qNone": 'x: "null"',
         "qStringNull": 'x: "null"'}
    )
    if fault == "native":
        checks["quoted_42_string"] = False
    elif fault == "external":
        dumps["none"] = '"null"'
    elif fault == "missing":
        del checks["quoted_42_string"]
    elif fault == "duplicate":
        pass
    records = [f"CHECK:{k}={str(v).lower()}" for k, v in checks.items()]
    if fault == "duplicate":
        records.append("CHECK:plain_null_option=true")
    records += [f"DUMP:{k}={v}" for k, v in dumps.items()]
    return "\n".join(records) + "\n"

def check(log, mode, should_pass):
    with tempfile.TemporaryDirectory() as d:
        raw, receipt = Path(d) / "native.log", Path(d) / "receipt.json"
        raw.write_text(log)
        p = subprocess.run(
            [sys.executable, str(ROOT / "analyze.py"), "--lean-log", str(raw),
             "--out", str(receipt), "--expect", mode, "--upstream-sha", SHA],
            capture_output=True, text=True,
        )
        assert (p.returncode == 0) == should_pass, (
            mode, should_pass, p.stdout, p.stderr
        )
        assert receipt.exists() == should_pass
        if should_pass:
            data = json.loads(receipt.read_text())
            assert data["upstream"] == "nasa-jpl/L4YAML@" + SHA
            assert data["expectation"] == mode
            assert data["source_modified"] is False
            assert data["status"] == (
                "WARRANTED_BOUNDED_FIXED_GREEN"
                if mode == "fixed-green" else "WARRANTED_BOUNDED_ORIGINAL_RED"
            )

check(synthetic_log(False), "original-red", True)
check(synthetic_log(False), "fixed-green", False)
check(synthetic_log(True), "fixed-green", True)
check(synthetic_log(True), "original-red", False)
for fault in ("native", "external", "missing", "duplicate"):
    check(synthetic_log(True, fault), "fixed-green", False)
print("VERIFIER_CONTRACT_TESTS_PASS: original-RED and synthetic-GREEN, four adversarial rejects")
