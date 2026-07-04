import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_4_controlled_source_input_ledger.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v444_source_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(
    root: Path,
    *,
    repo_root: str,
    source_snippet: str | None = "example : True := by\n  sorry",
    patch_snippet: str | None = "example : True := by\n  trivial",
) -> tuple[Path, Path]:
    certificate = {
        "certificate_id": "source-input-case",
        "certificate_version": "v4.test",
        "final_verdict": "PATCH_ACCEPTED",
        "lean_returncode": 0,
        "repo_root": repo_root,
        "file_path": "Example.lean",
        "project": "fixture/project",
        "project_commit": "abc123",
    }
    if source_snippet is not None:
        certificate["source_snippet"] = source_snippet
    if patch_snippet is not None:
        certificate["patch_snippet"] = patch_snippet
    certificate_path = root / "certificates" / "source-input-case.json"
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    certificate_path.write_text(json.dumps(certificate), encoding="utf-8")

    plan = {
        "version": "v4.4.3",
        "ready_candidates": [],
        "blocked_rows": [
            {
                "terminal_form": "NAMED_OBSTRUCTION",
                "category": "BACKFILL_BLOCKED_SOURCE_MISSING",
                "evidence_id": "source-input-case",
                "certificate_path": str(certificate_path),
            }
        ],
    }
    plan_path = root / "backfill_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return plan_path, certificate_path


def build_one(mod, root: Path, plan_path: Path, controlled_dirs: list[Path]):
    return mod.build_ledger(
        plan_path,
        reference_dirs=[root],
        controlled_source_dirs=controlled_dirs,
    )


def test_controlled_checked_in_source_is_available(tmp_path):
    mod = load_module()
    controlled = tmp_path / "controlled"
    repo = controlled / "repo"
    repo.mkdir(parents=True)
    source_snippet = "example : True := by\n  sorry"
    (repo / "Example.lean").write_text(source_snippet + "\n", encoding="utf-8")
    plan_path, _ = write_fixture(
        tmp_path / "evidence",
        repo_root=str(repo),
        source_snippet=source_snippet,
    )
    summary, ledger, _ = build_one(mod, tmp_path, plan_path, [controlled])
    assert summary["source_checkout_available_count"] == 1
    assert ledger["rows"][0]["source_input_status"] == mod.SOURCE_CHECKOUT_AVAILABLE
    assert ledger["rows"][0]["known_repo_root_is_stable"] is True


def test_tmp_repo_root_is_path_unstable_but_snippet_is_preserved(tmp_path):
    mod = load_module()
    plan_path, _ = write_fixture(
        tmp_path,
        repo_root="/tmp/nonexistent-sorrydb-checkout",
    )
    summary, ledger, snippets = build_one(mod, tmp_path, plan_path, [tmp_path / "controlled"])
    assert summary["category_counts"][mod.SOURCE_CHECKOUT_PATH_UNSTABLE] == 1
    assert ledger["rows"][0]["known_repo_root_is_stable"] is False
    assert len(snippets) == 1


def test_missing_snippet_is_insufficient(tmp_path):
    mod = load_module()
    plan_path, _ = write_fixture(
        tmp_path,
        repo_root="",
        source_snippet=None,
    )
    summary, ledger, _ = build_one(mod, tmp_path, plan_path, [tmp_path / "controlled"])
    assert summary["source_input_insufficient_count"] == 1
    assert ledger["rows"][0]["source_input_status"] == mod.SOURCE_INPUT_INSUFFICIENT


def test_snippet_json_contains_sha256_hashes(tmp_path):
    mod = load_module()
    source_snippet = "example : True := by\n  sorry"
    patch_snippet = "example : True := by\n  trivial"
    plan_path, _ = write_fixture(
        tmp_path / "evidence",
        repo_root="/tmp/unstable",
        source_snippet=source_snippet,
        patch_snippet=patch_snippet,
    )
    summary, ledger, snippets = build_one(
        mod,
        tmp_path,
        plan_path,
        [tmp_path / "controlled"],
    )
    output = tmp_path / "output"
    mod.write_outputs(output, summary, ledger, snippets)
    snippet_files = list((output / "source_snippets").glob("*.json"))
    assert len(snippet_files) == 1
    payload = json.loads(snippet_files[0].read_text(encoding="utf-8"))
    assert payload["source_snippet_sha256"] == hashlib.sha256(source_snippet.encode()).hexdigest()
    assert payload["patch_snippet_sha256"] == hashlib.sha256(patch_snippet.encode()).hexdigest()


def test_category_counts_are_stable(tmp_path):
    mod = load_module()
    plan_path, _ = write_fixture(tmp_path, repo_root="/tmp/unstable")
    summary, _, _ = build_one(mod, tmp_path, plan_path, [tmp_path / "controlled"])
    assert list(summary["category_counts"]) == list(mod.CATEGORIES)
    assert sum(summary["category_counts"].values()) == 1
    assert summary["blocked_source_missing_count"] == 1


def test_summary_records_bounded_claim_and_nonclaims(tmp_path):
    mod = load_module()
    plan_path, _ = write_fixture(tmp_path, repo_root="/tmp/unstable")
    summary, _, _ = build_one(mod, tmp_path, plan_path, [tmp_path / "controlled"])
    assert "controlled source-input statuses" in summary["bounded_claim"]
    assert "new proof discovery" in summary["does_not_claim"]
    assert "source hydration" in summary["does_not_claim"]
    assert "Lean replay success" in summary["does_not_claim"]


def test_missing_backfill_plan_records_note_without_crashing(tmp_path):
    mod = load_module()
    missing = tmp_path / "missing-plan.json"
    summary, ledger, snippets = mod.build_ledger(
        missing,
        reference_dirs=[],
        controlled_source_dirs=[tmp_path / "controlled"],
    )
    assert summary["blocked_source_missing_count"] == 0
    assert ledger["rows"] == []
    assert snippets == {}
    assert any("missing backfill plan" in note for note in ledger["notes"])
