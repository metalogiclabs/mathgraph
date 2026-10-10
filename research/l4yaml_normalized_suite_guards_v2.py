"""Compile actual pinned JPL TokenParser.parseYaml against decoded YAML-suite input.

This generator never claims the suite's metadata matches human intent.
The Lean #guard checks execute source-pinned parser semantics on 48 cases,
not a general theorem that the YAML specification and implementation agree.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from research.l4yaml_external_acceptance_v1 import (
    ensure_source_pins, load_suite_cases,
)


def stable(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def emit(jpl: Path, suite: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    pins = ensure_source_pins(jpl.resolve(), suite.resolve())
    selected, skipped = load_suite_cases(suite.resolve())
    counts = Counter("ACCEPT" if c["expected_accept"] else "REJECT" for c in selected)
    assert len(selected) == 48 and counts == {"ACCEPT": 31, "REJECT": 17}
    changed = [c for c in selected if c["encoded_yaml_sha256"] != c["yaml_sha256"]]
    assert [c["id"] for c in changed] == ["26DV:0"], changed
    assert all(c["source_decoder"] == "yaml-suite-visible-space-only-v1" for c in selected)
    decoded = changed[0]["yaml_source"]
    assert "␣" not in decoded and '"top1" : ' in decoded
    lines = [
        "import L4YAML.Parser.Composition",
        "/- Exact pinned source parser executable guard replay.",
        "   No generalized source-grammar theorem, no badge or truth promotion. -/",
        "open L4YAML", "",
    ]
    guard_ids = []
    for case in selected:
        literal = json.dumps(case["yaml_source"], ensure_ascii=False)
        expected = "true" if case["expected_accept"] else "false"
        lines.append(f'-- yaml-test-suite {case["id"]} {case["source_git_blob"]}')
        lines.append(f'#guard ((TokenParser.parseYaml {literal}).isOk == {expected})')
        guard_ids.append(case["id"])
    # Previously invalid source encoding must be rejected, while the same
    # input decoded according to yaml-test-suite metadata must be accepted.
    with_meta = json.dumps(decoded.replace(" ", "␣"), ensure_ascii=False)
    # Do NOT use this reconstructed glyph transformation as a source authority;
    # regenerate the real encoded input by loading the pinned descriptor.
    import yaml
    encoded_doc = yaml.safe_load(
        (suite / "src/26DV.yaml").read_text(encoding="utf-8")
    )
    encoded_source = encoded_doc[0]["yaml"]
    assert "␣" in encoded_source
    original = json.dumps(encoded_source, ensure_ascii=False)
    lines.extend([
        "-- Error-conditioning control: input contains visible whitespace glyphs",
        f'#guard ((TokenParser.parseYaml {original}).isOk == false)',
        "",
        "-- YAML cyclic alias separator for current unmodified JPL parser",
        '#guard ((TokenParser.parseYaml "&x [*x]\\n").isOk == false)',
        '#guard ((TokenParser.parseYaml "- &x item\\n- *x\\n").isOk == true)',
        '#guard ((TokenParser.parseYaml "*x\\n").isOk == false)',
        "",
    ])
    source = "\n".join(lines)
    (out / "NormalizedSuiteV2.lean").write_text(source, encoding="utf-8")
    report = {
        "schema": "mathgraph.l4yaml.decoded-source-semantics.v2",
        "jpl_commit": pins["jpl_commit"],
        "yaml_suite_commit": pins["yaml_suite_commit"],
        "jpl_pinned_blobs": pins["jpl_pinned_blobs"],
        "cases": len(selected),
        "external_expected": dict(counts),
        "normalized_fixture_ids": [c["id"] for c in changed],
        "normalized_fixture": {
            "id": changed[0]["id"],
            "source_file_git_blob": changed[0]["source_git_blob"],
            "raw_source_sha256": changed[0]["encoded_yaml_sha256"],
            "decoded_input_sha256": changed[0]["yaml_sha256"],
            "source_decoder": changed[0]["source_decoder"],
        },
        "frozen_selected_case_ids_sha256": hashlib.sha256(stable(guard_ids)).hexdigest(),
        "lean_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "source_metadata_skipped_files": len(skipped),
        "generated_lean_guards": len(selected) + 4,
        "lean_evaluation": "PENDING_PINNED_JPL_LEAN_RUN",
        "original_compiled_jpl_cli_v1": "47/48_RAW_SUITE_UNDECODED",
        "whole_input_spec_iff_parser": "UNKNOWN",
        "natural_language_fidelity": "UNKNOWN",
        "truth_promotion": False,
        "verified_badge": "NOT_ISSUED",
        "upstream_contact": False,
    }
    (out / "manifest.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:report[k] for k in (
        "cases","external_expected","normalized_fixture_ids",
        "generated_lean_guards","lean_evaluation","whole_input_spec_iff_parser"
    )},sort_keys=True))
    return report


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--jpl",required=True,type=Path)
    p.add_argument("--suite",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    v=p.parse_args()
    emit(v.jpl,v.suite,v.out)


if __name__ == "__main__":
    main()
