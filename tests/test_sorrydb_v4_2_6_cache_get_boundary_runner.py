import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_2_6_cache_get_boundary_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v426_cache_get", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cache_get_command_requires_explicit_permission():
    mod = load_module()
    assert not mod.command_is_safe(["lake", "exe", "cache", "get"], False)
    assert mod.command_is_safe(["lake", "exe", "cache", "get"], True)


def test_forbids_lake_update_even_when_cache_get_allowed():
    mod = load_module()
    assert not mod.command_is_safe(["lake", "update"], True)


def test_classify_cache_get():
    mod = load_module()
    assert mod.classify_cache_get(0, "", "", False) == mod.CACHE_GET_PASSED
    assert mod.classify_cache_get(1, "", "failed", False) == mod.CACHE_GET_FAILED
    assert mod.classify_cache_get(124, "", "", True) == mod.OBSTRUCTED_CACHE_GET_TIMEOUT


def test_classify_baseline_cache_boundary_and_success():
    mod = load_module()
    assert mod.classify_baseline(0, "", "", False) == mod.BASELINE_PASSED
    assert mod.classify_baseline(1, "unknown module prefix Mathlib", "", False) == mod.OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    assert mod.classify_baseline(1, "", "unknown identifier foo", False) == mod.OBSTRUCTED_BASELINE_COMPILE_FAILURE


def test_env_flag_accepts_one(monkeypatch):
    mod = load_module()
    monkeypatch.setenv("X_FLAG", "1")
    assert mod.env_flag("X_FLAG") is True
