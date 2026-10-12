"""Real pinned Lean qualification. Missing Lean is a failure, never a skip."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/source_catalogue_v1/lean-project"
ORIGIN_COLLISION_FIXTURE = ROOT / "tests/fixtures/source_catalogue_v1/lean-origin-collision"


def test_real_lean_environment_extractor(tmp_path):
    extractor = ROOT / "tools/mathlib_catalogue/Extract.lean"
    assert extractor.is_file(), "Lean extractor missing"
    lean = os.environ.get("MATHGRAPH_CATALOGUE_LEAN", shutil.which("lean") or "")
    assert lean, "pinned Lean qualification requires MATHGRAPH_CATALOGUE_LEAN"
    version = subprocess.check_output([lean, "--version"], text=True)
    assert "version 4.34.1," in version, "qualification requires exact Lean v4.34.1"
    project = tmp_path / "project"
    shutil.copytree(FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    subprocess.run([lean, "-o", "CatalogueFixture.olean", "CatalogueFixture.lean"], cwd=project, env=env, check=True)
    out = tmp_path / "extracted.json"
    subprocess.run([lean, "--run", str(extractor), str(project), str(out), "CatalogueFixture"], cwd=project, env=env, check=True)
    first = out.read_bytes()
    subprocess.run([lean, "--run", str(extractor), str(project), str(out), "CatalogueFixture"], cwd=project, env=env, check=True)
    assert out.read_bytes() == first
    doc = json.loads(first)
    module, = doc["modules"]
    assert module["module"] == "CatalogueFixture"
    assert module["imports"] == ["Init", "Lean"]
    ds = {d["qualified_name"]: d for d in module["declarations"]}
    assert {"CatalogueFixture.Token", "CatalogueFixture.Token.mk", "CatalogueFixture.typeOnly", "CatalogueFixture.proofOnly",
            "CatalogueFixture.usesProof", "CatalogueFixture.text", "CatalogueFixture.α", "CatalogueFixture.«name.with.dot»", "CatalogueFixture.hidden", "CatalogueFixture.recur",
            "CatalogueFixture._user", "_private.CatalogueFixture.0.CatalogueFixture.secret"} == set(ds)
    assert ds["CatalogueFixture.α"]["type_references"] == ["CatalogueFixture.Token"]
    assert ds["CatalogueFixture.usesProof"]["type_references"] == ["True"]
    assert ds["CatalogueFixture.text"]["type_references"] == ["String"]
    assert ds["CatalogueFixture.Token.mk"]["kind"] == "constructor"
    assert ds["CatalogueFixture.Token"]["kind"] == "inductive"
    assert ds["CatalogueFixture.hidden"]["kind"] == "opaque"
    raw = (project / "CatalogueFixture.lean").read_bytes()
    for decl in ds.values():
        for p in decl["range"].values():
            assert p["line"] == raw[:p["byte"]].count(b"\n") + 1
            assert p["column"] == len(raw[:p["byte"]].rsplit(b"\n", 1)[-1])
    alpha = ds["CatalogueFixture.α"]["range"]
    assert raw[alpha["start"]["byte"]:alpha["end"]["byte"]].decode() == "noncomputable def α : Token := typeOnly"
    omissions = {d["qualified_name"]: d for d in module["omissions"]}
    assert omissions["CatalogueFixture.Token.rec"]["reason"] == "GENERATED"
    assert omissions["CatalogueFixture.noRange"]["reason"] == "MISSING_RANGE"
    assert "proofOnly" not in ds["CatalogueFixture.usesProof"]["statement"]


def test_generated_equation_origin_collision_is_named_omission(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["OriginDefs", "OriginBasic", "OriginLeft"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "origin-collision.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "OriginBasic", "OriginLeft",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    document = json.loads(output.read_bytes())
    assert [module["module"] for module in document["modules"]] == [
        "OriginBasic", "OriginLeft",
    ]
    for module, direct in zip(document["modules"], ["Origin.forceInBasic", "Origin.forceInLeft"]):
        omissions = {entry["qualified_name"]: entry for entry in module["omissions"]}
        assert omissions["Origin.duplicatedEquation.eq_1"] == {
            "qualified_name": "Origin.duplicatedEquation.eq_1",
            "kind": "theorem",
            "reason": "GENERATED",
        }
        assert {entry["qualified_name"] for entry in module["declarations"]} == {direct}


def test_direct_source_origin_collision_remains_fail_closed(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "direct-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["DirectLeft", "DirectRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "DirectLeft", "DirectRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Origin.directDuplicate" in result.stderr
    assert "selected=DirectRight" in result.stderr
    assert "canonical=DirectLeft" in result.stderr
    assert not output.exists()


def test_generated_hcongr_origin_collision_is_named_omission(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "hcongr-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["HCongrDefs", "HCongrLeft", "HCongrRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "hcongr-origin-collision.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "HCongrLeft", "HCongrRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    document = json.loads(output.read_bytes())
    assert [module["module"] for module in document["modules"]] == [
        "HCongrLeft", "HCongrRight",
    ]
    for module, direct in zip(document["modules"], ["Origin.forceHCongrLeft", "Origin.forceHCongrRight"]):
        omissions = {entry["qualified_name"]: entry for entry in module["omissions"]}
        assert omissions["Origin.congrTarget.hcongr_3"] == {
            "qualified_name": "Origin.congrTarget.hcongr_3",
            "kind": "theorem",
            "reason": "GENERATED",
        }
        assert {entry["qualified_name"] for entry in module["declarations"]} == {direct}


def test_direct_hcongr_suffix_origin_collision_remains_fail_closed(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "direct-hcongr-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["DirectHCongrLeft", "DirectHCongrRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "DirectHCongrLeft", "DirectHCongrRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "DirectHCongr.hcongr_3" in result.stderr
    assert "selected=DirectHCongrRight" in result.stderr
    assert "canonical=DirectHCongrLeft" in result.stderr
    assert not output.exists()


def test_hcongr_collision_without_selected_module_metadata_remains_fail_closed(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "forged-hcongr-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["HCongrDefs", "HCongrLeft", "HCongrSpoofRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "HCongrLeft", "HCongrSpoofRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Origin.congrTarget.hcongr_3" in result.stderr
    assert "selected=HCongrSpoofRight" in result.stderr
    assert "canonical=HCongrLeft" in result.stderr
    assert not output.exists()


def test_hcongr_collision_with_selected_module_source_range_remains_fail_closed(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "range-spoof-hcongr-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["HCongrDefs", "HCongrLeft", "HCongrRangeSpoofRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "HCongrLeft", "HCongrRangeSpoofRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Origin.congrTarget.hcongr_3" in result.stderr
    assert "selected=HCongrRangeSpoofRight" in result.stderr
    assert "canonical=HCongrLeft" in result.stderr
    assert not output.exists()


def test_generated_congr_simp_origin_collision_is_named_omission(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "congr-simp-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["HCongrDefs", "CongrSimpLeft", "CongrSimpRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "congr-simp-origin-collision.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "CongrSimpLeft", "CongrSimpRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    document = json.loads(output.read_bytes())
    assert [module["module"] for module in document["modules"]] == [
        "CongrSimpLeft", "CongrSimpRight",
    ]
    for module, direct in zip(document["modules"], ["Origin.forceCongrSimpLeft", "Origin.forceCongrSimpRight"]):
        omissions = {entry["qualified_name"]: entry for entry in module["omissions"]}
        assert omissions["Origin.congrTarget.congr_simp"] == {
            "qualified_name": "Origin.congrTarget.congr_simp",
            "kind": "theorem",
            "reason": "GENERATED",
        }
        assert {entry["qualified_name"] for entry in module["declarations"]} == {direct}


@pytest.mark.parametrize("left,right,qualified", [
    ("DirectCongrSimpLeft", "DirectCongrSimpRight", "DirectCongrSimp.congr_simp"),
    ("NearCongrSimpLeft", "NearCongrSimpRight", "NearCongrSimp.congr_simp_extra"),
])
def test_direct_congr_simp_names_remain_fail_closed(tmp_path, left, right, qualified):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / (left + "-origin-collision")
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in [left, right]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), left, right,
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert qualified in result.stderr
    assert f"selected={right}" in result.stderr
    assert f"canonical={left}" in result.stderr
    assert not output.exists()


def test_congr_simp_collision_without_selected_module_metadata_remains_fail_closed(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "spoof-congr-simp-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["HCongrDefs", "CongrSimpLeft", "CongrSimpSpoofRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "CongrSimpLeft", "CongrSimpSpoofRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Origin.congrTarget.congr_simp" in result.stderr
    assert "selected=CongrSimpSpoofRight" in result.stderr
    assert "canonical=CongrSimpLeft" in result.stderr
    assert not output.exists()


def test_congr_simp_collision_with_selected_module_source_range_remains_fail_closed(tmp_path):
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    project = tmp_path / "range-spoof-congr-simp-origin-collision"
    shutil.copytree(ORIGIN_COLLISION_FIXTURE, project)
    env = {**os.environ, "LEAN_PATH": str(project)}
    for module in ["HCongrDefs", "CongrSimpLeft", "CongrSimpRangeSpoofRight"]:
        subprocess.run([
            lean, "-o", str(project / (module + ".olean")),
            str(project / (module + ".lean")),
        ], cwd=project, env=env, check=True)
    output = tmp_path / "must-not-exist.json"
    result = subprocess.run([
        lean, "--run", str(ROOT / "tools/mathlib_catalogue/Extract.lean"),
        str(project), str(output), "CongrSimpLeft", "CongrSimpRangeSpoofRight",
    ], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Origin.congrTarget.congr_simp" in result.stderr
    assert "selected=CongrSimpRangeSpoofRight" in result.stderr
    assert "canonical=CongrSimpLeft" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("cache_mode", ["stale", "absent"])
def test_source_compile_order_includes_transitive_selected_dependencies(tmp_path, cache_mode):
    helper = ROOT / "tools/mathlib_catalogue/CompileOrder.lean"
    assert helper.is_file(), "environment compile-order helper missing"
    lean = os.environ["MATHGRAPH_CATALOGUE_LEAN"]
    source, cache = tmp_path / "source", tmp_path / "cache"
    source.mkdir()
    cache.mkdir()
    env = {**os.environ, "LEAN_PATH": str(cache), "LEAN_SRC_PATH": str(source)}
    for name, text in [("Z", "def z : Nat := 1\n"), ("Middle", "def middle : Nat := 0\n"), ("A", "def a : Nat := 0\n")]:
        (source / (name + ".lean")).write_text(text)
        if cache_mode == "stale": subprocess.run([lean, "-o", str(cache / (name + ".olean")), str(source / (name + ".lean"))], cwd=source, env=env, check=True)
    (source / "Middle.lean").write_text("import Z\ndef middle : Nat := z\n")
    (source / "A.lean").write_text("/- import Missing.Comment -/\nimport Middle\ndef text := \"import Missing.String\"\n")
    out = tmp_path / "order.json"
    subprocess.run([lean, "--run", str(helper), str(out), "A", "Z"], env=env, check=True)
    assert json.loads(out.read_bytes()) == {"modules": ["Z", "A"]}


@pytest.mark.parametrize("failure", ["cycle", "missing_source", "malformed_header"])
def test_source_compile_order_declines_invalid_import_closure(tmp_path, failure):
    source = tmp_path / "source"
    source.mkdir()
    (source / "A.lean").write_text("import B\n" if failure != "malformed_header" else "import\n")
    if failure == "cycle": (source / "B.lean").write_text("import A\n")
    output = tmp_path / "order.json"
    result = subprocess.run([os.environ["MATHGRAPH_CATALOGUE_LEAN"], "--run", str(ROOT / "tools/mathlib_catalogue/CompileOrder.lean"), str(output), "A"],
                            env={**os.environ, "LEAN_SRC_PATH": str(source)}, capture_output=True, text=True)
    assert result.returncode != 0
    assert {"cycle": "cyclic source imports", "missing_source": "missing verified import source", "malformed_header": "invalid source import header"}[failure] in result.stderr
    assert not output.exists()
