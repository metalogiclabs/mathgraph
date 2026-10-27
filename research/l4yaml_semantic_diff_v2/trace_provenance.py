"""Independently qualify scanner-to-raw-tree anchor-event order on finite inputs.

The scanner and AST projections are both executed by the pinned original
L4YAML source. This verifier only checks observed order; it cannot certify
unique semantic source traces when the source grammar itself is ambiguous.
"""
import argparse
import hashlib
import json
from pathlib import Path


def check(ok, msg):
    if not ok:
        raise ValueError(msg)


def main():
    ap = argparse.ArgumentParser()
    for field in ("oracle", "anchor", "ordinary", "special", "report"):
        ap.add_argument("--" + field, type=Path, required=True)
    ap.add_argument("--source-sha", required=True)
    args = ap.parse_args()
    check(len(args.source_sha) == 40 and
          all(c in "0123456789abcdef" for c in args.source_sha), "INVALID_SHA")
    oracle = json.loads(args.oracle.read_text())
    expected = oracle["cases"]
    check(len(expected) == 532, "ORACLE_SCOPE_DRIFT")
    actual = []
    digests = {}
    for suite, path in (("anchor", args.anchor), ("ordinary", args.ordinary)):
        rows = [json.loads(x) for x in path.read_text().splitlines() if x]
        control = [x for x in expected if x["suite"] == suite]
        check(len(rows) == len(control), "TRUNCATED_NATIVE_" + suite)
        for source, row in zip(control, rows):
            check(row["input"] == source["input"], "INPUT_ORDER_DRIFT")
            check(set(row) == {"input", "status", "scanner", "raw_tree"},
                  "NATIVE_RECORD_SHAPE_DRIFT")
            check(type(row["scanner"]) is list and
                  type(row["raw_tree"]) is list, "BAD_EVENT_SEQUENCE")
            check(all(type(x) is str for x in row["scanner"] + row["raw_tree"]),
                  "BAD_EVENT_TYPE")
            actual.append(row)
        digests[suite] = hashlib.sha256(path.read_bytes()).hexdigest()
    baseline = sum(x["status"] == "MATCH" for x in actual)
    disagreements = [
        {"suite": source["suite"], "family": source["family"],
         "input": source["input"],
         "scanner": row["scanner"], "raw_tree": row["raw_tree"],
         "status": row["status"]}
        for source, row in zip(expected, actual) if row["status"] != "MATCH"
    ]

    special = [json.loads(x) for x in args.special.read_text().splitlines() if x]
    expected_special = {
        "&x [*x]": "MATCH",
        "&x {a: *x}": "MATCH",
        "[&x [&x 1], *x]": "MATCH",
        "[&x 1, *x, &x 9, *x]": "MATCH",
        "[*x]": "REFUSED",
        "&x [*x, *y]": "REFUSED",
        "---\n&x 1\n---\n*x\n": "REFUSED",
    }
    check({r["input"] for r in special} == set(expected_special),
          "SPECIAL_INPUT_DRIFT")
    for row in special:
        check(row["status"] == expected_special[row["input"]],
              "SPECIAL_SOURCE_ORDER_OR_REFUSAL_CHANGED:" + repr(row["input"]))

    result = {
        "source": args.source_sha,
        "method": "original L4YAML Scanner.scanFiltered tokens versus original parseYamlRaw AST",
        "total": 532,
        "matched": baseline,
        "mismatched": 532 - baseline,
        "examples": disagreements[:20],
        "special": {r["input"]: r["status"] for r in special},
        "native_sha256": digests,
        "oracle_sha256": hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
        "scope": "anchor/alias event order in finite native corpus only",
        "whole_source_trace_uniqueness": "UNKNOWN",
        "trace_to_graph_general_semantics": "UNKNOWN",
        "release_authority": "NOT_AUTHORIZED",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                     sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("total", "matched", "mismatched")},
                     sort_keys=True))
    check(baseline == 532, "FINITE_SOURCE_TO_AST_EVENT_ORDER_MISMATCH")


if __name__ == "__main__":
    main()
