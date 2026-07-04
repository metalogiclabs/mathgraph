import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_3_missing_manifest_backfill_planner.py"
QUEUE_RUNNER = ROOT / "experiments/sorrydb/sorrydb_v4_3_5_json_patch_queue_runner.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(
    root: Path,
    *,
    source_snippet: str = "example : True := by\n  sorry",
    patch_snippet: str | None = "example : True := by\n  trivial",
    source_text: str | None = None,
    create_source: bool = True,
) -> tuple[Path, Path, Path]:
    repo_root = root / "repo"
    source = repo_root / "Example.lean"
    if create_source:
        repo_root.mkdir(parents=True, exist_ok=True)
        source.write_text(
            source_text if source_text is not None else f"namespace Fixture\n{source_snippet}\nend Fixture\n",
            encoding="utf-8",
        )

    certificate = {
        "certificate_id": "missing-manifest-case",
        "certificate_version": "v4.test",
        "final_verdict": "PATCH_ACCEPTED",
        "lean_returncode": 0,
        "project": "fixture/project",
        "project_commit": "abc123",
        "repo_root": str(repo_root),
        "file_path": "Example.lean",
        "source_snippet": source_snippet,
        "restore_check": "source restored after replay",
    }
    if patch_snippet is not None:
        certificate["patch_snippet"] = patch_snippet
    certificate_path = root / "certificates" / "missing-manifest-case.json"
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    certificate_path.write_text(json.dumps(certificate), encoding="utf-8")

    profile = {
        "version": "v4.4.2",
        "candidates": [],
        "obstructions": [
            {
                "terminal_form": "NAMED_OBSTRUCTION",
                "category": "MISSING_MANIFEST",
                "evidence_id": "missing-manifest-case",
                "manifest_paths": [],
                "certificate_paths": [str(certificate_path)],
            }
        ],
    }
    profile_path = root / "profile.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    return profile_path, certificate_path, source


def plan_one(mod, root: Path, profile_path: Path):
    return mod.plan_backfills(
        profile_path,
        reference_dirs=[root],
        source_roots=[root],
    )


def test_ready_row_emits_queue_candidate(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_ready")
    profile_path, _, _ = write_fixture(tmp_path)
    summary, plan = plan_one(mod, tmp_path, profile_path)
    assert summary["backfill_ready_count"] == 1
    assert summary["category_counts"][mod.BACKFILL_REPLAY_READY] == 1
    candidate = plan["ready_candidates"][0]
    for key in (
        "candidate_id",
        "repo_root",
        "file_path",
        "source_snippet",
        "patch_snippet",
        "timeout_seconds",
        "queue_timeout_seconds",
        "provenance",
    ):
        assert key in candidate


def test_missing_source_file_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_missing_source")
    profile_path, _, _ = write_fixture(tmp_path, create_source=False)
    summary, _ = plan_one(mod, tmp_path, profile_path)
    assert summary["category_counts"][mod.BACKFILL_BLOCKED_SOURCE_MISSING] == 1


def test_ambiguous_source_snippet_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_ambiguous")
    snippet = "example : True := by\n  sorry"
    profile_path, _, _ = write_fixture(
        tmp_path,
        source_snippet=snippet,
        source_text=f"{snippet}\n{snippet}\n",
    )
    summary, _ = plan_one(mod, tmp_path, profile_path)
    assert summary["category_counts"][mod.BACKFILL_BLOCKED_SOURCE_SNIPPET_AMBIGUOUS] == 1


def test_no_sorry_in_source_snippet_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_no_sorry")
    profile_path, _, _ = write_fixture(
        tmp_path,
        source_snippet="example : True := by\n  trivial",
        patch_snippet="example : True := by\n  exact True.intro",
    )
    summary, _ = plan_one(mod, tmp_path, profile_path)
    assert summary["category_counts"][mod.BACKFILL_BLOCKED_NO_SORRY_IN_SOURCE_SNIPPET] == 1


def test_multiple_sorries_in_source_snippet_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_many_sorries")
    profile_path, _, _ = write_fixture(
        tmp_path,
        source_snippet="example : True := by\n  have h : True := by sorry\n  sorry",
    )
    summary, _ = plan_one(mod, tmp_path, profile_path)
    assert summary["category_counts"][mod.BACKFILL_BLOCKED_MULTIPLE_SORRIES_IN_SOURCE_SNIPPET] == 1


def test_missing_patch_snippet_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_no_patch")
    profile_path, _, _ = write_fixture(tmp_path, patch_snippet=None)
    summary, _ = plan_one(mod, tmp_path, profile_path)
    assert summary["category_counts"][mod.BACKFILL_BLOCKED_PATCH_SNIPPET_MISSING] == 1


def test_summary_counts_are_stable(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_counts")
    profile_path, _, _ = write_fixture(tmp_path)
    summary, _ = plan_one(mod, tmp_path, profile_path)
    assert list(summary["category_counts"]) == list(mod.CATEGORIES)
    assert sum(summary["category_counts"].values()) == summary["missing_manifest_count"]
    assert summary["backfill_ready_count"] + summary["blocked_count"] == 1


def test_emitted_backfill_queue_is_runner_compatible(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v443_queue")
    queue_runner = load_module(QUEUE_RUNNER, "sorrydb_v435_for_v443")
    profile_path, _, _ = write_fixture(tmp_path)
    summary, plan = plan_one(mod, tmp_path, profile_path)
    output = tmp_path / "output"
    mod.write_outputs(output, summary, plan)
    queue_path = output / "backfill_queue.json"
    assert queue_path.exists()
    candidates, obstruction = queue_runner.load_queue(queue_path)
    assert obstruction == ""
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"].startswith("v443-backfill-")
