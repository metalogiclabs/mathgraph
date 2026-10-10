"""Read-only MathGraph Check release built from exact archived verifier receipts.

This is an authenticated-by-digest *publication* projection over two qualified,
historical GitHub Actions artifacts. It does not run a prover, trust user-supplied
claims, update live status, validate natural language, or issue a theorem badge.

The source of truth is the original ZIP bytes from the exact pinned CI runs;
the record is always regenerated, never edited to create mathematical warrant.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from html import escape
from io import BytesIO
import json
from pathlib import Path
import re
import zipfile

RECORD_ID = "mg-l4yaml-source-check-20261010"
EXPECTED_RECORD_SHA256 = "f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb"
JPL_COMMIT = "62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
SUITE_COMMIT = "da267a5c4782e7361e82889e76c0dc7df0e1e870"
MATHGRAPH_V1_HEAD = "d49a17d2786e6d071af37d2aeba2f2dad7765b75"
MATHGRAPH_V2_HEAD = "988afbf9a6ec69488b63af5c7ff986fde26d673c"
TRUSTED_ZIPS = {
    "v1": "b75581017d6620481c77e52b350e8bb8631d11747a92789f7887cde527807086",
    "v2": "61fc93815e3329c0490324f52897a94d3417044a5cf16a8e1e0f0109aa0e515e",
}
V1_NAMES = frozenset((
    "lean-bridge.txt", "pins.json", "report.json", "toolchain-version.txt",
))
V2_NAMES = frozenset((
    "NormalizedSuiteV2.lean", "lean-evaluation.log", "manifest.json", "toolchain.txt",
))
ALLOWED_AX = frozenset(("propext", "Classical.choice", "Quot.sound"))
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
EXPECTED_CLAIM_NAMES = (
    "L4YAML.Proofs.Serialization.CommitTrace.yaml_enclosing_anchor_self_reference_allowed",
    "L4YAML.Proofs.Serialization.CommitTrace.current_l4yaml_enclosing_anchor_self_reference_rejected",
    "L4YAML.Proofs.Serialization.CommitTrace.later_sibling_alias_allowed",
    "L4YAML.Proofs.Serialization.parse_iff_executable_language",
)


class ReleaseBoundaryError(ValueError):
    """The source evidence cannot safely be published as an earned receipt."""


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise ReleaseBoundaryError(code)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _load_archive(path: Path, label: str) -> dict[str, bytes]:
    data = Path(path).read_bytes()
    _require(len(data) < 256_000, "UNEXPECTED_ARCHIVE_SIZE")
    _require(digest(data) == TRUSTED_ZIPS[label], "EVIDENCE_ARCHIVE_SHA256_MISMATCH")
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            infos = archive.infolist()
            wanted = V1_NAMES if label == "v1" else V2_NAMES
            _require(len(infos) == len(wanted), "ZIP_MEMBER_COUNT_CHANGED")
            _require({info.filename for info in infos} == wanted, "ZIP_MEMBERS_CHANGED")
            _require(
                all(info.file_size <= 512_000 and not info.is_dir() for info in infos),
                "ZIP_UNBOUNDED_MEMBER",
            )
            return {name: archive.read(name) for name in sorted(wanted)}
    except (zipfile.BadZipFile, OSError) as exc:
        raise ReleaseBoundaryError("MALFORMED_PINNED_EVIDENCE_ARCHIVE") from exc


def _load_json(data: bytes, name: str) -> dict:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ReleaseBoundaryError("MALFORMED_EVIDENCE_JSON:" + name) from exc
    _require(type(value) is dict, "EVIDENCE_NOT_AN_OBJECT:" + name)
    return value


def validate_sources(v1: dict[str, bytes], v2: dict[str, bytes]) -> tuple[dict, dict]:
    a = _load_json(v1["report.json"], "v1.report")
    b = _load_json(v2["manifest.json"], "v2.manifest")
    pins = _load_json(v1["pins.json"], "v1.pins")
    _require(a.get("schema") == "mathgraph.l4yaml.external-acceptance-audit.v1", "V1_SCHEMA")
    _require(b.get("schema") == "mathgraph.l4yaml.decoded-source-semantics.v2", "V2_SCHEMA")
    _require(pins == a.get("pins"), "V1_PIN_MANIFEST_MISMATCH")
    _require(pins.get("jpl_commit") == JPL_COMMIT, "JPL_SOURCE_COMMIT_MISMATCH")
    _require(pins.get("yaml_suite_commit") == SUITE_COMMIT, "YAML_SUITE_COMMIT_MISMATCH")
    _require(pins.get("jpl_pinned_blobs") == EXPECTED_BLOBS, "JPL_BLOB_SET_MISMATCH")
    _require(b.get("jpl_commit") == JPL_COMMIT, "V2_JPL_SOURCE_COMMIT_MISMATCH")
    _require(b.get("yaml_suite_commit") == SUITE_COMMIT, "V2_SUITE_COMMIT_MISMATCH")
    _require(b.get("jpl_pinned_blobs") == EXPECTED_BLOBS, "V2_JPL_BLOB_SET_MISMATCH")

    _require(a.get("fixed_model_cases") == 31, "V1_FIXED_CASE_COUNT")
    _require(a.get("independent_suite_cases") == 48, "V1_SUITE_CASE_COUNT")
    _require(a.get("independent_suite_scored") == 48, "V1_SUITE_NOT_FULLY_SCORED")
    _require(a.get("independent_suite_agreements") == 47, "V1_RAW_SUITE_EXPECTATION")
    _require(a.get("independent_suite_disagreements") == 1, "V1_RAW_RESIDUAL_COUNT")
    _require(a.get("independent_suite_labels") == {
        "expected_accept": 31, "expected_reject": 17,
    }, "V1_LABEL_COUNTS")
    _require(a.get("independent_suite_residuals") == [{
        "expected": "ACCEPT", "id": "26DV:0", "observed": "REJECT",
        "source_file": "src/26DV.yaml",
    }], "V1_NOT_SOURCE_ENCODING_RESIDUAL")
    _require(
        len(a.get("template_normative_residuals", [])) == 8
        and all(r.get("family") == "self-reference-separator"
                for r in a["template_normative_residuals"]),
        "V1_ANCHOR_POLICY_SEPARATORS",
    )
    separator = a.get("self_reference_anchor_policy_separator", {})
    _require(
        separator.get("actual_parser_observation") == "REJECT"
        and separator.get("normative_early_commit") is True
        and separator.get("current_l4yaml_completion_commit") is False
        and separator.get("source_to_events_independently_certified") is False,
        "V1_ANCHOR_SEMANTICS_BOUNDARY",
    )
    _require(a.get("no_truth_promotion") is True and a.get("no_verified_badge") is True,
             "V1_ILLEGAL_AUTHORITY_PROMOTION")
    _require(a.get("whole_input_spec_iff_parser") == "UNKNOWN", "V1_UNIVERSAL_CLAIM_CHANGED")

    _require(b.get("cases") == 48, "V2_CASE_COUNT")
    _require(b.get("external_expected") == {"ACCEPT": 31, "REJECT": 17},
             "V2_EXTERNAL_LABELS")
    _require(b.get("generated_lean_guards") == 52, "V2_GUARD_COUNT")
    _require(b.get("normalized_fixture_ids") == ["26DV:0"], "V2_SOURCE_DECODER_SCOPE")
    normalized = b.get("normalized_fixture", {})
    _require(normalized == {
        "id": "26DV:0",
        "source_file_git_blob": "ada7c5f1b42a6240c2d8c523f50a08a024d37a77",
        "raw_source_sha256": "6a7b111962441781a368bdcb793ca5a4be450b65c2c82da48bca86f3d8944791",
        "decoded_input_sha256": "b9ac5bb5babe113af697638577d77ee556dbc2d596bf05c5d31a8b402882976a",
        "source_decoder": "yaml-suite-visible-space-only-v1",
    }, "V2_DECODER_IDENTITY_CHANGED")
    _require(
        b.get("lean_evaluation") == "PASS_ALL_52_GUARDS_EXACT_JPL_SOURCE"
        and b.get("verified_badge") == "NOT_ISSUED"
        and b.get("truth_promotion") is False
        and b.get("natural_language_fidelity") == "UNKNOWN"
        and b.get("whole_input_spec_iff_parser") == "UNKNOWN"
        and b.get("upstream_contact") is False,
        "V2_EPISTEMIC_BOUNDARY_CHANGED",
    )
    lean_source = v2["NormalizedSuiteV2.lean"]
    _require(digest(lean_source) == b.get("lean_source_sha256"), "V2_LEAN_SOURCE_MISMATCH")
    _require(lean_source.count(b"#guard ((") == 52, "V2_NOT_52_ACTUAL_GUARDS")
    _require(b'-- yaml-test-suite 26DV:0' in lean_source, "V2_DECODED_CASE_MISSING")
    _require(b'&x [*x]' in lean_source, "V2_ANCHOR_NEGATIVE_MISSING")
    _require(v2["lean-evaluation.log"].strip() == b"", "V2_LEAN_WARNINGS_OR_ERRORS")
    toolchain = v2["toolchain.txt"].decode("utf-8").strip()
    _require(toolchain.startswith("Lean (version 4.34.0, "), "V2_TOOLCHAIN_CHANGED")
    v1_toolchain = v1["toolchain-version.txt"].decode("utf-8").strip()
    _require(v1_toolchain.startswith("Lean (version 4.34.0, "), "V1_TOOLCHAIN_CHANGED")
    bridge = v1["lean-bridge.txt"].decode("utf-8")
    matched = re.findall(
        r"'([^']+)' depends on axioms: \[([^\]]+)\]", bridge,
    )
    _require(
        len(matched) == 4 and tuple(name for name, _ in matched) == EXPECTED_CLAIM_NAMES,
        "V1_ORIGINAL_PROOF_NAMES_CHANGED",
    )
    for _, axioms in matched:
        subset = frozenset(a.strip() for a in axioms.split(","))
        _require(subset.issubset(ALLOWED_AX), "V1_UNAPPROVED_PROOF_AXIOM")
    return a, b


def build_record(v1_path: Path, v2_path: Path) -> dict:
    v1 = _load_archive(v1_path, "v1")
    v2 = _load_archive(v2_path, "v2")
    report, manifest = validate_sources(v1, v2)
    result = {
        "schema": "mathgraph.public-consequence-record.v1",
        "id": RECORD_ID,
        "title": "L4YAML parser acceptance — pinned source check",
        "project": "L4YAML",
        "publisher": "Metalogic Labs / MathGraph",
        "attribution": "Independent check of public third-party code; no affiliation or endorsement implied",
        "record_kind": "READ_ONLY_EVIDENCE_PROJECTION",
        "snapshot_date": "2026-10-10",
        "source": {
            "repo": "nasa-jpl/L4YAML",
            "commit": JPL_COMMIT,
            "branch_at_pin": "fix-a-grammar-completeness",
            "lean_toolchain": "leanprover/lean4:v4.34.0",
            "external_suite_repo": "yaml/yaml-test-suite",
            "external_suite_commit": SUITE_COMMIT,
        },
        "axes": {
            "formal_verification": {
                "status": "PINNED_SOURCE_THEOREMS_REPLAYED",
                "authority": "ORIGINAL_JPL_LEAN_PROOF_OBJECTS",
                "scope": "Named executable factorization and scoped anchor-event lemmas only",
                "universal_yaml_correctness": "UNKNOWN",
            },
            "finite_executable": {
                "status": "PINNED_CASES_CHECKED",
                "authority": "LEAN_GUARDS_AND_COMPILED_TRYPARSE",
                "source_cases": 48,
                "matched_external_labels": 48,
                "expected_accept": 31,
                "expected_reject": 17,
                "extra_controls": 4,
                "total_lean_guards": 52,
                "case_scope": "Pinned YAML-suite examples after specified source decoding",
            },
            "statement_fidelity": {"status": "UNKNOWN", "truth_promoting": False},
            "human_digestion": {"status": "UNKNOWN", "truth_promoting": False},
            "generalization": {"status": "UNKNOWN", "truth_promoting": False},
            "current_requalification": {"status": "NOT_CHECKED_AFTER_SNAPSHOT"},
            "global_truth_promotion": False,
        },
        "known_separator": {
            "input": "&x [*x]\\n",
            "source_to_event_translation": "RESTRICTED_MANUALLY_DECLARED",
            "independent_normative_event_model": "ACCEPT",
            "actual_pinned_jpl_parser": "REJECT",
            "jpl_completion_order_event_model": "REJECT",
            "evidence_kind": "SOURCE_SPECIFIC_KNOWN_DISCREPANCY",
            "novel_bug_claim": False,
            "whole_input_extraction_theorem": "UNKNOWN",
        },
        "test_input_normalization": {
            "case_id": "26DV:0",
            "decoder": "yaml-suite-visible-space-only-v1",
            "raw_sha256": manifest["normalized_fixture"]["raw_source_sha256"],
            "decoded_sha256": manifest["normalized_fixture"]["decoded_input_sha256"],
            "v1_raw_mismatch": True,
            "v2_native_decoded_guard": "PASS",
        },
        "evidence": {
            "v1_compiled_parser": {
                "run": 38018495536,
                "source_commit": MATHGRAPH_V1_HEAD,
                "artifact_id": 11657687808,
                "archive_sha256": TRUSTED_ZIPS["v1"],
                "url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38018495536",
                "artifact_url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38018495536/artifacts/11657687808",
                "original_build_targets": 487,
                "raw_unconverted_external_agreement": 47,
            },
            "v2_normalized_native_parser": {
                "run": 38020008793,
                "source_commit": MATHGRAPH_V2_HEAD,
                "artifact_id": 11657314389,
                "archive_sha256": TRUSTED_ZIPS["v2"],
                "url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38020008793",
                "artifact_url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38020008793/artifacts/11657314389",
                "lean_source_sha256": manifest["lean_source_sha256"],
                "decoded_case_count": 48,
                "guards": 52,
            },
            "external_sources": {
                "jpl": "https://github.com/nasa-jpl/L4YAML/tree/" + JPL_COMMIT,
                "yaml_suite": "https://github.com/yaml/yaml-test-suite/tree/" + SUITE_COMMIT,
            },
        },
        "admission": {
            "status": "WARRANTED_ON_PINNED_BOUNDED_CASES",
            "source_archive_hashes_replayed": True,
            "mathematical_theorem_badge_issued": False,
            "source_fidelity_certified": False,
            "automatic_api_warrant_promotion": False,
        },
    }
    result["content_sha256"] = digest(canonical_json(result))
    return result


def _release_integrity(record: dict) -> None:
    _require(record.get("id") == RECORD_ID, "RECORD_ID_CHANGED")
    label = dict(record)
    actual = label.pop("content_sha256", "")
    _require(type(actual) is str and actual == digest(canonical_json(label)),
             "PUBLIC_RECORD_CONTENT_HASH_INVALID")
    _require(actual == EXPECTED_RECORD_SHA256, "PUBLIC_RECORD_NOT_TRUSTED_SNAPSHOT")
    _require(label.get("admission", {}).get("mathematical_theorem_badge_issued") is False,
             "PUBLIC_RECORD_OVERCLAIMS_BADGE")
    _require(label.get("axes", {}).get("generalization", {}).get("status") == "UNKNOWN",
             "PUBLIC_RECORD_GENERALIZATION_PROMOTION")
    _require(label.get("axes", {}).get("global_truth_promotion") is False,
             "PUBLIC_RECORD_TRUTH_PROMOTION")


def resolve(record: dict, query: object) -> dict:
    """Pure read-only, exact scope-bound agent query; never infer from names."""
    _release_integrity(record)
    if not isinstance(query, dict):
        return {"status": "BAD_REQUEST", "reason": "QUERY_MUST_BE_OBJECT"}
    permitted = {"record_id", "source_commit", "external_suite_commit", "goal"}
    if set(query) - permitted:
        return {"status": "BAD_REQUEST", "reason": "UNRECOGNIZED_QUERY_KEYS"}
    if not all(isinstance(query.get(k), str) and query[k] for k in permitted):
        return {"status": "BAD_REQUEST", "reason": "EXACT_SCOPE_REQUIRED"}
    if (
        query["record_id"] != RECORD_ID
        or query["source_commit"] != JPL_COMMIT
        or query["external_suite_commit"] != SUITE_COMMIT
    ):
        return {
            "status": "UNKNOWN",
            "reason": "NO_EVIDENCE_FOR_REQUESTED_SOURCE_OR_VERSION",
            "evidence": [],
            "truth_promotion": False,
        }
    goal = query["goal"]
    if goal == "finite_parser_acceptance":
        return {
            "status": "WARRANTED_BOUNDED",
            "scope": "48 pinned external YAML cases plus 4 Lean guard controls",
            "verified": {"matched": 48, "total": 48, "extra_controls": 4},
            "authority": "PINNED_SOURCE_LEAN_GUARDS",
            "whole_language_validity": "UNKNOWN",
            "truth_promotion": False,
            "evidence": [record["evidence"]["v2_normalized_native_parser"]["url"]],
            "record_id": RECORD_ID,
            "record_sha256": record["content_sha256"],
        }
    if goal == "recursive_anchor_behavior":
        return {
            "status": "WARRANTED_BOUNDED_DIFFERENCE",
            "input": "&x [*x]\\n",
            "pinned_jpl": "REJECT",
            "normative_restricted_event_model": "ACCEPT",
            "source_to_event_translation": "RESTRICTED_MANUALLY_DECLARED",
            "general_semantic_fidelity": "UNKNOWN",
            "truth_promotion": False,
            "evidence": [record["evidence"]["v1_compiled_parser"]["url"],
                         record["evidence"]["v2_normalized_native_parser"]["url"]],
            "record_id": RECORD_ID,
            "record_sha256": record["content_sha256"],
        }
    return {
        "status": "UNKNOWN",
        "reason": "NO_QUALIFIED_WARRANT_FOR_REQUESTED_GOAL",
        "supported_goals": ["finite_parser_acceptance", "recursive_anchor_behavior"],
        "truth_promotion": False,
        "evidence": [],
        "record_id": RECORD_ID,
    }


def render_badge(record: dict) -> str:
    _release_integrity(record)
    # Explicit scope in the badge itself; neutral coloring and no theorem seal.
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="288" height="30"'
        ' role="img" aria-label="MathGraph: 48/48 pinned source cases checked">'
        '<title>MathGraph: 48/48 pinned source cases checked</title>'
        '<rect width="288" height="30" rx="5" fill="#192332"/>'
        '<rect x="112" width="176" height="30" rx="5" fill="#3B506B"/>'
        '<rect x="112" width="10" height="30" fill="#3B506B"/>'
        '<g fill="#FFF" font-family="system-ui,Segoe UI,sans-serif"'
        ' font-size="12" font-weight="600" text-anchor="middle">'
        '<text x="56" y="20">MathGraph</text>'
        '<text x="200" y="20">48/48 source cases</text></g></svg>'
    )


def render_html(record: dict) -> str:
    _release_integrity(record)
    evidence = record["evidence"]
    jpl = evidence["external_sources"]["jpl"]
    suite = evidence["external_sources"]["yaml_suite"]
    orig = evidence["v1_compiled_parser"]["url"]
    norm = evidence["v2_normalized_native_parser"]["url"]
    exact = escape(record["source"]["commit"])
    proof = escape(record["content_sha256"])
    # No generated HTML from user-provided, untrusted mathematical source text.
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="MathGraph Check: independently reproducible, source-scoped Lean evidence.">
<title>MathGraph Check — L4YAML source evidence</title>
<style>
:root{{color-scheme:light;--ink:#1A202B;--muted:#657181;--line:#DDE3EA;--soft:#F5F7F9;--blue:#3155A8}}
*{{box-sizing:border-box}}
body{{margin:0;background:#FFF;color:var(--ink);font:16px/1.58 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
a{{color:var(--blue);text-decoration:none}}a:hover{{text-decoration:underline}}
header{{border-bottom:1px solid var(--line)}}.shell{{max-width:1024px;margin:auto;padding:0 28px}}
nav{{display:flex;align-items:center;justify-content:space-between;min-height:74px;gap:16px}}
.brand{{font-weight:730;letter-spacing:-.04em;font-size:23px;color:var(--ink)}}
.dot{{display:inline-grid;place-items:center;width:29px;height:29px;border-radius:6px;background:var(--ink);color:white;margin-right:9px;font-size:15px;font-weight:700}}
nav .rhs{{font-size:13px;color:var(--muted)}}
main{{padding-top:65px;padding-bottom:95px}}
.kicker{{font-size:12px;font-weight:720;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}}
h1{{font-size:clamp(35px,5vw,57px);font-weight:650;line-height:1.12;letter-spacing:-.048em;max-width:780px;margin:18px 0 19px}}
.lead{{font-size:18px;color:#4C5968;max-width:770px;line-height:1.65;margin:0 0 25px}}
.pills{{display:flex;flex-wrap:wrap;gap:9px;margin:20px 0 32px}}
.pill{{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:5px;padding:5px 10px;color:#354354;font-weight:600}}
.pill.ch{{border-color:#CAD7EE;color:#244993;background:#F5F8FD}}
.sep{{border-top:1px solid var(--line);margin:35px 0}}
.stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid var(--line);border-radius:9px;overflow:hidden}}
.stat{{padding:26px 24px;border-right:1px solid var(--line)}}.stat:last-child{{border-right:0}}
.big{{font-size:36px;font-weight:670;letter-spacing:-.045em}}
.small{{font-size:12px;color:var(--muted);line-height:1.5}}
.grid{{display:grid;grid-template-columns:1.45fr 1fr;gap:38px;margin-top:55px}}
h2{{font-size:22px;letter-spacing:-.025em;margin:0 0 17px}}
p{{margin:0 0 16px}}
.rows{{border-top:1px solid var(--line)}}
.item{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;border-bottom:1px solid var(--line);padding:15px 0}}
.item span:first-child{{font-size:14px}}.status{{font:600 11px ui-monospace,monospace;white-space:nowrap;color:#476077}}
.note{{background:var(--soft);border:1px solid var(--line);border-radius:7px;padding:20px;margin-top:25px;font-size:14px}}
aside{{border:1px solid var(--line);padding:24px;border-radius:9px;align-self:start}}
aside a{{display:block;font-size:14px;margin:8px 0 12px;overflow-wrap:anywhere}}
pre{{overflow:auto;white-space:pre-wrap;word-break:break-word;font:12px/1.6 ui-monospace,SFMono-Regular,monospace;color:#475467;background:var(--soft);padding:12px;border-radius:5px}}
footer{{border-top:1px solid var(--line);padding:30px 0;font-size:13px;color:var(--muted)}}
@media(max-width:740px){{.grid{{grid-template-columns:1fr;gap:24px}}.stats{{grid-template-columns:1fr}}.stat{{border-right:0;border-bottom:1px solid var(--line)}}.stat:last-child{{border:0}}main{{padding-top:38px}}}}
</style></head><body>
<header><div class="shell"><nav>
<a class="brand" href="/" aria-label="MathGraph"><span class="dot">M</span>MathGraph</a>
<span class="rhs">Check / Research record</span>
</nav></div></header>
<main class="shell">
<div class="kicker">Pinned external evidence · 10 October 2026</div>
<h1>Know what this check establishes.</h1>
<p class="lead">Independent, source-pinned observations of the L4YAML parser.
The finite results are reproducible. Broader correctness remains an explicit open question.</p>
<div class="pills"><span class="pill ch">52 source-bound Lean guards passed</span>
<span class="pill">Universal theorem: UNKNOWN</span><span class="pill">No project endorsement</span></div>
<div class="stats">
<div class="stat"><div class="big">48/48</div><div class="small">Independent YAML case decisions matched<br>31 accepts / 17 rejects</div></div>
<div class="stat"><div class="big">52/52</div><div class="small">Pinned Lean executable guards passed<br>4 targeted extra controls</div></div>
<div class="stat"><div class="big">UNKNOWN</div><div class="small">Universal source-to-parser equivalence<br>Not established by this record</div></div>
</div>
<div class="grid">
<section>
<h2>Exactly what was checked</h2>
<p>MathGraph replayed a fixed independent YAML test set against the original,
pinned Lean parser function and separately checked the upstream source's
named serialization lemmas. Its prior compiled command-line run remains
an independent historical observation.</p>
<div class="rows">
<div class="item"><span>External test-suite acceptance</span><span class="status">48/48 REPLAYED</span></div>
<div class="item"><span>Lean executable source guards</span><span class="status">52/52 PASSED</span></div>
<div class="item"><span>Known cyclic-anchor behavior</span><span class="status">SCOPED DISTINCTION</span></div>
<div class="item"><span>Whole YAML language correctness</span><span class="status">UNKNOWN</span></div>
<div class="item"><span>Natural-language statement fidelity</span><span class="status">UNKNOWN</span></div>
<div class="item"><span>Requalification against future commits</span><span class="status">NOT CHECKED</span></div>
</div>
<div class="note"><strong>An important distinction.</strong>
The input <code>&amp;x [*x]</code> is accepted by the restricted early-anchor
event model but rejected by this pinned version of L4YAML. This difference
was already documented by its contributors. The correspondence from all
possible YAML inputs to event traces is not proved here.</div>
</section><aside><h2>Independent evidence</h2>
<div class="small">Original projects are credited as sources, not endorsers.</div>
<a href="{escape(jpl)}">Pinned original L4YAML source ↗</a>
<a href="{escape(suite)}">Pinned independent YAML test suite ↗</a>
<a href="{escape(orig)}">Compiled parser + original Lean proofs ↗</a>
<a href="{escape(norm)}">Decoded 48-case native Lean replay ↗</a>
<div class="sep"></div>
<div class="small">Exact JPL commit</div><pre>{exact}</pre>
<div class="small">Read-only record SHA-256</div><pre>{proof}</pre>
<div class="small">Agent endpoints</div>
<a href="/v1/records/{RECORD_ID}">JSON record ↗</a>
<a href="/v1/records/{RECORD_ID}/evidence">Evidence references ↗</a>
<a href="/v1/badges/{RECORD_ID}.svg">Scoped SVG status mark ↗</a>
</aside></div>
</main><footer><div class="shell">MathGraph · Independently checkable,
boundary-preserving research evidence. Built by Metalogic Labs.</div></footer>
</body></html>"""


def build_site(v1_path: Path, v2_path: Path, out_dir: Path) -> dict:
    record = build_record(v1_path, v2_path)
    _release_integrity(record)
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "evidence.json").write_text(
        json.dumps(record["evidence"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "index.html").write_text(render_html(record), encoding="utf-8")
    (target / "badge.svg").write_text(render_badge(record), encoding="utf-8")
    (target / "openapi.json").write_text(
        json.dumps(openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return record


def openapi() -> dict:
    return {
        "openapi": "3.1.0",
        "info": {"title": "MathGraph Check — read-only evidence API", "version": "0.1"},
        "servers": [{"url": "http://127.0.0.1:8796",
                     "description": "Local development only; no hosted API is claimed"}],
        "paths": {
            "/v1/records/" + RECORD_ID: {
                "get": {"summary": "Read the pinned L4YAML research record",
                        "responses": {"200": {"description": "Immutable snapshot"}}},
            },
            "/v1/records/" + RECORD_ID + "/evidence": {
                "get": {"summary": "Read exact upstream evidence references",
                        "responses": {"200": {"description": "Source receipts"}}},
            },
            "/v1/badges/" + RECORD_ID + ".svg": {
                "get": {"summary": "Only scoped finite-case status, not theorem truth",
                        "responses": {"200": {"description": "SVG scoped status"}}},
            },
            "/v1/resolve": {
                "post": {
                    "summary": "Resolve only a pinned scope-qualified consequence; no mutation",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "required": ["record_id", "source_commit",
                                         "external_suite_commit", "goal"],
                            "properties": {
                                "record_id": {"const": RECORD_ID},
                                "source_commit": {"const": JPL_COMMIT},
                                "external_suite_commit": {"const": SUITE_COMMIT},
                                "goal": {"type": "string"},
                            },
                            "additionalProperties": False,
                        }}},
                    },
                    "responses": {
                        "200": {"description": "WARRANTED_BOUNDED or explicit UNKNOWN"},
                        "400": {"description": "Invalid typed query"},
                    },
                },
            },
        },
    }


def cli() -> None:
    p = argparse.ArgumentParser(
        description="Build a read-only MathGraph Check release from pinned CI ZIPs"
    )
    p.add_argument("--v1-zip", type=Path, required=True)
    p.add_argument("--v2-zip", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    record = build_site(args.v1_zip, args.v2_zip, args.out)
    print(json.dumps({
        "record_id": RECORD_ID,
        "record_sha256": record["content_sha256"],
        "finite_case_checks": 48,
        "additional_guards": 4,
        "universal_yaml_theorem": "UNKNOWN",
        "badge_kind": "FINITE_CASES_ONLY",
        "out": str(args.out),
    }, sort_keys=True))


if __name__ == "__main__":
    cli()
