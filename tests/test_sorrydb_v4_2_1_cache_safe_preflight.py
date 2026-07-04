import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_2_declaration_retrieval_patcher.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v421", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_load_records_accepts_native_sorrydb_json(tmp_path):
    mod = load_module()
    record = {
        "repo": {
            "remote": "https://github.com/siddhartha-gadgil/MetaExamples",
            "commit": "abc123",
            "lean_version": "v4.22.0",
        },
        "location": {"path": "MetaExamples/Fiddle.lean", "start_line": 79},
        "debug_info": {"goal": "case zero ⊢ 0 + 2 ≤ 0 + 4"},
    }
    path = tmp_path / "sorrydb.json"
    path.write_text(json.dumps({"documentation": {}, "sorries": [record]}))

    rows = mod.load_records(path)
    assert len(rows) == 1

    target = mod.defensive_target(rows[0])
    assert target.repo == "https://github.com/siddhartha-gadgil/MetaExamples"
    assert target.commit == "abc123"
    assert target.lean_version == "v4.22.0"
    assert target.file_path == "MetaExamples/Fiddle.lean"
    assert target.line == 79
    assert "0 + 2" in target.statement


def test_focus_matching_accepts_short_name_full_url_and_git_suffix():
    mod = load_module()
    target = mod.SorryTarget(
        repo="https://github.com/siddhartha-gadgil/LeanLangur",
        file_path="LeanLangur/QuickSort.lean",
        line=90,
    )

    assert mod.target_matches_focus(target, ["LeanLangur"])
    assert mod.target_matches_focus(target, ["https://github.com/siddhartha-gadgil/LeanLangur"])
    assert mod.target_matches_focus(target, ["https://github.com/siddhartha-gadgil/LeanLangur.git"])
    assert not mod.target_matches_focus(target, ["MetaExamples"])


def test_disk_preflight_obstructs_when_free_space_below_threshold(monkeypatch, tmp_path):
    mod = load_module()

    class Usage:
        free = 2 * mod.GIB

    monkeypatch.setattr(mod.shutil, "disk_usage", lambda path: Usage())

    safe, free_gb, checked = mod.disk_preflight([tmp_path], required_gb=15)
    assert safe is False
    assert checked == [str(tmp_path)]
    assert free_gb[str(tmp_path)] == 2.0


def test_command_safety_rejects_lake_update_and_cache_get_by_default():
    mod = load_module()
    assert mod.command_safety_obstruction(["lake", "update"], False) == mod.OBSTRUCTED_UNSAFE_REPLAY_COMMAND
    assert mod.command_safety_obstruction(["lake", "exe", "cache", "get"], False) == mod.OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    assert mod.command_safety_obstruction(["lake", "exe", "cache", "get"], True) is None


def test_baseline_classifies_nonzero_without_cache_get_as_cache_boundary(monkeypatch, tmp_path):
    mod = load_module()

    target = mod.SorryTarget(
        repo="https://github.com/example/repo",
        file_path="A.lean",
        line=1,
    )
    source = tmp_path / "A.lean"
    source.write_text("example : True := by trivial\n")
    (tmp_path / "lakefile.toml").write_text("name = \"dummy\"\n")

    monkeypatch.setattr(
        mod,
        "run_command",
        lambda command, cwd, timeout: mod.ProcessResult(1, "", "build failed", 0.01),
    )

    baseline = mod.check_baseline(target, source, tmp_path, timeout=1, allow_cache_get=False)
    assert baseline.classification == mod.OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    assert baseline.command == ["lake", "env", "lean", "A.lean"]
