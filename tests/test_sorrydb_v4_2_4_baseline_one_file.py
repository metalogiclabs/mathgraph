import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_2_4_baseline_one_file.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v424_baseline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_command_is_safe_for_lake_env_lean():
    mod = load_module()
    assert mod.command_is_safe(["lake", "env", "lean", "MetaExamples/Fiddle.lean"], False)


def test_command_rejects_lake_update_and_cache_get_by_default():
    mod = load_module()
    assert not mod.command_is_safe(["lake", "update"], False)
    assert not mod.command_is_safe(["lake", "exe", "cache", "get"], False)


def test_command_allows_cache_get_only_when_explicit():
    mod = load_module()
    assert mod.command_is_safe(["lake", "exe", "cache", "get"], True)


def test_classify_success_timeout_and_compile_failure():
    mod = load_module()
    assert mod.classify(0, "", "", False) == mod.BASELINE_PASSED
    assert mod.classify(124, "", "", True) == mod.OBSTRUCTED_BASELINE_TIMEOUT
    assert mod.classify(1, "", "unknown identifier foo", False) == mod.OBSTRUCTED_BASELINE_COMPILE_FAILURE


def test_classify_cache_or_build_boundary():
    mod = load_module()
    assert mod.classify(1, "", "missing manifest", False) == mod.OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    assert mod.classify(1, "", "toolchain not installed", False) == mod.OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
