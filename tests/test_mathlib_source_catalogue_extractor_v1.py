"""Real pinned Lean qualification. Missing Lean is a failure, never a skip."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/source_catalogue_v1/lean-project"


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
