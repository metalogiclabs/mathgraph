import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_6_controlled_source_hydration_ledger.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v446_hydration", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def create_repo(root: Path, source_text: str) -> tuple[Path, str]:
    repo = root / "source-repo"
    repo.mkdir(parents=True)
    git(repo, "init")
    git(repo, "config", "user.email", "fixture@example.test")
    git(repo, "config", "user.name", "Fixture")
    target = repo / "MetaExamples" / "Fiddle.lean"
    target.parent.mkdir()
    target.write_text(source_text, encoding="utf-8")
    git(repo, "add", "MetaExamples/Fiddle.lean")
    git(repo, "commit", "-m", "fixture")
    return repo, git(repo, "rev-parse", "HEAD")


def row_and_snippet(source_snippet: str, patch_snippet: str):
    row = {
        "row_id": "fixture-row",
        "registration_status": "REGISTRATION_NEEDS_NETWORK_HYDRATION",
        "repo_url": "fixture-repo",
        "commit": "fixture-commit",
        "file_path": "MetaExamples/Fiddle.lean",
        "source_snippet_sha256": hashlib.sha256(source_snippet.encode()).hexdigest(),
        "patch_snippet_sha256": hashlib.sha256(patch_snippet.encode()).hexdigest(),
    }
    snippet = {
        "row_id": "fixture-row",
        "file_path": "MetaExamples/Fiddle.lean",
        "source_snippet": source_snippet,
        "source_snippet_sha256": row["source_snippet_sha256"],
        "patch_snippet": patch_snippet,
        "patch_snippet_sha256": row["patch_snippet_sha256"],
    }
    return row, snippet


def test_local_pinned_repo_hydrates_and_verifies(tmp_path):
    mod = load_module()
    source_snippet = "example : True := by\n  sorry"
    patch_snippet = "example : True := by\n  trivial"
    repo, commit = create_repo(tmp_path, f"namespace T\n{source_snippet}\nend T\n")
    row, snippet = row_and_snippet(source_snippet, patch_snippet)
    row["repo_url"] = str(repo)
    row["commit"] = commit
    plan = {"rows": [row]}
    plan_path = tmp_path / "registration_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    snippet_dir = tmp_path / "snippets"
    snippet_dir.mkdir()
    (snippet_dir / "fixture-row.json").write_text(json.dumps(snippet), encoding="utf-8")

    summary, ledger, files, verified = mod.execute_hydration(
        plan_path,
        plan_summary_path=None,
        fixture_plan_path=None,
        snippet_dir=snippet_dir,
        cache_root=tmp_path / "cache",
        allowed_pairs={(str(repo), commit)},
    )
    assert summary["source_hydrated_verified_count"] == 1
    assert ledger["actual_commit"] == commit
    assert ledger["rows"][0]["status"] == mod.SOURCE_HYDRATED_VERIFIED
    assert len(files) == 1
    assert verified[0]["source_snippet_occurrence_count"] == 1


def test_missing_file(tmp_path):
    mod = load_module()
    row, snippet = row_and_snippet("by\n  sorry", "by\n  trivial")
    rows, _, _, counts = mod.verify_rows(
        [row], {"fixture-row": snippet}, tmp_path, "abc", "abc"
    )
    assert rows[0]["status"] == mod.SOURCE_HYDRATED_FILE_MISSING
    assert counts[mod.SOURCE_HYDRATED_FILE_MISSING] == 1


def test_snippet_not_found(tmp_path):
    mod = load_module()
    target = tmp_path / "MetaExamples" / "Fiddle.lean"
    target.parent.mkdir()
    target.write_text("example : False := by\n  sorry\n", encoding="utf-8")
    row, snippet = row_and_snippet("example : True := by\n  sorry", "example : True := by\n  trivial")
    rows, _, verified, _ = mod.verify_rows(
        [row], {"fixture-row": snippet}, tmp_path, "abc", "abc"
    )
    assert rows[0]["status"] == mod.SOURCE_HYDRATED_SNIPPET_NOT_FOUND
    assert verified[0]["source_snippet_occurrence_count"] == 0


def test_snippet_ambiguous(tmp_path):
    mod = load_module()
    source = "example : True := by\n  sorry"
    target = tmp_path / "MetaExamples" / "Fiddle.lean"
    target.parent.mkdir()
    target.write_text(f"{source}\n{source}\n", encoding="utf-8")
    row, snippet = row_and_snippet(source, "example : True := by\n  trivial")
    rows, _, verified, _ = mod.verify_rows(
        [row], {"fixture-row": snippet}, tmp_path, "abc", "abc"
    )
    assert rows[0]["status"] == mod.SOURCE_HYDRATED_SNIPPET_AMBIGUOUS
    assert verified[0]["source_snippet_occurrence_count"] == 2


def test_snippet_hash_mismatch(tmp_path):
    mod = load_module()
    source = "example : True := by\n  sorry"
    target = tmp_path / "MetaExamples" / "Fiddle.lean"
    target.parent.mkdir()
    target.write_text(source, encoding="utf-8")
    row, snippet = row_and_snippet(source, "example : True := by\n  trivial")
    row["source_snippet_sha256"] = "0" * 64
    rows, _, _, _ = mod.verify_rows(
        [row], {"fixture-row": snippet}, tmp_path, "abc", "abc"
    )
    assert rows[0]["status"] == mod.SOURCE_HYDRATED_SNIPPET_HASH_MISMATCH


def test_commit_mismatch(tmp_path):
    mod = load_module()
    row, snippet = row_and_snippet("by\n  sorry", "by\n  trivial")
    rows, _, _, _ = mod.verify_rows(
        [row], {"fixture-row": snippet}, tmp_path, "expected", "actual"
    )
    assert rows[0]["status"] == mod.SOURCE_HYDRATED_COMMIT_MISMATCH


def test_summary_counts_are_stable():
    mod = load_module()
    counts = {category: 0 for category in mod.CATEGORIES}
    counts[mod.SOURCE_HYDRATED_VERIFIED] = 1
    counts[mod.SOURCE_HYDRATED_FILE_MISSING] = 1
    summary = mod.make_summary("repo", "commit", "cache", ["a", "b"], counts)
    assert list(summary["category_counts"]) == list(mod.CATEGORIES)
    assert summary["source_hydrated_verified_count"] == 1
    assert summary["blocked_count"] == 1


def test_missing_registration_plan_records_missing_input(tmp_path):
    mod = load_module()
    missing = tmp_path / "missing-plan.json"
    summary, ledger, files, verified = mod.execute_hydration(
        missing,
        plan_summary_path=None,
        fixture_plan_path=None,
        snippet_dir=tmp_path / "snippets",
        cache_root=tmp_path / "cache",
        allowed_pairs=set(),
    )
    assert summary["hydrated_row_count"] == 0
    assert files == []
    assert verified == []
    assert any("missing registration plan" in note for note in ledger["notes"])
