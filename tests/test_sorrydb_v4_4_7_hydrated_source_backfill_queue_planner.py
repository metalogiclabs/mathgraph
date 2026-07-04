import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_7_hydrated_source_backfill_queue_planner.py"
QUEUE_RUNNER = ROOT / "experiments/sorrydb/sorrydb_v4_3_5_json_patch_queue_runner.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_fixture(
    root: Path,
    *,
    source_snippet: str = "example : True := by\n  sorry",
    patch_snippet: str = "example : True := by\n  trivial",
    occurrence_count: int = 1,
    hydration_status: str = "SOURCE_HYDRATED_VERIFIED",
):
    cache = root / "cache"
    target = cache / "MetaExamples" / "Fiddle.lean"
    target.parent.mkdir(parents=True)
    target.write_text("\n".join([source_snippet] * max(1, occurrence_count)) + "\n", encoding="utf-8")
    source_hash = digest(source_snippet)
    patch_hash = digest(patch_snippet) if patch_snippet else ""
    row_id = "hydrated-row"

    hydration_summary = {
        "controlled_cache_path": str(cache),
        "status": "CONTROLLED_SOURCE_HYDRATION_LEDGERED",
    }
    hydration_ledger = {
        "rows": [{
            "row_id": row_id,
            "file_path": "MetaExamples/Fiddle.lean",
            "status": hydration_status,
        }]
    }
    verified = [{
        "row_id": row_id,
        "file_path": "MetaExamples/Fiddle.lean",
        "source_snippet_sha256": source_hash,
        "patch_snippet_sha256": patch_hash,
        "source_snippet_occurrence_count": occurrence_count,
        "source_snippet_line_start": 1,
        "source_snippet_line_end": source_snippet.count("\n") + 1,
        "status": hydration_status,
    }]
    registration = {
        "rows": [{
            "row_id": row_id,
            "certificate_id": "fixture-certificate",
            "file_path": "MetaExamples/Fiddle.lean",
            "source_snippet_sha256": source_hash,
            "patch_snippet_sha256": patch_hash,
            "repo_url": "https://example.test/fixture",
            "commit": "abc123",
        }]
    }
    snippet = {
        "row_id": row_id,
        "file_path": "MetaExamples/Fiddle.lean",
        "source_snippet": source_snippet,
        "source_snippet_sha256": source_hash,
        "patch_snippet": patch_snippet,
        "patch_snippet_sha256": patch_hash,
    }

    paths = {
        "summary": root / "hydration_summary.json",
        "ledger": root / "hydration_ledger.json",
        "files": root / "file_hashes.json",
        "verified": root / "verified_snippets.json",
        "registration": root / "registration_plan.json",
        "prior": root / "prior_backfill_plan.json",
        "snippets": root / "source_snippets",
    }
    paths["snippets"].mkdir()
    values = {
        "summary": hydration_summary,
        "ledger": hydration_ledger,
        "files": [{"file_path": "MetaExamples/Fiddle.lean"}],
        "verified": verified,
        "registration": registration,
        "prior": {"blocked_rows": []},
    }
    for key, value in values.items():
        paths[key].write_text(json.dumps(value), encoding="utf-8")
    (paths["snippets"] / "hydrated-row.json").write_text(json.dumps(snippet), encoding="utf-8")
    return paths


def run_plan(mod, paths):
    return mod.plan_queue(
        paths["summary"],
        paths["ledger"],
        paths["files"],
        paths["verified"],
        paths["registration"],
        paths["snippets"],
        paths["prior"],
    )


def test_verified_one_sorry_row_is_ready(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_ready")
    summary, plan, queue = run_plan(mod, write_fixture(tmp_path))
    assert summary["backfill_ready_count"] == 1
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_READY] == 1
    candidate = plan["ready_candidates"][0]
    assert candidate["timeout_seconds"] == 240
    assert candidate["queue_timeout_seconds"] == 600
    assert candidate["required_gb"] == 5.0
    assert candidate["certificate_version"] == ""
    assert queue["candidates"] == plan["ready_candidates"]


def test_original_certificate_version_is_preserved():
    mod = load_module(SCRIPT, "sorrydb_v447_version")
    assert mod.certificate_version_from_id("sorrydb-v4-3-2-example") == "v4.3.2"
    assert mod.certificate_version_from_id("sorrydb-v4-3-4-example") == "v4.3.4"


def test_ambiguous_occurrence_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_ambiguous")
    summary, _, _ = run_plan(mod, write_fixture(tmp_path, occurrence_count=2))
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_BLOCKED_SNIPPET_AMBIGUOUS] == 1


def test_source_snippet_with_no_sorry_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_no_sorry")
    summary, _, _ = run_plan(
        mod,
        write_fixture(tmp_path, source_snippet="example : True := by\n  trivial"),
    )
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_BLOCKED_NO_SORRY] == 1


def test_source_snippet_with_two_sorries_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_many_sorries")
    summary, _, _ = run_plan(
        mod,
        write_fixture(
            tmp_path,
            source_snippet="example : True := by\n  have h : True := by sorry\n  sorry",
        ),
    )
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_BLOCKED_MULTIPLE_SORRIES] == 1


def test_patch_containing_sorry_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_patch_sorry")
    summary, _, _ = run_plan(
        mod,
        write_fixture(tmp_path, patch_snippet="example : True := by\n  sorry"),
    )
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_BLOCKED_PATCH_CONTAINS_SORRY] == 1


def test_missing_patch_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_missing_patch")
    summary, _, _ = run_plan(mod, write_fixture(tmp_path, patch_snippet=""))
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_BLOCKED_MISSING_PATCH] == 1


def test_unverified_hydration_is_blocked(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_unverified")
    summary, _, _ = run_plan(
        mod,
        write_fixture(tmp_path, hydration_status="SOURCE_HYDRATED_FILE_MISSING"),
    )
    assert summary["category_counts"][mod.HYDRATED_BACKFILL_BLOCKED_NOT_VERIFIED] == 1


def test_summary_counts_are_stable(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_counts")
    summary, _, _ = run_plan(mod, write_fixture(tmp_path))
    assert list(summary["category_counts"]) == list(mod.CATEGORIES)
    assert sum(summary["category_counts"].values()) == summary["hydrated_row_count"]
    assert summary["backfill_ready_count"] + summary["blocked_count"] == 1


def test_emitted_queue_is_runner_compatible(tmp_path):
    mod = load_module(SCRIPT, "sorrydb_v447_queue")
    runner = load_module(QUEUE_RUNNER, "sorrydb_v435_for_v447")
    summary, plan, queue = run_plan(mod, write_fixture(tmp_path))
    output = tmp_path / "output"
    mod.write_outputs(output, summary, plan, queue)
    candidates, obstruction = runner.load_queue(output / "backfill_queue.json")
    assert obstruction == ""
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == "v447-backfill-fixture-certificate"
