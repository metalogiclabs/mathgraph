import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_2_5_cache_build_boundary_inspector.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v425_inspector", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_package_status_missing_package(tmp_path):
    mod = load_module()
    status = mod.package_status(tmp_path, "mathlib")
    assert status["package"] == "mathlib"
    assert status["root_exists"] is False
    assert status["build_lib_exists"] is False
    assert status["olean_count"] == 0


def test_classify_dependencies_cloned_without_mathlib_olean():
    mod = load_module()
    summary = {
        "repo_exists": True,
        "source_exists": True,
        "lake_manifest_exists": True,
        "lean_toolchain": "leanprover/lean4:v4.22.0",
        "mathlib_package_exists": True,
        "mathlib_olean_exists": False,
        "lake_packages_count": 9,
    }
    findings = mod.classify(summary)
    assert "dependencies_cloned_but_mathlib_not_built_or_cached" in findings
    assert "lake_env_materialized_packages_without_olean_cache" in findings


def test_recommended_next_for_missing_mathlib_olean():
    mod = load_module()
    summary = {
        "repo_exists": True,
        "source_exists": True,
        "mathlib_package_exists": True,
        "mathlib_olean_exists": False,
    }
    assert mod.recommended_next(summary) == "next_safe_portal_is_cache_get_or_build_in_disposable_environment_not_local_proof_repair"


def test_recommended_next_when_olean_exists():
    mod = load_module()
    summary = {
        "repo_exists": True,
        "source_exists": True,
        "mathlib_package_exists": True,
        "mathlib_olean_exists": True,
    }
    assert mod.recommended_next(summary) == "baseline_replay_can_be_retried_without_dependency_materialization"
