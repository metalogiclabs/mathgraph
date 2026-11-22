"""Independent finite status reference; no subject or renderer code is executed.

The selected PASS/FAIL/SKIP display policy counts direct error and failure
children as FAIL. Pytest's JUnit producer distinguishes those from passing tests:
https://github.com/pytest-dev/pytest/blob/13ba5cba07f56728d25d89cc7f5f0b24b06c3b95/src/_pytest/junitxml.py
ElementTree provides XML structure, not authority for that finite display policy.
This observer does not claim full JUnit dialect or renderer conformance.
"""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def observe(xml):
    root = ET.fromstring(xml)
    rows = []
    for case in root.iter("testcase"):
        # find() selects direct children. An empty <error/> is still an outcome;
        # text, comments, CDATA and nested metadata are not direct outcome tags.
        if case.find("error") is not None or case.find("failure") is not None:
            status, css = "FAIL", "fail"
        elif case.find("skipped") is not None:
            status, css = "SKIP", "skip"
        else:
            status, css = "PASS", "pass"
        rows.append([
            case.get("classname", "") + "." + case.get("name", ""),
            status, css, case.get("time", "0"),
        ])
    total = len(rows)
    passed = sum(row[1] == "PASS" for row in rows)
    failed = sum(row[1] == "FAIL" for row in rows)
    skipped = sum(row[1] == "SKIP" for row in rows)
    return {
        "accepted": True,
        "rows": rows,
        "count": total,
        "summary": {"total": total, "passed": passed, "failed": failed,
                    "skipped": skipped, "css": "fail" if failed else "pass"},
    }


def main(output):
    runner = Path(__file__)
    corpus = runner.with_name("report-status-cases.json").read_bytes()
    cases = json.loads(corpus)
    records = []
    for case in cases:
        observed = observe(case["input"])
        if observed != case["expected"]:
            raise ValueError("REFERENCE_EXPECTATION_MISMATCH: " + case["id"])
        records.append({"id": case["id"], "observed": observed})
    result = {
        "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256(corpus).hexdigest(),
        "records": records,
    }
    Path(output).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 report-status-reference.py OUTPUT_JSON")
    main(sys.argv[1])
