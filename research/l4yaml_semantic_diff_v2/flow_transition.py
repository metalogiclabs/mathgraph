"""Compare exact scanner acceptance observations across two L4YAML commits.

The 19 finite inputs come from the public PR #89 guard suite. The report
distinguishes native behavioral transitions from independent YAML parser
agreement: parser implementations are not substitutes for YAML grammar proofs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import warnings

from research.l4yaml_semantic_diff_v2.differential import (
    PYYAML_WHEEL_SHA256, check_installed_oracle_composer,
    check_installed_pyyaml_module, digest, require, require_wheel,
    strict_json, verify_source,
)

CASES = (
    ("plain_glued", "{a:[1]}"),
    ("plain_glued", "[a:[1]]"),
    ("plain_glued", "{a:{b: c}}"),
    ("plain_glued", "[a:{b: c}]"),
    ("plain_glued", "{a:[]}"),
    ("plain_glued", "{a:{}}"),
    ("plain_glued", "{a :[1]}"),
    ("empty_key_glued", "{:[1]}"),
    ("empty_key_glued", "[:[1]]"),
    ("explicit_key_glued", "{? a :[1]}"),
    ("explicit_key_glued", "[? a :[1]]"),
    ("json_key_adjacent", '{"a":b}'),
    ("json_key_adjacent", '{"a":[1]}'),
    ("json_key_adjacent", "{'a':{b: c}}"),
    ("json_key_adjacent", "{[a]:[1]}"),
    ("separated_or_plain", "{a: [1]}"),
    ("separated_or_plain", "{a:b}"),
    ("separated_or_plain", '{a:"x"}'),
    ("separated_or_plain", "a: [1]"),
)


def classify_rows(lines: list[str]) -> list[dict]:
    require(len(lines) == len(CASES), "FLOW_ROW_COUNT_MISMATCH")
    out = []
    for (family, source), line in zip(CASES, lines):
        row = strict_json(line)
        require(type(row) is dict and set(row) == {"input", "legacy", "indexed"}
                and row["input"] == source, "FLOW_CASE_ORDER_OR_IDENTITY_MISMATCH")
        require(type(row["legacy"]) is bool and type(row["indexed"]) is bool,
                "FLOW_NATIVE_BOOLEAN_REQUIRED")
        out.append({"family": family, **row})
    return out


def summarize_transition(baseline: list[dict], candidate: list[dict]) -> dict:
    require(len(baseline) == len(candidate) == len(CASES), "FLOW_TRANSITION_SHAPE_MISMATCH")
    counts = {"accepted_to_refused": 0, "accepted_to_accepted": 0,
              "refused_to_accepted": 0, "refused_to_refused": 0}
    changes = []
    divergence = 0
    for (family, source), before, after in zip(CASES, baseline, candidate):
        require(before["input"] == after["input"] == source
                and before["family"] == after["family"] == family,
                "FLOW_TRANSITION_CASE_MISMATCH")
        if before["legacy"] != before["indexed"] or after["legacy"] != after["indexed"]:
            divergence += 1
            changes.append({"family": family, "input": source,
                            "before": before, "after": after, "status": "NATIVE_PATH_DISAGREEMENT"})
            continue
        b, a = before["legacy"], after["legacy"]
        key = ("accepted" if b else "refused") + "_to_" + ("accepted" if a else "refused")
        counts[key] += 1
        if a != b:
            changes.append({"family": family, "input": source,
                            "before_accepted": b, "after_accepted": a})
    return {**counts, "legacy_indexed_disagreements": divergence,
            "changes": changes, "cases": len(CASES)}


def external_parsers(wheel: Path, ruamel_path: Path, pyyaml_wheel: Path,
                     pyyaml_path: Path) -> dict:
    require_wheel(wheel)
    check_installed_oracle_composer(wheel.read_bytes(),
                                    (ruamel_path / "ruamel/yaml/composer.py").read_bytes())
    require(digest(pyyaml_wheel.read_bytes()) == PYYAML_WHEEL_SHA256,
            "SECOND_PARSER_WHEEL_SHA256_MISMATCH")
    check_installed_pyyaml_module(
        pyyaml_wheel.read_bytes(), (pyyaml_path / "yaml/constructor.py").read_bytes(),
        (pyyaml_path / "yaml/loader.py").read_bytes())
    sys.path.insert(0, str(ruamel_path.resolve()))
    sys.path.insert(0, str(pyyaml_path.resolve()))
    from ruamel.yaml import YAML
    import ruamel.yaml
    import yaml
    require(ruamel.yaml.__version__ == "0.18.17" and yaml.__version__ == "6.0.3",
            "INDEPENDENT_PARSER_VERSION_DRIFT")
    oracle = YAML(typ="safe", pure=True)
    oracle.version = (1, 2)
    observations = []
    for family, source in CASES:
        statuses = {}
        for parser in ("ruamel", "pyyaml"):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if parser == "ruamel":
                        oracle.load(source)
                    else:
                        yaml.safe_load(source)
                statuses[parser] = "accepted"
            except (ruamel.yaml.error.YAMLError, yaml.YAMLError) as exc:
                # Only genuine parser errors count as refusals; other errors fail closed.
                statuses[parser] = "refused:" + type(exc).__name__
        observations.append({"family": family, "input": source, **statuses})
    return {"observations": observations,
            "implementation_disagreements": sum(
                a["ruamel"].startswith("accepted") != a["pyyaml"].startswith("accepted")
                for a in observations),
            "scope": "Observational parser behavior, not normative grammar authority"}


def exact_source(checkout: Path, lean: Path, sha: str) -> dict:
    result = verify_source(checkout, lean, sha)
    result["scanner_files"] = {}
    for filename in ("L4YAML/Scanner/SimpleKey.lean", "L4YAML/Scanner/IndexedDispatch.lean"):
        content = (checkout / filename).read_bytes()
        documented = subprocess.check_output(["git", "show", f"HEAD:{filename}"], cwd=checkout)
        require(content == documented, "CHANGED_SCANNER_SOURCE_FILE")
        result["scanner_files"][filename] = digest(content)
    return result


def read_native(path: Path) -> list[dict]:
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and raw, "FLOW_NATIVE_LOG_INCOMPLETE")
    return classify_rows(raw.decode("utf-8").splitlines())


def verified_report(base_native: Path, candidate_native: Path,
                    base_checkout: Path, candidate_checkout: Path, lean: Path,
                    base_sha: str, candidate_sha: str, wheel: Path, ruamel_path: Path,
                    pyyaml_wheel: Path, pyyaml_path: Path) -> dict:
    require(base_sha != candidate_sha, "FLOW_NO_SOURCE_TRANSITION")
    sources = {"baseline": exact_source(base_checkout, lean, base_sha),
               "candidate": exact_source(candidate_checkout, lean, candidate_sha)}
    baseline, candidate = read_native(base_native), read_native(candidate_native)
    delta = summarize_transition(baseline, candidate)
    independent = external_parsers(wheel, ruamel_path, pyyaml_wheel, pyyaml_path)
    status = ("BOUNDED_TARGETED_SCANNER_CHANGE_OBSERVED"
              if delta["accepted_to_refused"] == 11 and delta["accepted_to_accepted"] == 8
              and delta["legacy_indexed_disagreements"] == 0
              else "BOUNDED_SCANNER_DIFFERENTIAL_OBSERVED")
    return {
        "schema": "mathgraph.check.l4yaml.source-derived-flow-transition.v1",
        "status": status,
        "source": sources,
        "native_delta": delta,
        "external_parser_observations": independent,
        "native_logs_sha256": {"baseline": digest(base_native.read_bytes()),
                               "candidate": digest(candidate_native.read_bytes())},
        "verifier_sha256": digest(Path(__file__).read_bytes()),
        "decision_authority": "NOT_AUTHORIZED",
        "mathematical_terminal_form": None,
        "boundary": "19 source-derived flow acceptance inputs; no universal YAML conformance proof",
    }


def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("base-native", "candidate-native", "base-checkout", "candidate-checkout",
                 "lean", "base-sha", "candidate-sha", "wheel", "ruamel-path", "pyyaml-wheel",
                 "pyyaml-path", "out"):
        p.add_argument("--" + flag, required=True,
                       type=str if flag.endswith("sha") else Path)
    args = p.parse_args(argv)
    try:
        report = verified_report(
            args.base_native, args.candidate_native, args.base_checkout,
            args.candidate_checkout, args.lean, args.base_sha, args.candidate_sha,
            args.wheel, args.ruamel_path, args.pyyaml_wheel, args.pyyaml_path)
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as exc:
        report = {"schema": "mathgraph.check.l4yaml.source-derived-flow-transition.v1",
                  "status": "UNKNOWN", "error": f"{type(exc).__name__}: {exc}",
                  "decision_authority": "NOT_AUTHORIZED"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "transition": report.get("native_delta", {})
                      and {k: v for k, v in report["native_delta"].items()
                           if isinstance(v, int)}}))
    return 0 if report["status"] != "UNKNOWN" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
