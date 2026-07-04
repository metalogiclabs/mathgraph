import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_2_miner_coverage_profiler.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v442_profiler", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_case(
    root: Path,
    *,
    evidence_id: str = "case-1",
    source_snippet: str = "example : True := by\n  sorry",
    patch_snippet: str = "example : True := by\n  trivial",
    source_text: str | None = None,
    include_manifest: bool = True,
    include_certificate: bool = True,
) -> tuple[Path, Path]:
    source = root / "repo" / "Example.lean"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        source_text if source_text is not None else f"namespace Fixture\n{source_snippet}\nend Fixture\n",
        encoding="utf-8",
    )
    if include_manifest:
        manifest = {
            "patch_certificate_id": evidence_id,
            "verdict": "PATCH_ACCEPTED",
            "patch_verdict": "PATCH_ACCEPTED",
            "patch_result": {"returncode": 0},
            "repo_root": str(source.parent),
            "source": str(source),
            "file_path": "Example.lean",
            "source_snippet": source_snippet,
            "patch_snippet": patch_snippet,
        }
        path = root / "manifests" / f"{evidence_id}.manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest), encoding="utf-8")
    if include_certificate:
        certificate = {
            "certificate_id": evidence_id,
            "final_verdict": "PATCH_ACCEPTED",
            "lean_returncode": 0,
            "file_path": "Example.lean",
            "source_snippet": source_snippet,
            "patch_snippet": patch_snippet,
        }
        path = root / "certificates" / f"{evidence_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(certificate), encoding="utf-8")
    return root, source


def profile_one(mod, root: Path, *, span_line: int = 3):
    return mod.profile_evidence(
        [root],
        source_roots=[root],
        known_spans_by_file={
            "Example.lean": [{"start_line": span_line, "end_line": span_line}]
        },
    )


def test_accepted_pair_unique_source_and_known_span_is_mined(tmp_path):
    mod = load_module()
    root, _ = write_case(tmp_path)
    summary, profile = profile_one(mod, root)
    assert summary["mined_candidate_count"] == 1
    assert summary["category_counts"][mod.MINED_CANDIDATE] == 1
    assert profile["candidates"][0]["category"] == mod.MINED_CANDIDATE


def test_missing_certificate(tmp_path):
    mod = load_module()
    root, _ = write_case(tmp_path, include_certificate=False)
    summary, profile = profile_one(mod, root)
    assert summary["category_counts"][mod.MISSING_CERTIFICATE] == 1
    assert profile["obstructions"][0]["category"] == mod.MISSING_CERTIFICATE


def test_source_snippet_occurs_twice(tmp_path):
    mod = load_module()
    snippet = "example : True := by\n  sorry"
    root, _ = write_case(tmp_path, source_snippet=snippet, source_text=f"{snippet}\n{snippet}\n")
    summary, _ = profile_one(mod, root, span_line=2)
    assert summary["category_counts"][mod.SOURCE_SNIPPET_AMBIGUOUS] == 1


def test_source_snippet_has_no_sorry(tmp_path):
    mod = load_module()
    snippet = "example : True := by\n  trivial"
    root, _ = write_case(
        tmp_path,
        source_snippet=snippet,
        patch_snippet="example : True := by\n  exact True.intro",
    )
    summary, _ = profile_one(mod, root)
    assert summary["category_counts"][mod.NO_SORRY_IN_SOURCE_SNIPPET] == 1


def test_source_snippet_has_two_sorries(tmp_path):
    mod = load_module()
    snippet = "example : True := by\n  have h : True := by sorry\n  sorry"
    root, _ = write_case(tmp_path, source_snippet=snippet)
    summary, _ = profile_one(mod, root)
    assert summary["category_counts"][mod.MULTIPLE_SORRIES_IN_SOURCE_SNIPPET] == 1


def test_sorry_outside_known_span(tmp_path):
    mod = load_module()
    root, _ = write_case(tmp_path)
    summary, _ = profile_one(mod, root, span_line=99)
    assert summary["category_counts"][mod.SORRY_OUTSIDE_KNOWN_SPAN] == 1


def test_malformed_json_becomes_named_obstruction(tmp_path):
    mod = load_module()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    summary, profile = mod.profile_evidence([tmp_path], source_roots=[tmp_path])
    assert summary["obstruction_count"] == 1
    assert summary["category_counts"][mod.UNCLASSIFIED_OBSTRUCTION] == 1
    assert profile["obstructions"][0]["terminal_form"] == "NAMED_OBSTRUCTION"


def test_summary_category_counts_are_stable(tmp_path):
    mod = load_module()
    write_case(tmp_path / "accepted", evidence_id="accepted")
    write_case(
        tmp_path / "missing-certificate",
        evidence_id="missing-certificate",
        include_certificate=False,
    )
    summary, _ = mod.profile_evidence(
        [tmp_path],
        source_roots=[tmp_path],
        known_spans_by_file={
            "Example.lean": [{"start_line": 3, "end_line": 3}]
        },
    )
    assert list(summary["category_counts"]) == list(mod.CATEGORIES)
    assert summary["category_counts"][mod.MINED_CANDIDATE] == 1
    assert summary["category_counts"][mod.MISSING_CERTIFICATE] == 1
    assert sum(summary["category_counts"].values()) == 2


def test_duplicate_certificates_are_grouped(tmp_path):
    mod = load_module()
    root, _ = write_case(tmp_path)
    original = root / "certificates" / "case-1.json"
    duplicate = root / "other" / "case-1-copy.json"
    duplicate.parent.mkdir()
    duplicate.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
    _, profile = profile_one(mod, root)
    assert profile["duplicate_groups"] == [
        {
            "kind": "certificate",
            "evidence_id": "case-1",
            "count": 2,
            "paths": sorted([str(original), str(duplicate)]),
        }
    ]
