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


def test_patch_certificate_builder_for_accepted_summary(monkeypatch, tmp_path):
    mod = load_module()
    monkeypatch.setenv("SORRYDB_V430_PROJECT", "siddhartha-gadgil/MetaExamples")
    monkeypatch.setenv("SORRYDB_V430_PROJECT_COMMIT", "edbb75e784db19846a1c19841e182b797afc18bb")
    monkeypatch.setenv("SORRYDB_V430_CERTIFICATE_ID", "test-cert")
    summary = {
        "verdict": mod.PATCH_ACCEPTED,
        "file_path": "MetaExamples/Fiddle.lean",
        "source_snippet": "  · extract_goal using eg₁\n    sorry",
        "patch_snippet": "  · extract_goal using eg₁\n    exact Nat.le_add_right n 1",
        "baseline_command": ["lake", "env", "lean", "MetaExamples/Fiddle.lean"],
        "patch_command": ["lake", "env", "lean", "MetaExamples/Fiddle.lean"],
        "baseline_verdict": mod.BASELINE_PASSED,
        "patch_apply_verdict": mod.PATCH_APPLIED,
        "patch_verdict": mod.PATCH_ACCEPTED,
        "patch_result": {"returncode": 0},
    }
    cert = mod.build_patch_certificate(summary)
    assert cert["certificate_id"] == "test-cert"
    assert cert["project"] == "siddhartha-gadgil/MetaExamples"
    assert cert["status"] == mod.PATCH_ACCEPTED
    assert cert["final_verdict"] == mod.PATCH_ACCEPTED
    assert cert["lean_returncode"] == 0
    assert "general proof repair" in "\n".join(cert["does_not_claim"])


def test_maybe_write_patch_certificate_only_for_patch_accepted(monkeypatch, tmp_path):
    mod = load_module()
    monkeypatch.setenv("SORRYDB_V430_CERTIFICATE_ID", "accepted-cert")
    summary = {
        "verdict": mod.PATCH_ACCEPTED,
        "file_path": "MetaExamples/Fiddle.lean",
        "source_snippet": "old",
        "patch_snippet": "new",
        "baseline_command": ["lake", "env", "lean", "MetaExamples/Fiddle.lean"],
        "patch_command": ["lake", "env", "lean", "MetaExamples/Fiddle.lean"],
        "baseline_verdict": mod.BASELINE_PASSED,
        "patch_apply_verdict": mod.PATCH_APPLIED,
        "patch_verdict": mod.PATCH_ACCEPTED,
        "patch_result": {"returncode": 0},
    }
    mod.maybe_write_patch_certificate(summary, tmp_path)
    cert_path = tmp_path / "patch_certificates" / "accepted-cert.json"
    assert cert_path.exists()
    assert summary["patch_certificate_id"] == "accepted-cert"

    rejected = {"verdict": mod.PATCH_REJECTED}
    mod.maybe_write_patch_certificate(rejected, tmp_path)
    assert "patch_certificate_id" not in rejected
