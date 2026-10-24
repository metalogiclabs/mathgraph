"""Verify 13 exact source-native L4YAML cases against literal independent semantics.

Exit 0 means a bounded native classification was obtained: all five known
defects reproduced, some repaired, or all five repaired. Five independent
controls and the undefined-alias refusal must still pass. This is never a
whole-language correctness or theorem certificate. Cycle policy is excluded.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

TOOLCHAIN = "leanprover/lean4:v4.35.0"
WHEEL_SHA = "9c8ba9eb3e793efdf924b60d521820869d5bf0cb9c6f1b82d82de8295e290b9d"
ROOT = pathlib.Path(__file__).resolve().parent
CASES = [
    ("same-name-seq", "[&x [&x 1], *x]", [[1], 1], "defect"),
    ("same-name-seq-both-aliases", "[&x [&x 1, *x], *x]", [[1, 1], 1], "defect"),
    ("same-name-map", "a: &x {b: &x 1}\nc: *x\n", {"a": {"b": 1}, "c": 1}, "defect"),
    ("same-name-map-both-aliases", "a: &x {b: &x 1, c: *x}\nd: *x\n", {"a": {"b": 1, "c": 1}, "d": 1}, "defect"),
    ("sibling-rebind", "[&x 1, *x, &x 2, *x]", [1, 1, 2, 2], "control"),
    ("nested-distinct", "[&o [&x 1], *x, *o]", [[1], 1, [1]], "control"),
    ("noalias-same-name", "[&x [&x 1]]", [[1]], "control"),
    ("same-name-string", "[&x [&x inner], *x]", [["inner"], "inner"], "defect"),
    ("single-anchor", "[&x 1, *x]", [1, 1], "control"),
    ("no-alias", "[1,[2]]", [1, [2]], "control"),
    ("selfcycle-policy", "&x [*x]", None, "cycle_policy"),
    ("rebound-selfcycle-policy", "[&x 0, &x [*x]]", None, "cycle_policy"),
    ("undefined-alias-control", "[*missing]", None, "refusal"),
]
DOC_STAGES = ("raw", "composed", "public_load", "indexed_raw", "indexed_load")
STRING_STAGES = ("json", "indexed_json", "events")
FIELDS = {"case", "input", *DOC_STAGES, *STRING_STAGES}


class VerificationError(Exception):
    pass


def require(test, message):
    if not test:
        raise VerificationError(message)


def pairs_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def invalid_constant(value):
    raise VerificationError(f"non-JSON numeric constant: {value}")


def loads(text):
    return json.loads(text, object_pairs_hook=pairs_object, parse_constant=invalid_constant)


def scalar(value, anchor=None):
    return {"kind": "scalar", "content": str(value), "anchor": anchor, "tag": None}


def seq(items, anchor=None):
    return {"kind": "sequence", "items": items, "anchor": anchor, "tag": None}


def mapping(pairs, anchor=None):
    return {"kind": "mapping", "pairs": pairs, "anchor": anchor, "tag": None}


def alias(name="x"):
    return {"kind": "alias", "name": name}


# Literal source trees, independently read from the small fixed YAML inputs.
# There is no parser, alias interpretation, or implementation-derived model here.
RAW = {
    "same-name-seq": seq([seq([scalar(1, "x")], "x"), alias()]),
    "same-name-seq-both-aliases": seq([seq([scalar(1, "x"), alias()], "x"), alias()]),
    "same-name-map": mapping([[scalar("a"), mapping([[scalar("b"), scalar(1, "x")]], "x")], [scalar("c"), alias()]]),
    "same-name-map-both-aliases": mapping([[scalar("a"), mapping([[scalar("b"), scalar(1, "x")], [scalar("c"), alias()]], "x")], [scalar("d"), alias()]]),
    "sibling-rebind": seq([scalar(1, "x"), alias(), scalar(2, "x"), alias()]),
    "nested-distinct": seq([seq([scalar(1, "x")], "o"), alias(), alias("o")]),
    "noalias-same-name": seq([seq([scalar(1, "x")], "x")]),
    "same-name-string": seq([seq([scalar("inner", "x")], "x"), alias()]),
    "single-anchor": seq([scalar(1, "x"), alias()]),
    "no-alias": seq([scalar(1), seq([scalar(2)])]),
}


def canonical_shape(value):
    if type(value) is int or isinstance(value, str):
        return scalar(value)
    if isinstance(value, list):
        return seq([canonical_shape(v) for v in value])
    if isinstance(value, dict):
        return mapping([[scalar(k), canonical_shape(v)] for k, v in value.items()])
    raise VerificationError(f"unexpected JSON type in acyclic case: {type(value).__name__}")


def validate_shape(value):
    require(isinstance(value, dict), "node shape is not an object")
    kind = value.get("kind")
    fields = {
        "scalar": {"kind", "content", "anchor", "tag"},
        "sequence": {"kind", "items", "anchor", "tag"},
        "mapping": {"kind", "pairs", "anchor", "tag"},
        "alias": {"kind", "name"},
    }
    require(kind in fields and set(value) == fields[kind], "invalid node fields")
    if kind == "alias":
        require(isinstance(value["name"], str), "alias name is not a string")
        return
    for field in ("anchor", "tag"):
        require(value[field] is None or isinstance(value[field], str), f"invalid {field}")
    if kind == "scalar":
        require(isinstance(value["content"], str), "scalar content is not a string")
    elif kind == "sequence":
        require(isinstance(value["items"], list), "sequence items is not a list")
        for item in value["items"]:
            validate_shape(item)
    else:
        require(isinstance(value["pairs"], list), "mapping pairs is not a list")
        for pair in value["pairs"]:
            require(isinstance(pair, list) and len(pair) == 2, "invalid mapping pair")
            for item in pair:
                validate_shape(item)


def read_native(path):
    text = path.read_text()
    require(text and text.endswith("\n"), "empty or non-newline-terminated native log")
    lines = text.splitlines()
    require(len(lines) == len(CASES), f"native line count {len(lines)} != {len(CASES)}")
    rows = {}
    for number, line in enumerate(lines, 1):
        require(line.strip(), f"blank native line {number}")
        row = loads(line)
        require(isinstance(row, dict) and set(row) == FIELDS, f"invalid row fields at line {number}")
        name = row["case"]
        require(isinstance(name, str) and name not in rows, f"duplicate or invalid case: {name}")
        rows[name] = row
        for stage in DOC_STAGES + STRING_STAGES:
            result = row[stage]
            require(isinstance(result, dict), f"{name}/{stage}: result is not an object")
            status = result.get("status")
            require(status in ("ok", "error"), f"{name}/{stage}: missing/invalid status")
            if status == "error":
                require(set(result) == {"status", "error"}, f"{name}/{stage}: invalid error fields")
                require(isinstance(result["error"], str) and result["error"], f"{name}/{stage}: empty error")
            elif stage in DOC_STAGES:
                require(set(result) == {"status", "values"}, f"{name}/{stage}: invalid values fields")
                require(isinstance(result["values"], list), f"{name}/{stage}: values not list")
                for value in result["values"]:
                    validate_shape(value)
            else:
                require(set(result) == {"status", "value"}, f"{name}/{stage}: invalid string fields")
                require(isinstance(result["value"], str) and result["value"], f"{name}/{stage}: empty string")
    require(set(rows) == {c[0] for c in CASES}, "native case membership mismatch")
    for name, source, _, _ in CASES:
        require(rows[name]["input"] == source, f"{name}: source input mismatch")
    return rows


def check_oracle(path):
    oracle = loads(path.read_text())
    require(oracle.get("package") == "ruamel.yaml" and oracle.get("version") == "0.18.17", "oracle package mismatch")
    require(oracle.get("wheel_sha256") == WHEEL_SHA and oracle.get("composer_matches_wheel") is True, "oracle provenance mismatch")
    rows = oracle.get("acyclic_cases")
    require(isinstance(rows, list) and len(rows) == 16, "oracle case count mismatch")
    expected = {(mode, name): (source, value) for name, source, value, _ in CASES[:8] for mode in ("safe", "rt")}
    seen = set()
    for row in rows:
        key = (row.get("mode"), row.get("name"))
        require(key in expected and key not in seen, f"oracle duplicate/unknown case: {key}")
        seen.add(key)
        source, value = expected[key]
        require(row.get("input") == source, f"oracle input mismatch: {key}")
        require(row.get("expected") == value and row.get("actual") == value and row.get("agrees") is True, f"oracle value mismatch: {key}")
    require(seen == set(expected), "missing oracle cases")
    return {"package": oracle["package"], "version": oracle["version"], "wheel_sha256": WHEEL_SHA, "acyclic_cases": 16, "independent_implementations": 1}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True).stdout


def provenance(checkout, lean, expected_head):
    head = command(["git", "rev-parse", "HEAD"], checkout).decode().strip()
    require(len(expected_head) == 40 and all(c in "0123456789abcdef" for c in expected_head), "invalid immutable source commit")
    require(head == expected_head, f"checkout pin mismatch: {head}")
    require(not command(["git", "status", "--porcelain", "--untracked-files=no"], checkout), "tracked checkout files modified")
    require((checkout / "lean-toolchain").read_text().strip() == TOOLCHAIN, "toolchain declaration mismatch")
    version = command([str(lean), "--version"]).decode().strip()
    require("4.35.0" in version, "runtime Lean version mismatch")
    paths = ["lean-toolchain", "L4YAML/Spec/Types.lean", "L4YAML/Parser/TokenParser.lean", "L4YAML/Parser/TokenParserIx.lean", "L4YAML/Parser/Composition.lean", "L4YAML/Parser/IndexedComposition.lean", "L4YAML/Output/Json.lean", "L4YAML/Output/JsonIx.lean", "L4YAML/Proofs/Serialization/SerializationWellFormed.lean"]
    files = {}
    for path in paths:
        working = (checkout / path).read_bytes()
        committed = command(["git", "show", f"HEAD:{path}"], checkout)
        require(working == committed, f"source differs from commit: {path}")
        files[path] = {"sha256": hashlib.sha256(working).hexdigest(), "git_blob": command(["git", "rev-parse", f"HEAD:{path}"], checkout).decode().strip()}
    return {"repository": "https://github.com/nasa-jpl/L4YAML", "commit": head, "tracked_checkout_clean": True, "toolchain": TOOLCHAIN, "lean_version": version, "lean_binary_sha256": sha(lean), "source_files": files}


def verify(args):
    receipt = {"status": "REPRODUCER_VERIFICATION_FAILED", "errors": [], "scope": "Bounded native alias-value reproduction; exit 0 means defects reproduced, not L4YAML correctness", "cycle_policy_boundary": "Cycle cases are observations only and excluded from acyclic conformance counts", "shape_boundary": "Kind/content/anchor/tag and child order; style, block metadata, positions, comments and general graph identity are outside this probe", "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        rows = read_native(args.native)
        receipt["source"] = provenance(args.checkout, args.lean, args.expected_head)
        receipt["oracle"] = check_oracle(args.oracle)
        require(args.stderr.read_bytes() == b"", "native stderr is nonempty")
        receipt["cases"] = []
        defects, controls, cycles, refusals = [], [], [], []
        for name, source, expected, category in CASES:
            row = rows[name]
            result = {"case": name, "input": source, "category": category}
            if category in ("defect", "control"):
                for stage in DOC_STAGES + STRING_STAGES:
                    require(row[stage]["status"] == "ok", f"{name}/{stage}: unexpected refusal")
                require(row["raw"]["values"] == [RAW[name]], f"{name}: raw source tree differs from literal expected structure")
                require(row["indexed_raw"] == row["raw"], f"{name}: raw pipeline disagreement")
                require(row["composed"] == row["public_load"] == row["indexed_load"], f"{name}: direct compose/public/indexed disagreement")
                actual = loads(row["json"]["value"])
                actual_ix = loads(row["indexed_json"]["value"])
                require(actual == actual_ix, f"{name}: JSON pipelines disagree")
                require(row["public_load"]["values"] == [canonical_shape(actual)], f"{name}: JSON value disagrees with composed node shape")
                shape_agrees = row["public_load"]["values"] == [canonical_shape(expected)]
                agrees = actual == expected
                require(shape_agrees == agrees, f"{name}: shape/JSON mismatch classification differs")
                require(category != "control" or agrees, f"{name}: declared control unexpectedly disagrees")
                (controls if agrees else defects).append(name)
                result.update({"expected": expected, "actual": actual, "indexed_actual": actual_ix, "agrees": agrees, "raw_structure_verified": True, "both_raw_pipelines_agree": True, "direct_compose_public_indexed_agree": True, "json_matches_composed_shape": True, "events_observed": row["events"]["value"], "expected_basis": "native ruamel.yaml safe+rt and YAML1.2.2" if name in {c[0] for c in CASES[:8]} else "literal anchor/control semantics"})
            elif category == "refusal":
                for stage in DOC_STAGES + STRING_STAGES:
                    require(row[stage]["status"] == "error", f"{name}/{stage}: undefined alias accepted")
                    require("undefined alias" in row[stage]["error"].lower() and "missing" in row[stage]["error"], f"{name}/{stage}: wrong refusal category")
                refusals.append(name)
                result.update({"refused_at_all_stages": True, "observed_errors": {s: row[s]["error"] for s in DOC_STAGES + STRING_STAGES}})
            else:
                cycles.append(name)
                result.update({"classification": "GRAPH_POLICY_OBSERVATION_NOT_ACYCLIC_CONFORMANCE_FAILURE", "observed_stages": {s: row[s] for s in DOC_STAGES + STRING_STAGES}})
            receipt["cases"].append(result)
        require(len(controls) == 5 and len(cycles) == 2 and len(refusals) == 1, "final category counts mismatch")
        receipt["counts"] = {"native_rows": len(rows), "acyclic_cases": 10, "defects_reproduced_both_pipelines": len(defects), "acyclic_controls_passed_both_pipelines": len(controls), "cycle_policy_observations": len(cycles), "undefined_alias_controls_refused": len(refusals)}
        receipt["defect_cases"] = defects
        receipt["control_cases"] = controls
        receipt["status"] = (
            "BOUNDED_DEFECT_REPRODUCED" if len(defects) == 5
            else "BOUNDED_FIX_OBSERVED" if len(defects) == 0
            else "BOUNDED_PARTIAL_DEFECT"
        )
        receipt["upstream_build_boundary"] = "Runtime target build and native process exit0 observed by parent runner; this verifier independently checks complete structured logs, exact source pin, compiler version, source hashes and empty stderr. Full proof suite not replayed."
    except (VerificationError, ValueError, OSError, subprocess.CalledProcessError) as e:
        receipt["errors"].append(f"{type(e).__name__}: {e}")
    receipt["artifact_sha256"] = {str(p.name): sha(p) for p in [args.native, args.oracle, args.stderr, ROOT / "Probe.lean", pathlib.Path(__file__)] if p.is_file()}
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "counts": receipt.get("counts"), "errors": receipt["errors"], "receipt": str(args.output)}))
    return 0 if receipt["status"] in {
        "BOUNDED_DEFECT_REPRODUCED", "BOUNDED_FIX_OBSERVED", "BOUNDED_PARTIAL_DEFECT",
    } else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=pathlib.Path, default=ROOT / "native_results.jsonl")
    parser.add_argument("--oracle", type=pathlib.Path, default=ROOT / "oracle_results.json")
    parser.add_argument("--stderr", type=pathlib.Path, default=ROOT / "native_stderr.log")
    parser.add_argument("--checkout", type=pathlib.Path, default=pathlib.Path("/tmp/l4yaml-native-20261024"))
    parser.add_argument("--lean", type=pathlib.Path, default=pathlib.Path("/tmp/lean-4.35.0-linux/bin/lean"))
    parser.add_argument("--expected-head", required=True, help="40-hex immutable upstream commit required for every native replay")
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "verification_receipt.json")
    sys.exit(verify(parser.parse_args()))
