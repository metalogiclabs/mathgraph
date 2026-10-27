"""Eight source-native schema controls, distinct from the 532 JSON-path cases.

This is a finite regression receipt for the typed `parseTyped` API; it is not a
theorem about all YAML scalars. Two independently pinned parsers supply values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import warnings

from research.l4yaml_semantic_diff_v2.differential import (
    PYYAML_WHEEL_SHA256, check_installed_oracle_composer,
    check_installed_pyyaml_module, digest, require, require_wheel,
    strict_json, verify_source,
)

CASES = (
    ("quoted_true", 'k: "true"\n'),
    ("plain_true", "k: true\n"),
    ("quoted_null", 'k: "null"\n'),
    ("plain_null", "k: null\n"),
    ("quoted_42", 'k: "42"\n'),
    ("plain_42", "k: 42\n"),
    ("explicit_str", "k: !!str true\n"),
    ("explicit_bool", "k: !!bool 'true'\n"),
)


def typed_value(value) -> dict:
    if type(value) is str:
        return {"kind": "str", "value": value}
    if type(value) is bool:
        return {"kind": "bool", "value": value}
    if value is None:
        return {"kind": "null", "value": None}
    if type(value) is int:
        return {"kind": "int", "value": value}
    raise ValueError("SCHEMA_VALUE_UNSUPPORTED")


def verify_native_rows(expected: list[dict], rows: list[str]) -> dict:
    require(len(rows) == len(expected) == len(CASES), "SCHEMA_ROW_COUNT_MISMATCH")
    for (case_name, case_source), oracle, line in zip(CASES, expected, rows):
        require(oracle == {"input": case_source, "result": oracle.get("result")},
                "ORACLE_CASE_IDENTITY_MISMATCH")
        row = strict_json(line)
        require(type(row) is dict and set(row) == {"input", "result"}
                and row["input"] == case_source, "NATIVE_CASE_IDENTITY_MISMATCH")
        observed_result, expected_result = row["result"], oracle["result"]
        require(type(observed_result) is dict and set(observed_result) == {"kind", "value"}
                and type(observed_result["value"]) is type(expected_result["value"])
                and observed_result == expected_result,
                f"SCHEMA_VALUE_MISMATCH:{case_name}")
    return {"cases": len(CASES), "matched": len(CASES), "mismatched": 0}


def independent_typed_oracles(wheel: Path, ruamel_path: Path, pyyaml_wheel: Path,
                               pyyaml_path: Path) -> list[dict]:
    require_wheel(wheel)
    check_installed_oracle_composer(wheel.read_bytes(),
                                    (ruamel_path / "ruamel/yaml/composer.py").read_bytes())
    require(digest(pyyaml_wheel.read_bytes()) == PYYAML_WHEEL_SHA256,
            "SECOND_PARSER_WHEEL_SHA256_MISMATCH")
    check_installed_pyyaml_module(
        pyyaml_wheel.read_bytes(),
        (pyyaml_path / "yaml/constructor.py").read_bytes(),
        (pyyaml_path / "yaml/loader.py").read_bytes(),
    )
    sys.path.insert(0, str(ruamel_path.resolve()))
    sys.path.insert(0, str(pyyaml_path.resolve()))
    from ruamel.yaml import YAML
    import ruamel.yaml
    import yaml
    require(ruamel.yaml.__version__ == "0.18.17" and yaml.__version__ == "6.0.3",
            "INDEPENDENT_PARSER_VERSION_DRIFT")
    ruamel = YAML(typ="safe", pure=True)
    ruamel.version = (1, 2)
    expected = []
    for name, source in CASES:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            value_a = ruamel.load(source)["k"]
        value_b = yaml.safe_load(source)["k"]
        require(typed_value(value_a) == typed_value(value_b),
                f"SCHEMA_INDEPENDENT_ORACLES_DISAGREE:{name}")
        expected.append({"input": source, "result": typed_value(value_a)})
    return expected


def verified_report(native: Path, checkout: Path, lean: Path, sha: str,
                    wheel: Path, ruamel_path: Path, pyyaml_wheel: Path,
                    pyyaml_path: Path) -> dict:
    source = verify_source(checkout, lean, sha)
    expected = independent_typed_oracles(wheel, ruamel_path, pyyaml_wheel, pyyaml_path)
    raw = native.read_bytes()
    require(raw.endswith(b"\n") and raw, "SCHEMA_NATIVE_LOG_INCOMPLETE")
    records = verify_native_rows(expected, raw.decode("utf-8").splitlines())
    return {
        "schema": "mathgraph.check.l4yaml.typed-schema-controls.v1",
        "status": "BOUNDED_TYPED_SCHEMA_AGREEMENT",
        "source": source,
        "native": records,
        "cases": [name for name, _ in CASES],
        "independent_parsers": ["ruamel.yaml@0.18.17", "PyYAML@6.0.3"],
        "native_jsonl_sha256": digest(raw),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "authority": "LOCAL_SOURCE_NATIVE_OBSERVATION_ONLY",
        "decision_authority": "NOT_AUTHORIZED",
        "boundary": "8 source-native parseTyped scalars at one exact L4YAML revision; not a proof",
    }


def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("native", "checkout", "lean", "expected-head", "wheel", "ruamel-path",
                 "pyyaml-wheel", "pyyaml-path", "out"):
        p.add_argument("--" + flag, required=True, type=str if flag == "expected-head" else Path)
    args = p.parse_args(argv)
    try:
        report = verified_report(args.native, args.checkout, args.lean, args.expected_head,
                                 args.wheel, args.ruamel_path, args.pyyaml_wheel,
                                 args.pyyaml_path)
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        report = {"status": "UNKNOWN", "error": f"{type(exc).__name__}: {exc}",
                  "decision_authority": "NOT_AUTHORIZED"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "cases": report.get("native")}))
    return 0 if report["status"] == "BOUNDED_TYPED_SCHEMA_AGREEMENT" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
