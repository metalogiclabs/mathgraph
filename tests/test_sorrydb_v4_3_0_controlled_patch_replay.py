import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_3_0_controlled_patch_replay.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v430_patch", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_safe_command_allows_lean_baseline_only():
    mod = load_module()
    assert mod.command_is_safe(["lake", "env", "lean", "MetaExamples/Fiddle.lean"])


def test_safe_command_forbids_cache_get_and_update():
    mod = load_module()
    assert not mod.command_is_safe(["lake", "exe", "cache", "get"])
    assert not mod.command_is_safe(["lake", "update"])


def test_single_replacement_success():
    mod = load_module()
    patched, verdict = mod.apply_single_replacement("a sorry b", "sorry", "by exact h")
    assert verdict == mod.PATCH_APPLIED
    assert patched == "a by exact h b"


def test_single_replacement_missing_and_ambiguous():
    mod = load_module()
    assert mod.apply_single_replacement("abc", "sorry", "x")[1] == mod.OBSTRUCTED_PATCH_TARGET_MISSING
    assert mod.apply_single_replacement("sorry sorry", "sorry", "x")[1] == mod.OBSTRUCTED_PATCH_AMBIGUOUS


def test_classify_lean_success_and_boundaries():
    mod = load_module()
    assert mod.classify_lean(0, "", "", False, mod.OBSTRUCTED_BASELINE_TIMEOUT) == mod.BASELINE_PASSED
    assert mod.classify_lean(1, "unknown module prefix Mathlib", "", False, mod.OBSTRUCTED_BASELINE_TIMEOUT) == mod.OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    assert mod.classify_lean(1, "unknown identifier nope", "", False, mod.OBSTRUCTED_BASELINE_TIMEOUT) == mod.OBSTRUCTED_BASELINE_COMPILE_FAILURE
    assert mod.classify_lean(124, "", "", True, mod.OBSTRUCTED_PATCH_TIMEOUT) == mod.OBSTRUCTED_PATCH_TIMEOUT


def test_default_patch_targets_eg1():
    mod = load_module()
    assert "eg₁" in mod.DEFAULT_SOURCE_SNIPPET
    assert "Nat.le_succ" in mod.DEFAULT_PATCH_SNIPPET
