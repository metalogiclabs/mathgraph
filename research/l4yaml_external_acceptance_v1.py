"""Source-pinned, no-maintainer-contact executable L4YAML semantic audit.

The harness runs the *actual* JPL TryParse binary at a pinned public commit
and separately consults (a) a tiny independently written document-scoped
anchor/tag event checker for restricted template families and (b) independent
YAML test-suite labels at a separate, pinned public commit.

It never claims a generic source-to-formal theorem or YAML 1.2.2 parser
correctness. The fixed-format source event assignments are explicit scope
assumptions, not an automated complete YAML grammar interpreter.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

JPL_REPO = "nasa-jpl/L4YAML"
JPL_SHA = "62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
JPL_BRANCH = "fix-a-grammar-completeness"
YAML_SUITE_REPO = "yaml/yaml-test-suite"
YAML_SUITE_SHA = "da267a5c4782e7361e82889e76c0dc7df0e1e870"

# Exact upstream blob identities, pinned independently from the MathGraph copy.
EXPECTED_BLOBS = {
    "L4YAML/Proofs/Serialization/CommitTrace.lean":
        "cd679fb6186dcc58ee41890d09df89fa582706f9",
    "L4YAML/Proofs/Serialization/SerializationWellFormed.lean":
        "6c5a5f30663eb343b529030ce873d47adba5f439",
    "L4YAML/Proofs/Serialization/ExecutableBoundary.lean":
        "443d2c450e2759663eea1bead7966378642e4ba8",
    "Tests/TryParse.lean": "84af929a6cf6267b71222d2694fe87141120f6cd",
    "lake-manifest.json": "a1e04693316e2447fae6919dd7db9b41cc5cf4c5",
}
SCHEMA = "mathgraph.l4yaml.external-acceptance-audit.v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exact_git(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args], text=True,
        capture_output=True, timeout=15, check=True,
    )
    return p.stdout.strip()


def ensure_source_pins(jpl: Path, suite: Path) -> dict[str, Any]:
    if exact_git(jpl, "rev-parse", "HEAD") != JPL_SHA:
        raise AssertionError("JPL_REPOSITORY_HEAD_NOT_PINNED")
    if exact_git(suite, "rev-parse", "HEAD") != YAML_SUITE_SHA:
        raise AssertionError("TEST_SUITE_HEAD_NOT_PINNED")
    blobs = {}
    for name, expected in EXPECTED_BLOBS.items():
        path = jpl / name
        if not path.is_file():
            raise AssertionError("MISSING_PINNED_JPL_SOURCE:" + name)
        actual = exact_git(jpl, "hash-object", str(path))
        if actual != expected:
            raise AssertionError("JPL_SOURCE_BLOB_MISMATCH:" + name)
        blobs[name] = actual
    return {"jpl_commit": JPL_SHA, "yaml_suite_commit": YAML_SUITE_SHA,
            "jpl_pinned_blobs": blobs}


@dataclass(frozen=True)
class ModelFixture:
    id: str
    family: str
    yaml_source: str
    normative_events: tuple[tuple[str, str], ...]
    current_events: tuple[tuple[str, str], ...]
    # This flag means the template's event-role interpretation is predeclared.
    source_event_extraction: str = "RESTRICTED_TEMPLATE_MANUALLY_SPECIFIED"


def independent_event_check(events: tuple[tuple[str, str], ...]) -> bool:
    """Independent document-scoped event state; never calls JPL scanner/parser.

    Node-start definition and node-completion definition are represented by
    differently ordered event streams. This does not parse unrestricted YAML.
    """
    anchors: set[str] = set()
    tags: set[str] = set()
    for event, arg in events:
        if event in ("begin", "end"):
            anchors.clear()
            tags.clear()
        elif event == "anchor":
            anchors.add(arg)
        elif event == "alias":
            if arg not in anchors:
                return False
        elif event == "tag_def":
            tags.add(arg)
        elif event == "tag_use":
            if arg not in tags and arg not in ("", "!", "!!"):
                return False
        else:
            raise ValueError("Unsupported event policy operation: " + event)
    return True


def fixtures() -> list[ModelFixture]:
    """Small, explicit YAML surface families + semantics (not general parsing)."""
    items = [
        ModelFixture(
            "simple-mapping", "lexical-control", "answer: 42\n",
            (("begin", ""),), (("begin", ""),)),
        ModelFixture(
            "quoted-not-alias", "lexical-control", 'message: "*x"\n',
            (("begin", ""),), (("begin", ""),)),
        ModelFixture(
            "literal-not-alias", "lexical-control", "message: |\n  *missing\n",
            (("begin", ""),), (("begin", ""),)),
        ModelFixture(
            "comment-not-alias", "lexical-control", "answer: ok # *missing\n",
            (("begin", ""),), (("begin", ""),)),
    ]
    for name in ("x", "y", "node", "alpha"):
        items.extend([
            ModelFixture(
                "recursive-" + name, "self-reference-separator",
                "&" + name + " [*" + name + "]\n",
                (("begin", ""), ("anchor", name), ("alias", name)),
                (("begin", ""), ("alias", name), ("anchor", name)),
            ),
            ModelFixture(
                "recursive-nested-" + name, "self-reference-separator",
                "&" + name + " [item, *" + name + "]\n",
                (("begin", ""), ("anchor", name), ("alias", name)),
                (("begin", ""), ("alias", name), ("anchor", name)),
            ),
            ModelFixture(
                "sibling-" + name, "declared-alias-control",
                "- &" + name + " item\n- *" + name + "\n",
                (("begin", ""), ("anchor", name), ("alias", name)),
                (("begin", ""), ("anchor", name), ("alias", name)),
            ),
            ModelFixture(
                "undefined-" + name, "undefined-alias-control",
                "*"+name+"\n",
                (("begin", ""), ("alias", name)),
                (("begin", ""), ("alias", name)),
            ),
            ModelFixture(
                "near-miss-" + name, "mutation-rejected",
                "- &" + name + " item\n- *" + name + "X\n",
                (("begin", ""), ("anchor", name), ("alias", name+"X")),
                (("begin", ""), ("anchor", name), ("alias", name+"X")),
            ),
            ModelFixture(
                "cross-document-" + name, "document-reset",
                "---\n&" + name + " item\n...\n---\n*" + name + "\n",
                (("begin", ""), ("anchor", name), ("end", ""),
                 ("begin", ""), ("alias", name)),
                (("begin", ""), ("anchor", name), ("end", ""),
                 ("begin", ""), ("alias", name)),
            ),
        ])
    tag_header = "%TAG !h! tag:example.org,2026:\n---\n"
    items.extend([
        ModelFixture(
            "tag-declared", "tag-declaration",
            tag_header + "!h!thing val\n",
            (("begin", ""), ("tag_def", "!h!"), ("tag_use", "!h!")),
            (("begin", ""), ("tag_def", "!h!"), ("tag_use", "!h!")),
        ),
        ModelFixture(
            "tag-undeclared", "tag-declaration",
            "---\n!h!thing val\n",
            (("begin", ""), ("tag_use", "!h!")),
            (("begin", ""), ("tag_use", "!h!")),
        ),
        ModelFixture(
            "tag-document-reset", "document-reset",
            tag_header + "!h!thing first\n...\n---\n!h!thing second\n",
            (("begin", ""), ("tag_def", "!h!"), ("tag_use", "!h!"),
             ("end", ""), ("begin", ""), ("tag_use", "!h!")),
            (("begin", ""), ("tag_def", "!h!"), ("tag_use", "!h!"),
             ("end", ""), ("begin", ""), ("tag_use", "!h!")),
        ),
    ])
    assert len({f.id for f in items}) == len(items)
    assert sum(f.family == "self-reference-separator" for f in items) == 8
    return items


def suite_expected_accept(case: dict[str, Any]) -> bool:
    """Use yaml-test-suite's *fail* flag, not the descriptive 'error' tag.

    An absent fail flag denotes a positive fixture. Fail is a typed Boolean;
    malformed or contradictory labels are not quietly reinterpreted.
    """
    fail = case.get("fail", False)
    if type(fail) is not bool:
        raise ValueError("yaml-test-suite.fail must be a Boolean if present")
    tags = case.get("tags", "")
    tagset = set(tags.split()) if isinstance(tags, str) else (
        set(tags) if isinstance(tags, list) and all(type(x) is str for x in tags)
        else set())
    if fail is False and "error" in tagset:
        raise ValueError("yaml-test-suite.error tag conflicts with absent/false fail")
    return not fail


def decode_yaml_suite_space_only(source: str) -> str:
    """Decode U+2423 visible trailing spaces on this frozen benchmark slice.

    yaml-test-suite/src uses visible glyphs for invisible input bytes. The
    current selected 48 cases only use the U+2423 marker; other markers
    require a separately checked decoder extension and fail closed here.
    """
    if not isinstance(source, str):
        raise ValueError("yaml test source must be a string")
    unsupported = tuple(sorted(set(source) & set("—»→←↵∎⇔")))
    if unsupported:
        raise ValueError("UNSUPPORTED_YAML_SUITE_ENCODING:" + "".join(unsupported))
    return source.replace("␣", " ")


def load_suite_cases(suite: Path, per_category: int = 12) -> tuple[list[dict[str, Any]], list[str]]:
    """Load independent labels from yaml/yaml-test-suite, not the JPL test fork."""
    import yaml  # Dev-only metadata parser, NOT the truth oracle

    sources = list(sorted((suite / "src").glob("*.yaml")))
    if len(sources) < 100:
        raise AssertionError("INDEPENDENT_SUITE_TOO_SMALL")
    records = []
    skipped = []
    for file in sources:
        try:
            doc = yaml.safe_load(file.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeError) as exc:
            skipped.append(file.name + ":" + type(exc).__name__)
            continue
        if not isinstance(doc, list):
            skipped.append(file.name + ":not_array")
            continue
        for n, case in enumerate(doc):
            if not isinstance(case, dict):
                continue
            snippet = case.get("yaml")
            tags = case.get("tags", "")
            tagset = set(tags.split()) if isinstance(tags, str) else (
                set(tags) if isinstance(tags, list) else set())
            if (not isinstance(snippet, str) or not snippet.strip() or
                    len(snippet.encode("utf-8")) > 1400):
                continue
            # Avoid post-YAML-1.2 deviations in this spec-bounded first trial.
            if any(t.startswith(("1.3-", "2.0-")) for t in tagset):
                continue
            records.append({
                "id": file.stem + ":" + str(n),
                "source_file": "src/" + file.name,
                "source_git_blob": exact_git(suite, "hash-object", str(file)),
                "yaml_source": snippet,
                "yaml_sha256": sha256(snippet.encode("utf-8")),
                "tags": sorted(tagset),
                "expected_accept": suite_expected_accept(case),
                "label_source": "yaml-test-suite.fail",
                "origin": "yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870",
            })
    selected: list[dict[str, Any]] = []
    chosen: set[str] = set()
    for category in ("alias", "anchor", "directive", "tag"):
        options = [r for r in records if category in r["tags"] and r["id"] not in chosen]
        # Keep label diversity where possible, without changing source labels.
        positives = [r for r in options if r["expected_accept"]]
        negatives = [r for r in options if not r["expected_accept"]]
        take = positives[:per_category // 2] + negatives[:per_category // 2]
        if len(take) < per_category:
            remainder = [r for r in options if r not in take]
            take.extend(remainder[:per_category - len(take)])
        for row in take:
            selected.append(row)
            chosen.add(row["id"])
    if len(selected) < 20:
        raise AssertionError("TOO_FEW_INDEPENDENT_YAML_CASES")
    if not any(not r["expected_accept"] for r in selected):
        raise AssertionError("NO_EXTERNAL_NEGATIVE_CASES")
    if not any(r["expected_accept"] for r in selected):
        raise AssertionError("NO_EXTERNAL_POSITIVE_CASES")
    if len({r["id"] for r in selected}) != len(selected):
        raise AssertionError("DUPLICATE_EXTERNAL_CASE_ID")
    # Decode *only after* the frozen selection. Unknown marker families must
    # not silently enter the grammar under a lossy representation change.
    for row in selected:
        encoded = row["yaml_source"]
        decoded = decode_yaml_suite_space_only(encoded)
        row["encoded_yaml_sha256"] = row["yaml_sha256"]
        row["yaml_source"] = decoded
        row["yaml_sha256"] = sha256(decoded.encode("utf-8"))
        row["source_decoder"] = "yaml-suite-visible-space-only-v1"
    return selected, skipped


def parser_observation(binary: Path, text: str, work: Path) -> dict[str, Any]:
    tmp = work / ("case-" + sha256(text.encode("utf-8"))[:20] + ".yaml")
    tmp.write_text(text, encoding="utf-8")
    try:
        proc = subprocess.run([str(binary), str(tmp)], cwd=binary.parent,
                              capture_output=True, text=True, timeout=12)
        rc = proc.returncode
        if rc in (0, 1):
            return {"status": "ACCEPT" if rc == 0 else "REJECT",
                    "exit_code": rc, "stderr_excerpt": proc.stderr[-280:]}
        return {"status": "ERROR", "exit_code": rc,
                "stderr_excerpt": proc.stderr[-280:]}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "exit_code": None, "stderr_excerpt": ""}


def run(jpl: Path, suite: Path, out: Path, *, require_replay: bool = True) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    pins = ensure_source_pins(jpl, suite) if require_replay else {
        "source_pin_status": "NOT_REPLAYED_IN_THIS_TEST"}
    binary = jpl / ".lake/build/bin/tryparse"
    if require_replay and not binary.is_file():
        raise AssertionError("REAL_EXECUTABLE_MISSING_DO_NOT_USE_STUB")
    details: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mathgraph-real-l4yaml-") as tmp_dir:
        work = Path(tmp_dir)
        for f in fixtures():
            norm = independent_event_check(f.normative_events)
            current = independent_event_check(f.current_events)
            observed = (parser_observation(binary, f.yaml_source, work) if require_replay
                        else {"status": "NOT_RUN"})
            details.append({
                "id": f.id, "family": f.family,
                "yaml_sha256": sha256(f.yaml_source.encode("utf-8")),
                "source_event_extraction": f.source_event_extraction,
                "normative_event_accept": norm, "current_event_accept": current,
                "parser": observed,
                "matches_normative": (
                    (observed["status"] == "ACCEPT") == norm
                    if observed["status"] in ("ACCEPT", "REJECT") else None
                ),
                "matches_current_model": (
                    (observed["status"] == "ACCEPT") == current
                    if observed["status"] in ("ACCEPT", "REJECT") else None
                ),
            })
        independent_cases, skipped = load_suite_cases(suite)
        external_rows = []
        for case in independent_cases:
            observed = (parser_observation(binary, case["yaml_source"], work)
                        if require_replay else {"status": "NOT_RUN"})
            external_rows.append({
                "id": case["id"], "source_file": case["source_file"],
                "source_git_blob": case["source_git_blob"],
                "encoded_yaml_sha256": case.get("encoded_yaml_sha256"),
                "source_decoder": case.get("source_decoder"),
                "yaml_sha256": case["yaml_sha256"],
                "tags": case["tags"], "expected_accept": case["expected_accept"],
                "parser": observed,
                "match": (
                    (observed["status"] == "ACCEPT") == case["expected_accept"]
                    if observed["status"] in ("ACCEPT", "REJECT") else None
                ),
            })
    template_counts = dict(sorted(Counter((z["parser"]["status"] for z in details)).items()))
    suite_counts = dict(sorted(Counter((z["parser"]["status"] for z in external_rows)).items()))
    suite_validated = [z for z in external_rows if z["match"] is not None]
    family_mismatches = [
        {"id": z["id"], "family": z["family"],
         "expected": z["normative_event_accept"],
         "observed": z["parser"]["status"]}
        for z in details if z["matches_normative"] is False
    ]
    suite_mismatches = [
        {"id": z["id"], "source_file": z["source_file"],
         "expected": "ACCEPT" if z["expected_accept"] else "REJECT",
         "observed": z["parser"]["status"]}
        for z in suite_validated if z["match"] is False
    ]
    exact_recursive = next(z for z in details if z["id"] == "recursive-x")
    simple = next(z for z in details if z["id"] == "simple-mapping")
    undefined = next(z for z in details if z["id"] == "undefined-x")
    if not exact_recursive["normative_event_accept"] or exact_recursive["current_event_accept"]:
        raise AssertionError("NORMATIVE_VERSUS_CURRENT_EVENT_SEPARATOR_MISSING")
    if require_replay:
        if simple["parser"]["status"] != "ACCEPT":
            raise AssertionError("PARSER_SANITY_VALID_CONTROL_FAILED")
        if undefined["parser"]["status"] != "REJECT":
            raise AssertionError("PARSER_SANITY_INVALID_CONTROL_FAILED")
        if any(z["parser"]["status"] in ("TIMEOUT", "ERROR") for z in details):
            raise AssertionError("PARSER_RUNTIME_ERROR_IN_FIXED_CONTROLS")
    summary = {
        "schema": SCHEMA, "pins": pins,
        "scope": "actual source-pinned L4YAML tryparse + restricted template event model + independent YAML test suite",
        "upstream_branch": JPL_BRANCH,
        "toolchain": "leanprover/lean4:v4.34.0 (taken from pinned JPL source)",
        "fixed_model_cases": len(details),
        "template_parser_outcomes": template_counts,
        "independent_suite_cases": len(external_rows),
        "independent_suite_labels": {
            "expected_accept": sum(x["expected_accept"] for x in external_rows),
            "expected_reject": sum(not x["expected_accept"] for x in external_rows)},
        "independent_suite_observations": suite_counts,
        "independent_suite_scored": len(suite_validated),
        "independent_suite_agreements": sum(x["match"] is True for x in suite_validated),
        "independent_suite_disagreements": len(suite_mismatches),
        "suite_ingest_skipped": len(skipped),
        "template_normative_mismatches": len(family_mismatches),
        "self_reference_anchor_policy_separator": {
            "input": "&x [*x]\\n",
            "normative_early_commit": exact_recursive["normative_event_accept"],
            "current_l4yaml_completion_commit": exact_recursive["current_event_accept"],
            "actual_parser_observation": exact_recursive["parser"]["status"],
            "source_to_events_independently_certified": False,
        },
        "formal_closed_trace_proofs": "PENDING_SEPARATE_LEAN_GATE",
        "whole_input_spec_iff_parser": "UNKNOWN",
        "source_to_event_grammar_completeness": "UNKNOWN",
        "source_to_spec_fidelity": "UNKNOWN",
        "model_training_or_palomar_cost_gain": "NOT_TESTED",
        "contacted_upstream_maintainer": False,
        "no_truth_promotion": True,
        "no_verified_badge": True,
        "fixed_cases": details,
        "independent_suite_details": external_rows,
        "template_normative_residuals": family_mismatches,
        "independent_suite_residuals": suite_mismatches,
    }
    (out / "report.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in (
        "fixed_model_cases", "template_parser_outcomes",
        "independent_suite_cases", "independent_suite_labels",
        "independent_suite_observations", "independent_suite_scored",
        "independent_suite_agreements", "independent_suite_disagreements",
        "template_normative_mismatches", "self_reference_anchor_policy_separator",
        "whole_input_spec_iff_parser"
    )}, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jpl", type=Path, required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.jpl.resolve(), args.suite.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()
