from pathlib import Path
import importlib.util
import subprocess

MODULE_PATH = Path("experiments/sorrydb/sorrydb_v4_4_9_cache_dependency_hydration_planner.py")
spec = importlib.util.spec_from_file_location("planner", MODULE_PATH)
planner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(planner)


def make_repo(tmp_path, *, toolchain=True, lakefile=True, lakefile_toml=False, manifest=True, mathlib=True, olean=False):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    if toolchain:
        (repo / "lean-toolchain").write_text("leanprover/lean4:v4.22.0\n", encoding="utf-8")
    if lakefile:
        if lakefile_toml:
            (repo / "lakefile.toml").write_text('name = "fixture"\n', encoding="utf-8")
        else:
            (repo / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
    if manifest:
        (repo / "lake-manifest.json").write_text("{}\n", encoding="utf-8")
    if mathlib:
        mathlib_dir = repo / ".lake/packages/mathlib"
        mathlib_dir.mkdir(parents=True)
        if olean:
            olean_path = mathlib_dir / ".lake/build/lib/lean/Mathlib.olean"
            olean_path.parent.mkdir(parents=True)
            olean_path.write_text("fake\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    return repo, commit


def test_ready_when_mathlib_source_exists_but_olean_missing(tmp_path):
    repo, commit = make_repo(tmp_path)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_READY


def test_missing_repo_root(tmp_path):
    result = planner.classify_cache_hydration(tmp_path / "missing", None, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_REPO_ROOT_MISSING


def test_missing_toolchain(tmp_path):
    repo, commit = make_repo(tmp_path, toolchain=False)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_TOOLCHAIN_MISSING




def test_ready_with_lakefile_toml(tmp_path):
    repo, commit = make_repo(tmp_path, lakefile=True, lakefile_toml=True)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_READY
    assert result["lakefile_toml_exists"] is True


def test_missing_lakefile(tmp_path):
    repo, commit = make_repo(tmp_path, lakefile=False)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_LAKEFILE_MISSING


def test_missing_manifest(tmp_path):
    repo, commit = make_repo(tmp_path, manifest=False)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_MANIFEST_MISSING


def test_missing_mathlib_package(tmp_path):
    repo, commit = make_repo(tmp_path, mathlib=False)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_MATHLIB_SOURCE_MISSING


def test_existing_mathlib_olean_already_satisfied(tmp_path):
    repo, commit = make_repo(tmp_path, olean=True)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=20.0)
    assert result["status"] == planner.STATUS_ALREADY


def test_low_disk_blocks_ready(tmp_path):
    repo, commit = make_repo(tmp_path)
    result = planner.classify_cache_hydration(repo, commit, free_gb_override=1.0)
    assert result["status"] == planner.STATUS_DISK_LOW


def test_summary_records_bounded_claim_and_nonclaims(tmp_path, monkeypatch):
    repo, commit = make_repo(tmp_path)
    monkeypatch.setattr(planner, "V448_SUMMARY", tmp_path / "v448.json")
    monkeypatch.setattr(planner, "V447_QUEUE", tmp_path / "queue.json")
    monkeypatch.setattr(planner, "V446_SUMMARY", tmp_path / "v446.json")
    planner.V448_SUMMARY.write_text('{"queue_verdict":"QUEUE_RUN_COMPLETED_WITH_FAILURES","primary_obstruction":"OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"}', encoding="utf-8")
    planner.V447_QUEUE.write_text('{"candidates":[{"repo_root":"' + str(repo) + '"}]}', encoding="utf-8")
    planner.V446_SUMMARY.write_text('{"commit":"' + commit + '"}', encoding="utf-8")
    summary, plan, env = planner.build_plan()
    assert summary["cache_hydration_status"] == planner.STATUS_READY
    assert "lake exe cache get" in summary["recommended_command"]
    assert "cache hydration performed" in summary["does_not_claim"]
    assert "upstream submission" in summary["does_not_claim"]
