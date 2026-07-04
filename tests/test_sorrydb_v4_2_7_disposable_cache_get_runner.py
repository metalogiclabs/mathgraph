from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sorrydb/sorrydb_v4_2_7_disposable_cache_get_runner.sh"


def test_script_exists_and_is_executable():
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & 0o111


def test_script_uses_disposable_work_root():
    text = SCRIPT.read_text()
    assert "SORRYDB_V427_WORK_ROOT" in text
    assert "/tmp/mathgraph_sorrydb_v427_disposable" in text


def test_script_runs_v426_with_cache_get_explicitly_enabled():
    text = SCRIPT.read_text()
    assert 'SORRYDB_V426_ALLOW_CACHE_GET="1"' in text
    assert 'SORRYDB_V426_RUN_BASELINE_AFTER_CACHE="1"' in text


def test_script_pins_metaexamples_commit():
    text = SCRIPT.read_text()
    assert "edbb75e784db19846a1c19841e182b797afc18bb" in text
    assert "MetaExamples/Fiddle.lean" in text


def test_script_has_disk_guard_and_manifest_print():
    text = SCRIPT.read_text()
    assert "OBSTRUCTED_DISK_PRESSURE" in text
    assert "cache_get_manifest.json" in text
    assert "FINAL_VERDICT=" in text
