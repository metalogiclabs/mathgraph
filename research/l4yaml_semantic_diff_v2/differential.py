"""Independent finite differential check of two L4YAML JSON paths.

The native result is observed behavior, not a proof that the YAML 1.2 model
is complete. Caller authority comes from a clean pinned upstream checkout,
native Lean execution, and a wheel-hash-qualified external YAML oracle.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
import warnings
import zipfile

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph

WHEEL_SHA256 = "9c8ba9eb3e793efdf924b60d521820869d5bf0cb9c6f1b82d82de8295e290b9d"
PYYAML_WHEEL_SHA256 = "ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
REPO = "https://github.com/nasa-jpl/L4YAML"
VALUES = ("1", "2", "word", "true", "null")
SCALARS = ("1", "-2", "true", "false", "null", "word", '"true"', '"null"',
           '"42"', "'line'", '"héllo"', "0xFF")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def reject_unreplayed_commit(receipt_head: str, requested_head: str) -> bool:
    for sha in (receipt_head, requested_head):
        require(isinstance(sha, str) and bool(re.fullmatch(r"[0-9a-f]{40}", sha)),
                "NOT_AN_IMMUTABLE_COMMIT")
    return receipt_head != requested_head


def anchor_patterns(name: str, value: str) -> dict[str, str]:
    a, r = "&" + name, "*" + name
    return {
        "nested_sequence": f"[{a} [{a} {value}], {r}]",
        "nested_mapping": f"[{a} {{k: {a} {value}}}, {r}]",
        "deep_nested": f"[{a} [{a} [{a} {value}]], {r}]",
        "internal_alias_external": f"[{a} [{a} {value}, {r}], {r}]",
        "two_outer_aliases": f"[{a} [{a} {value}], {r}, {r}]",
        "sibling_after_nested": f"[{a} [{a} {value}], {a} 9, {r}]",
        "nested_siblings": f"[{a} [{a} {value}], [{a} 9], {r}]",
        "mapping_internal_alias": f"[{a} {{k: {a} {value}, z: {r}}}, {r}]",
        "mapping_outer_sibling": f"{{a: {a} {{k: {a} {value}}}, b: {r}}}",
        "ordinary_rebinding": f"[{a} {value}, {r}, {a} 9, {r}]",
        "ordinary_simple": f"[{a} {value}, {r}]",
        "plain_without_alias": f"[{value}, [{name}, 9]]",
    }


def ordinary_patterns(a: str, b: str, c: str) -> dict[str, str]:
    return {
        "plain_scalar": a + "\n",
        "flow_sequence": f"[{a}, {b}, {c}]\n",
        "flow_nested": f"[[{a}], {{k: {b}}}, {c}]\n",
        "flow_mapping": f"{{alpha: {a}, beta: {b}, gamma: {c}}}\n",
        "block_sequence": f"- {a}\n- {b}\n- {c}\n",
        "block_mapping": f"alpha: {a}\nbeta: {b}\ngamma:\n  - {c}\n",
        "block_nested": f"root:\n  k: {a}\n  list:\n    - {b}\n    - {c}\n",
        "mixed_block": f"- k: {a}\n  m: {b}\n- q: {c}\n",
        "quoted_key_map": f'{{"null": {a}, "true": {b}, "42": {c}}}\n',
        "nested_keys": f"{{outer: {{inner: {a}}}, sample: [{b}, {c}]}}\n",
    }


SPECIALS = {
    "literal_block": "k: |\n  line one\n  line two\n",
    "folded_block": "k: >\n  line one\n  line two\n",
    "strip_block": "k: |-\n  trailing\n",
    "keep_block": "k: |+\n  line\n\n",
    "explicit_string": "k: !!str true\n",
    "explicit_number": "k: !!int '42'\n",
    "explicit_bool": "k: !!bool 'true'\n",
    "explicit_null": "k: !!null 'null'\n",
    "empty_sequence": "[]\n",
    "empty_mapping": "{}\n",
    "nested_empty": "[{}, [], {a: []}]\n",
    "empty_value": "k:\n",
    "empty_document": "---\n...\n",
    "unicode_double_quote": 'k: "雪 ☃ é"\n',
    "escaped_newline": 'k: "line\\nnext"\n',
    "escaped_tab": 'k: "a\\tb"\n',
}


def generate_cases() -> tuple[list[dict], list[dict]]:
    alias = [
        {"suite": "anchor", "family": family, "anchor": name, "value": value, "input": source}
        for name in ("x", "oak", "a") for value in VALUES
        for family, source in anchor_patterns(name, value).items()
    ]
    candidates = [
        {"suite": "ordinary", "family": family, "offset": offset, "scalar": a, "input": source}
        for offset in (1, 3, 7) for i, a in enumerate(SCALARS)
        for family, source in ordinary_patterns(a, SCALARS[(i + offset) % len(SCALARS)],
                                               SCALARS[(i + 2 * offset) % len(SCALARS)]).items()
    ]
    candidates += [
        {"suite": "ordinary", "family": family, "offset": 0, "scalar": "special", "input": source}
        for family, source in SPECIALS.items()
    ]
    ordinary, seen = [], set()
    for item in candidates:
        if item["input"] not in seen:
            seen.add(item["input"])
            ordinary.append(item)
    require(len(alias) == 180 and len(ordinary) == 352, "GENERATED_GRAMMAR_SIZE_DRIFT")
    require(len({c["input"] for c in alias + ordinary}) == 532, "DUPLICATE_GENERATED_INPUT")
    return alias, ordinary


def strict_json(text: str):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    def constant(value):
        raise ValueError("UNSUPPORTED_NON_JSON_CONSTANT:" + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def classify_native(oracle_cases: list[dict], native_lines: list[str]) -> dict:
    require(len(oracle_cases) == len(native_lines), "INCOMPLETE_NATIVE_ROWS")
    matches = 0
    mismatches = 0
    divergences = 0
    by_suite: dict[str, dict] = {}
    by_family: dict[str, dict] = {}
    examples: dict[str, list] = {}
    renaming = {}
    for expected, line in zip(oracle_cases, native_lines):
        require(isinstance(expected.get("input"), str) and "expected" in expected,
                "INVALID_ORACLE_CASE")
        row = strict_json(line)
        require(type(row) is dict and set(row) == {"input", "legacy", "indexed"}
                and row["input"] == expected["input"], "NATIVE_CASE_ORDER_OR_IDENTITY_MISMATCH")
        results = []
        for mode in ("legacy", "indexed"):
            result = row[mode]
            require(type(result) is dict and result.get("status") in {"ok", "error"},
                    "INVALID_NATIVE_STAGE")
            if result["status"] == "ok":
                require(set(result) == {"status", "value"} and type(result["value"]) is str,
                        "INVALID_NATIVE_JSON_VALUE")
                results.append(strict_json(result["value"]))
            else:
                require(set(result) == {"status", "error"} and type(result["error"]) is str
                        and result["error"], "INVALID_NATIVE_ERROR")
                results.append({"native_refusal": result["error"]})
        agrees = all(result == expected["expected"] for result in results)
        matches += agrees
        mismatches += not agrees
        divergences += results[0] != results[1]
        suite = expected["suite"]
        family = f"{suite}.{expected['family']}"
        for target, key in ((by_suite, suite), (by_family, family)):
            counter = target.setdefault(key, {"matched": 0, "mismatched": 0})
            counter["matched" if agrees else "mismatched"] += 1
        if not agrees and len(examples.setdefault(family, [])) < 2:
            examples[family].append({"input": expected["input"], "oracle": expected["expected"],
                                     "legacy": results[0], "indexed": results[1]})
        if suite == "anchor" and expected["family"] != "plain_without_alias":
            group = (family, expected["value"])
            renaming.setdefault(group, []).append(results[0])
    # The three anchor-name substitutions should never change the semantics.
    renaming_residuals = [
        {"family": family, "value": value}
        for (family, value), results in sorted(renaming.items())
        if len(results) != 3 or any(r != results[0] for r in results[1:])
    ]
    return {"cases": len(native_lines), "matched": matches, "mismatched": mismatches,
            "legacy_indexed_disagreement": divergences, "by_suite": by_suite,
            "by_family": by_family, "examples": examples,
            "anchor_renaming_residuals": renaming_residuals}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_wheel(path: Path) -> str:
    actual = digest(path.read_bytes())
    require(actual == WHEEL_SHA256, "INDEPENDENT_ORACLE_WHEEL_MISMATCH")
    return actual


def check_installed_oracle_composer(wheel_bytes: bytes, installed_composer: bytes) -> None:
    """Reject a same-version package whose interpretation code differs from the wheel."""
    try:
        with zipfile.ZipFile(BytesIO(wheel_bytes)) as archive:
            trusted_composer = archive.read("ruamel/yaml/composer.py")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("ORACLE_WHEEL_MISSING_COMPOSER") from exc
    require(installed_composer == trusted_composer, "ORACLE_COMPOSER_BYTES_CHANGED")


def check_installed_pyyaml_module(wheel_bytes: bytes, constructor: bytes, loader: bytes) -> None:
    """Bind the second parser's relevant modules to its exact installed wheel."""
    try:
        with zipfile.ZipFile(BytesIO(wheel_bytes)) as archive:
            trusted_constructor = archive.read("yaml/constructor.py")
            trusted_loader = archive.read("yaml/loader.py")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("SECOND_PARSER_WHEEL_UNAVAILABLE") from exc
    require(constructor == trusted_constructor and loader == trusted_loader,
            "SECOND_PARSER_BYTES_CHANGED")


def corroborate_ordinary_with_pyyaml(qualified: list[dict]) -> int:
    """Independent cross-check on the exact safe subset, not general YAML 1.2."""
    import yaml
    require(yaml.__version__ == "6.0.3", "SECOND_PARSER_VERSION_DRIFT")
    matched = 0
    for case in qualified:
        require(case["suite"] == "ordinary", "SECOND_PARSER_SCOPE_WIDENED")
        try:
            observed = yaml.safe_load(case["input"])
        except yaml.YAMLError as exc:
            raise ValueError("SECOND_PARSER_REFUSED_ORDINARY_CASE") from exc
        require(observed == case["expected"], "SECOND_PARSER_DISAGREES")
        matched += 1
    return matched


def independent_oracle(cases: list[dict], package_path: Path) -> list[dict]:
    sys.path.insert(0, str(package_path.resolve()))
    from ruamel.yaml import YAML
    import ruamel.yaml
    require(ruamel.yaml.__version__ == "0.18.17", "INDEPENDENT_ORACLE_VERSION_DRIFT")
    engine = YAML(typ="safe", pure=True)
    engine.version = (1, 2)
    rows = []
    for item in cases:
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            try:
                expected = engine.load(item["input"])
            except Exception as exc:
                raise ValueError("INDEPENDENT_ORACLE_CANNOT_PARSE:" + item["input"]) from exc
        rows.append({**item, "expected": expected,
                     "oracle_warnings": [type(w.message).__name__ for w in observed]})
    return rows


def encode_inputs(cases: list[dict]) -> bytes:
    return "".join(json.dumps(c["input"], ensure_ascii=False) + "\n" for c in cases).encode()


def write_generated(out: Path, wheel: Path, package_path: Path,
                    pyyaml_wheel: Path | None = None, pyyaml_package_path: Path | None = None) -> dict:
    require_wheel(wheel)
    check_installed_oracle_composer(wheel.read_bytes(),
                                    (package_path / "ruamel/yaml/composer.py").read_bytes())
    alias, ordinary = generate_cases()
    qualified = independent_oracle(alias + ordinary, package_path)
    corroboration = None
    require((pyyaml_wheel is None) == (pyyaml_package_path is None), "INCOMPLETE_SECOND_PARSER_PIN")
    if pyyaml_wheel is not None:
        require(digest(pyyaml_wheel.read_bytes()) == PYYAML_WHEEL_SHA256,
                "SECOND_PARSER_WHEEL_SHA256_MISMATCH")
        check_installed_pyyaml_module(
            pyyaml_wheel.read_bytes(),
            (pyyaml_package_path / "yaml/constructor.py").read_bytes(),
            (pyyaml_package_path / "yaml/loader.py").read_bytes(),
        )
        sys.path.insert(0, str(pyyaml_package_path.resolve()))
        corroboration = {"package": "PyYAML", "version": "6.0.3",
                         "wheel_sha256": PYYAML_WHEEL_SHA256,
                         "ordinary_cases_agreed": corroborate_ordinary_with_pyyaml(qualified[len(alias):]),
                         "scope": "Only the 352 selected ordinary YAML inputs; duplicate-anchor inputs excluded"}
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, cases in (("anchor", alias), ("ordinary", ordinary)):
        data = encode_inputs(cases)
        (out / f"{name}_inputs.jsonl").write_bytes(data)
        hashes[name] = digest(data)
    record = {"schema": "mathgraph.l4yaml.generated-source-native.v2",
              "input_manifest_sha256": hashes, "oracle_wheel_sha256": WHEEL_SHA256,
              "oracle_version": "0.18.17", "second_parser": corroboration, "cases": qualified}
    (out / "independent_oracle.json").write_text(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                                           indent=2, allow_nan=False) + "\n")
    return record


def verify_source(checkout: Path, lean: Path, expected_head: str) -> dict:
    reject_unreplayed_commit(expected_head, expected_head)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=checkout)
    observed = git("rev-parse", "HEAD").decode().strip()
    require(observed == expected_head, "SOURCE_COMMIT_MISMATCH")
    require(git("status", "--porcelain", "--untracked-files=no") == b"", "DIRTY_UPSTREAM_TRACKED_SOURCE")
    require((checkout / "lean-toolchain").read_text().strip() == TOOLCHAIN, "LEAN_TOOLCHAIN_MISMATCH")
    version = subprocess.check_output([str(lean), "--version"]).decode().strip()
    require("4.35.0" in version, "LEAN_RUNTIME_MISMATCH")
    files = {}
    for path in ("L4YAML/Spec/Types.lean", "L4YAML/Output/Json.lean", "L4YAML/Output/JsonIx.lean"):
        raw = (checkout / path).read_bytes()
        require(raw == git("show", f"HEAD:{path}"), "CHANGED_NATIVE_SOURCE_FILE")
        files[path] = {"sha256": digest(raw), "git_blob": git("rev-parse", f"HEAD:{path}").decode().strip()}
    return {"repository": REPO, "commit": observed, "lean_toolchain": TOOLCHAIN,
            "lean_version": version, "lean_binary_sha256": digest(lean.read_bytes()),
            "source_files": files}


def verified_report(
    root: Path, wheel: Path, package_path: Path, checkout: Path, lean: Path,
    expected_head: str, current_head: str,
    pyyaml_wheel: Path | None = None, pyyaml_package_path: Path | None = None,
) -> dict:
    require_wheel(wheel)
    source = verify_source(checkout, lean, expected_head)
    generated = write_generated(root / "reconstructed", wheel, package_path,
                                pyyaml_wheel, pyyaml_package_path)
    original = strict_json((root / "independent_oracle.json").read_text())
    require(original == generated, "ORACLE_EXPECTATION_TAMPERED")
    for name in ("anchor", "ordinary"):
        require((root / f"{name}_inputs.jsonl").read_bytes()
                == (root / "reconstructed" / f"{name}_inputs.jsonl").read_bytes(),
                "GENERATED_CASES_CHANGED")
    native_by_suite = {}
    for name in ("anchor", "ordinary"):
        stderr = (root / f"{name}_stderr.log").read_bytes()
        require(stderr == b"", "NATIVE_STDERR_NOT_EMPTY")
        raw = (root / f"{name}_native.jsonl").read_bytes()
        require(raw.endswith(b"\n") and raw, "INCOMPLETE_NATIVE_LOG")
        try:
            lines = raw.decode("utf-8").splitlines()
        except UnicodeError as exc:
            raise ValueError("INVALID_NATIVE_UTF8") from exc
        reference = [c for c in generated["cases"] if c["suite"] == name]
        native_by_suite[name] = classify_native(reference, lines)
    all_disagreements = sum(v["legacy_indexed_disagreement"] for v in native_by_suite.values())
    all_renaming = [x for v in native_by_suite.values() for x in v["anchor_renaming_residuals"]]
    original_scope = f"nasa-jpl/L4YAML@{expected_head}:source"
    native_scope = f"nasa-jpl/L4YAML@{expected_head}:532-native-cases"
    claims = [Claim("source_identity", "documentary", original_scope),
              Claim("ordinary_native_agreement", "formal", native_scope),
              Claim("anchor_differential_observed", "formal", native_scope)]
    receipts = [Receipt("source", "documentary", original_scope),
                *[Receipt(x, "formal", native_scope) for x in ("source_binding", "native", "oracle", "verifier")]]
    routes = [Route("source_identity", ("source",))]
    if native_by_suite["ordinary"]["mismatched"] == 0 and all_disagreements == 0:
        routes.append(Route("ordinary_native_agreement", ("source_binding", "native", "oracle", "verifier")))
    if native_by_suite["anchor"]["mismatched"] > 0:
        routes.append(Route("anchor_differential_observed", ("source_binding", "native", "oracle", "verifier")))
    withdrawn = frozenset(r.id for r in receipts) if reject_unreplayed_commit(expected_head, current_head) else frozenset()
    states = resolve_graph(claims, routes, receipts, withdrawn=withdrawn).states
    return {
        "schema": "mathgraph.check.l4yaml.semantic-differential.v2",
        "status": "BOUNDED_DIFFERENTIAL_OBSERVED" if not withdrawn else "UNKNOWN",
        "source": {**source, "current_head": current_head},
        "total": sum(v["cases"] for v in native_by_suite.values()),
        "matched": sum(v["matched"] for v in native_by_suite.values()),
        "mismatched": sum(v["mismatched"] for v in native_by_suite.values()),
        "legacy_indexed_disagreement": all_disagreements,
        "anchor_renaming_residuals": all_renaming,
        "second_parser": generated["second_parser"],
        "suites": native_by_suite,
        "claims": dict(states),
        "decision_authority": "NOT_AUTHORIZED",
        "mathematical_terminal_form": None,
        "evidence_sha256": {
            "oracle": digest((root / "independent_oracle.json").read_bytes()),
            "anchor_inputs": digest((root / "anchor_inputs.jsonl").read_bytes()),
            "ordinary_inputs": digest((root / "ordinary_inputs.jsonl").read_bytes()),
            "anchor_native": digest((root / "anchor_native.jsonl").read_bytes()),
            "ordinary_native": digest((root / "ordinary_native.jsonl").read_bytes()),
            "verifier": digest(Path(__file__).read_bytes()),
        },
        "boundary": "532 acyclic generated examples; no whole-language proof, no hardware or JPL endorsement",
    }


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("generate", "verify"):
        p = sub.add_parser(action)
        p.add_argument("--root", required=True, type=Path)
        p.add_argument("--wheel", required=True, type=Path)
        p.add_argument("--package-path", required=True, type=Path)
        p.add_argument("--pyyaml-wheel", type=Path)
        p.add_argument("--pyyaml-package-path", type=Path)
        if action == "verify":
            p.add_argument("--checkout", required=True, type=Path)
            p.add_argument("--lean", required=True, type=Path)
            p.add_argument("--expected-head", required=True)
            p.add_argument("--current-head", required=True)
            p.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.action == "generate":
        record = write_generated(args.root, args.wheel, args.package_path,
                                 args.pyyaml_wheel, args.pyyaml_package_path)
        print(json.dumps({"status": "GENERATED_INDEPENDENT_ORACLE", "cases": len(record["cases"]),
                          "input_sha256": record["input_manifest_sha256"]}))
        return 0
    try:
        report = verified_report(args.root, args.wheel, args.package_path, args.checkout,
                                 args.lean, args.expected_head, args.current_head,
                                 args.pyyaml_wheel, args.pyyaml_package_path)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        report = {"schema": "mathgraph.check.l4yaml.semantic-differential.v2",
                  "status": "UNKNOWN", "error": f"{type(exc).__name__}: {exc}",
                  "decision_authority": "NOT_AUTHORIZED"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False,
                                         allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "total": report.get("total"),
                      "matched": report.get("matched"), "mismatched": report.get("mismatched"),
                      "error": report.get("error"), "report": str(args.out)}))
    return 0 if report["status"] == "BOUNDED_DIFFERENTIAL_OBSERVED" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
