#!/usr/bin/env python3
"""Reaudit pinned historical native receipts, then apply the unchanged v1 core.

This is an independent *replay of existing evidence*, not a new source-native
PKC or L4YAML execution, new interpretation discovery, or upstream repair.
"""
import argparse
import hashlib
import json
import pathlib

from protocol import Obligation, assess

PKC_SOURCE = "nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824"
YAML_SOURCE = "nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110"
PKC_ARTIFACT = "sha256:8546dfc16783f8243329883e12b7a11f49b6d0c7a3634aaa5293e6c32613cbc6"
YAML_ARTIFACT = "sha256:dbe762c882a78e6e49889a7b81d4cd211e6e52dbc17f506fac420bce4e7f298b"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique(root: pathlib.Path, name: str) -> pathlib.Path:
    matches = [x for x in root.rglob(name) if x.is_file() and x.name == name]
    if len(matches) != 1:
        raise ValueError(f"evidence coverage: {name} appeared {len(matches)} times in {root}")
    return matches[0]


def pkc_observations(root: pathlib.Path) -> dict:
    receipt_file = unique(root, "PINNED_RESULT.json")
    base = receipt_file.parent
    receipt = json.loads(receipt_file.read_text())
    assert receipt["protocol"] == "JPL_PKC_OPENSYSML_FULL_TEXT_V5"
    assert receipt["upstream"] == PKC_SOURCE
    assert receipt["result"] == "WARRANTED_BOUNDED_FULL_TEXT_TO_KERNEL_WITHDRAWAL"
    assert receipt["authentic_SysML_cli"] is True
    assert receipt["converter_retains_optional_claim"] is True
    assert receipt["no_kernel_proof_of_false"] is True
    assert receipt["upstream_writes"] is False
    assert "0.9.1" in receipt["external_converter"]

    for name, expected in receipt["source_input_sha256"].items():
        assert name in ("false_statement.sysml", "no_statement.sysml")
        assert sha((base / name).read_bytes()) == expected
    assert set(receipt["source_input_sha256"]) == {
        "false_statement.sysml", "no_statement.sysml"
    }
    assert 'statement = "False"' in (base / "false_statement.sysml").read_text()
    text = (base / "OriginalFalseGenerated.lean").read_text()
    assert "-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False" in text
    assert "example : False" not in text and "theorem False" not in text
    native = {}
    for line in (base / "native-results.tsv").read_text().splitlines():
        lane, case, status = line.split("\t")
        key = f"{lane}/{case}"
        assert key not in native
        native[key] = int(status)
    expected = {
        "original/no_statement": 0, "original/false_statement": 0,
        "strict/no_statement": 0, "strict/false_statement": 1,
        "withdrawn/false_statement": 0,
    }
    assert set(native) == set(expected)
    assert all((native[k] == 0) == (v == 0) for k, v in expected.items())
    assert receipt["status_by_lane"] == {
        k: "ACCEPT" if v == 0 else "REJECT" for k, v in native.items()
    }
    for key, status in native.items():
        lane, case = key.split("/")
        log = (base / f"{lane}-{case}.log").read_text()
        if status == 0:
            assert "0 unverified citation(s)" in log
        else:
            assert "@Checked.statement is unchecked free text" in log
    api_json = json.loads((base / "convert-false_statement-api.json").read_text())
    vals = [v.get("value") for v in api_json if v.get("@type") == "LiteralString"]
    assert "False" in vals
    assert "PropertyKindCalculus.Iso80000.Part3.Edge.width_length" in vals
    return {"source": receipt["upstream"], "artifact": PKC_ARTIFACT,
            "receipt_sha256": sha(receipt_file.read_bytes()), "native": native}


def yaml_observations(root: pathlib.Path) -> dict:
    receipt_file = unique(root, "receipt.json")
    receipt = json.loads(receipt_file.read_text())
    assert receipt["protocol"] == "L4YAML_STYLE_RED_V1"
    assert receipt["upstream"] == YAML_SOURCE
    assert receipt["source_modified"] is False
    assert receipt["status"] == "WARRANTED_BOUNDED_ORIGINAL_RED"
    lean_log = unique(root, "original-lean.log")
    assert sha(lean_log.read_bytes()) == receipt["lean_stdout_sha256"]
    checks = receipt["native_correctness_checks"]
    bad = {
        "quoted_42_string", "quoted_true_string", "quoted_true_not_bool",
        "quoted_null_string_option", "quoted_null_struct",
        "distinct_dump_option_values", "round_trip_some_null",
    }
    good = {"plain_null_option", "plain_true_bool", "plain_42_nat", "ordinary_string"}
    assert set(checks) == bad | good
    assert all(checks[k] is False for k in bad)
    assert all(checks[k] is True for k in good)
    independent = receipt["independent_checks"]
    assert set(independent) == {
        "bool_true_is_bool_in_both", "none_is_null_in_both",
        "qNone_is_null_in_both", "qStringNull_is_string_in_both",
    }
    assert [independent[k] for k in (
        "bool_true_is_bool_in_both", "none_is_null_in_both",
        "qNone_is_null_in_both", "qStringNull_is_string_in_both"
    )] == [False, False, False, True]
    assert set(receipt["known_original_failures"]) == bad | {
        "bool_true_is_bool_in_both", "none_is_null_in_both", "qNone_is_null_in_both"
    }
    return {"source": receipt["upstream"], "artifact": YAML_ARTIFACT,
            "receipt_sha256": sha(receipt_file.read_bytes()),
            "native_checks": checks, "independent_checks": independent}


def obligations() -> tuple[Obligation, ...]:
    # Source-specific observations live ONLY here, not in the frozen evaluator.
    # PKC 'authoritative' is a HYPOTHESIS while Nicolas's intended contract is open.
    return (
        Obligation("pkc_checked_false_if_authoritative", PKC_SOURCE,
                   "MISMATCH", "ASSERTED", ("pkc_source", "pkc_native", "pkc_contract"),
                   "Conditional on @Checked.statement being an authoritative proposition"),
        Obligation("pkc_checked_false_if_annotation", PKC_SOURCE,
                   "MISMATCH", "ANNOTATION", ("pkc_source", "pkc_native", "pkc_contract"),
                   "The free-text field is explicitly non-authoritative"),
        Obligation("pkc_checked_false_contract_unresolved", PKC_SOURCE,
                   "MISMATCH", "UNRESOLVED", ("pkc_source", "pkc_native"),
                   "No assumption about Nicolas's intended statement semantics"),
        Obligation("pkc_no_statement", PKC_SOURCE,
                   "NO_ASSERTION", "ASSERTED", ("pkc_source", "pkc_native"),
                   "Native ACCEPT, but no attributed proposition was supplied"),
        Obligation("l4yaml_option_collision", YAML_SOURCE,
                   "MISMATCH", "ASSERTED", ("yaml_source", "yaml_native", "yaml_interpretation"),
                   "Typed none and some quoted null have conflated emitted representations"),
        Obligation("l4yaml_ordinary_string", YAML_SOURCE,
                   "MATCH", "ASSERTED", ("yaml_source", "yaml_native", "yaml_interpretation"),
                   "Targeted native positive with shared-schema independent reader"),
        Obligation("l4yaml_unsupported_schema", YAML_SOURCE,
                   "UNSUPPORTED", "ASSERTED", ("yaml_source", "yaml_native"),
                   "No independently declared unsupported schema interpretation"),
    )


def run(pkc_dir: pathlib.Path, yaml_dir: pathlib.Path) -> dict:
    pkc = pkc_observations(pkc_dir)
    yaml = yaml_observations(yaml_dir)
    required = {
        "pkc_source": PKC_SOURCE, "pkc_native": pkc["receipt_sha256"],
        "pkc_contract": "HYPOTHETICAL_AUTHORITATIVE_OR_ANNOTATION",
        "yaml_source": YAML_SOURCE, "yaml_native": yaml["receipt_sha256"],
        "yaml_interpretation": "YAML12_SAFE_COMMON_SCHEMA_SUBSET",
    }
    verdicts = assess(obligations(), required, required)
    assert verdicts == {
        "pkc_checked_false_if_authoritative": "DIVERGENT_BOUNDED",
        "pkc_checked_false_if_annotation": "NO_SEMANTIC_ASSERTION",
        "pkc_checked_false_contract_unresolved": "UNKNOWN_CONTRACT",
        "pkc_no_statement": "NO_SEMANTIC_ASSERTION",
        "l4yaml_option_collision": "DIVERGENT_BOUNDED",
        "l4yaml_ordinary_string": "SCOPED_AGREEMENT",
        "l4yaml_unsupported_schema": "UNKNOWN_INTERPRETATION",
    }
    # Selective premise withdrawal: never promote from a changed or missing digest.
    changed_p = dict(required)
    changed_p["pkc_native"] = "WITHDRAWN"
    after_p = assess(obligations(), changed_p, required)
    assert all(v == "UNKNOWN_WITHDRAWN_OR_CHANGED"
               for k, v in after_p.items() if k.startswith("pkc_"))
    assert all(after_p[k] == v for k, v in verdicts.items() if k.startswith("l4yaml_"))
    changed_y = dict(required)
    changed_y["yaml_interpretation"] = "CHANGED"
    after_y = assess(obligations(), changed_y, required)
    assert all(after_y[k] == "UNKNOWN_WITHDRAWN_OR_CHANGED"
               for k in ("l4yaml_option_collision", "l4yaml_ordinary_string"))
    assert after_y["l4yaml_unsupported_schema"] == verdicts["l4yaml_unsupported_schema"]
    assert all(after_y[k] == v for k, v in verdicts.items() if k.startswith("pkc_"))
    return {
        "protocol": "CROSS_DOMAIN_CORRESPONDENCE_V1",
        "status": "BOUNDED_HISTORICAL_EVIDENCE_REPLAY",
        "source_native_runs_new": 0,
        "artifact_evidence": {"pkc": pkc, "l4yaml": yaml},
        "verdicts": verdicts,
        "pkc_evidence_withdrawn": after_p,
        "yaml_interpretation_changed": after_y,
        "limitations": [
            "No proof that source-neutral core automatically discovers semantic relations.",
            "PKC authoritative statement status is conditional; intended contract remains unresolved.",
            "PKC statement-free positive is not a matching nonempty-statement control.",
            "This job rechecks archived receipts, not native builds or changed upstream sources.",
            "Selective withdrawal in this job mutates dependency tokens, not native source code.",
            "No fixed-GREEN for L4YAML or truthful arbitrary PKC statement has been qualified.",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pkc-artifact", required=True, type=pathlib.Path)
    p.add_argument("--yaml-artifact", required=True, type=pathlib.Path)
    p.add_argument("--output", required=True, type=pathlib.Path)
    a = p.parse_args()
    result = run(a.pkc_artifact, a.yaml_artifact)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("CROSS_DOMAIN_BOUNDED_REPLAY_PASS")
    print(json.dumps(result["verdicts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
