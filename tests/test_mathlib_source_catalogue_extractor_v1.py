"""Real pinned Lean qualification. Missing Lean is a failure, never a skip."""
import json
import os
from pathlib import Path
import shutil
import subprocess

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
