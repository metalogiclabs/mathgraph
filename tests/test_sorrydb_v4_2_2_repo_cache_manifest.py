import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_2_declaration_retrieval_patcher.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v422", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_repo_cache_key_is_stable_and_safe():
    mod = load_module()
    key = mod.safe_repo_cache_key("https://github.com/siddhartha-gadgil/MetaExamples.git", "edbb75e784db19846a1c")
    assert key.startswith("siddhartha-gadgil__MetaExamples__edbb75e784d")
    assert "/" not in key
    assert ":" not in key


def test_manifest_row_reports_repo_not_cached(tmp_path):
    mod = load_module()
    target = mod.SorryTarget(
        repo="https://github.com/siddhartha-gadgil/MetaExamples",
        commit="edbb75e784db19846a1c19841e182b797afc18bb",
        lean_version="v4.22.0",
        file_path="MetaExamples/Fiddle.lean",
        line=79,
        statement="0 + 2 ≤ 0 + 4",
    )
    row = mod.build_manifest_row(target, tmp_path / "cache")
    assert row["repo_cached"] is False
    assert row["source_exists"] is False
    assert row["obstruction"] == mod.OBSTRUCTED_REPO_NOT_CACHED


def test_manifest_row_reports_missing_file_when_repo_exists(tmp_path):
    mod = load_module()
    target = mod.SorryTarget(
        repo="https://github.com/siddhartha-gadgil/MetaExamples",
        commit="edbb75e784db19846a1c19841e182b797afc18bb",
        file_path="MetaExamples/Fiddle.lean",
        line=79,
    )
    repo = mod.expected_repo_cache_path(tmp_path / "cache", target)
    repo.mkdir(parents=True)
    row = mod.build_manifest_row(target, tmp_path / "cache")
    assert row["repo_cached"] is True
    assert row["source_exists"] is False
    assert row["obstruction"] == "OBSTRUCTED_MISSING_FILE"


def test_manifest_row_reports_none_when_source_exists(tmp_path):
    mod = load_module()
    target = mod.SorryTarget(
        repo="https://github.com/siddhartha-gadgil/MetaExamples",
        commit="edbb75e784db19846a1c19841e182b797afc18bb",
        file_path="MetaExamples/Fiddle.lean",
        line=79,
    )
    repo = mod.expected_repo_cache_path(tmp_path / "cache", target)
    source = repo / "MetaExamples/Fiddle.lean"
    source.parent.mkdir(parents=True)
    source.write_text("example : True := by trivial\n")
    row = mod.build_manifest_row(target, tmp_path / "cache")
    assert row["repo_cached"] is True
    assert row["source_exists"] is True
    assert row["obstruction"] == "NONE"


def test_native_sorrydb_json_to_manifest_dry_run_never_runs_command(tmp_path, monkeypatch):
    mod = load_module()

    record = {
        "repo": {
            "remote": "https://github.com/siddhartha-gadgil/MetaExamples",
            "commit": "edbb75e784db19846a1c19841e182b797afc18bb",
            "lean_version": "v4.22.0",
        },
        "location": {"path": "MetaExamples/Fiddle.lean", "start_line": 79},
        "debug_info": {"goal": "case zero ⊢ 0 + 2 ≤ 0 + 4"},
    }
    records = tmp_path / "sorrydb.json"
    records.write_text(json.dumps({"documentation": {}, "sorries": [record]}))

    def fail_run_command(*args, **kwargs):
        raise AssertionError("dry-run manifest must not run commands")

    monkeypatch.setattr(mod, "run_command", fail_run_command)

    monkeypatch.setenv("SORRYDB_V421_WORK_ROOT", str(tmp_path / "work"))
    monkeypatch.setenv("SORRYDB_V421_RECORDS_PATH", str(records))
    monkeypatch.setenv("SORRYDB_V421_MAX_RECORDS", "1")
    monkeypatch.setenv("SORRYDB_V421_FOCUS_REPOS", "MetaExamples")
    monkeypatch.setenv("SORRYDB_V421_MIN_FREE_GB", "0")
    monkeypatch.setenv("SORRYDB_V422_DRY_RUN_MANIFEST", "1")
    monkeypatch.setenv("SORRYDB_V422_REPO_CACHE_ROOT", str(tmp_path / "cache"))

    rc = mod.main()
    assert rc == 0

    manifests = list((tmp_path / "work").glob("artifacts/runs/*/*/replay_manifest.jsonl"))
    assert len(manifests) == 1
    rows = [json.loads(line) for line in manifests[0].read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["repo"] == "https://github.com/siddhartha-gadgil/MetaExamples"
    assert rows[0]["obstruction"] == mod.OBSTRUCTED_REPO_NOT_CACHED

    summaries = list((tmp_path / "work").glob("artifacts/runs/*/*/run_summary.json"))
    summary = json.loads(summaries[0].read_text())
    assert summary["verdict"] == mod.REPLAY_MANIFEST_WRITTEN
    assert summary["replay_manifest_rows"] == 1
    assert summary["dry_run_manifest_enabled"] is True
