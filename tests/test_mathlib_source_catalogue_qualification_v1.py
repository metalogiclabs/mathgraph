"""Task 3 orchestration binds acquisition separately from the Task 2 producer."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def api():
    path = ROOT / "scripts/qualify_mathlib_source_catalogue_v1.py"
    spec = importlib.util.spec_from_file_location("qualify_mathlib_source_catalogue_v1", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_qualification_orchestrator_exists():
    assert (ROOT / "scripts/qualify_mathlib_source_catalogue_v1.py").is_file()


def test_approved_producer_commit_and_wrapper_identity_are_separate(api):
    assert api.PRODUCER_COMMIT == "b321166e085fca3393d5e244ae89ab852f869c33"
    assert set(api.QUALIFICATION_WRAPPER_FILES) == {
        ".github/workflows/mathgraph-source-catalogue-v1.yml",
        "conformance/source_catalogue_v1/consumer.py",
        "conformance/source_catalogue_v1/run_isolated.py",
        "conformance/source_catalogue_v1/test_consumer.py",
        "scripts/qualify_mathlib_source_catalogue_v1.py",
        "tests/test_mathlib_source_catalogue_qualification_v1.py",
    }
    assert "scripts/qualify_mathlib_source_catalogue_v1.py" not in api.PRODUCER_FILES


def test_runtime_profile_uses_child_manifest_not_parent_index_as_run_reference(api):
    assert api.BASE_IMAGE.endswith("@sha256:17923645546d74acef88727bce62c23bbaed953fc7097c41a8b777bba3ca98de")
    assert api.BASE_PARENT_INDEX == "sha256:8ea58fbc817960cd62d512044956ff00cb94865e549eeec32c12139413262004"
    assert api.BASE_IMAGE_CONFIG == "sha256:12d2284be437af82eaf8ebf5d1965223b8f259d82c1a523fff8e46de50ed5b54"


def test_qualification_runtime_profile_matches_exact_approved_producer(api):
    publisher = api.load_producer_module(ROOT)
    assert api.BASE_IMAGE == publisher.BASE_IMAGE
    assert api.BASE_IMAGE_CONFIG == publisher.BASE_IMAGE_CONFIG
    assert len(api.BASE_IMAGE_CONFIG.removeprefix("sha256:")) == 64


def test_parent_index_requires_exact_linux_amd64_child(api):
    good = {"manifests": [{"digest": api.BASE_IMAGE.rsplit("@", 1)[1],
                            "platform": {"os": "linux", "architecture": "amd64"}}]}
    api.verify_parent_index(json.dumps(good).encode())
    for changed in [
        {"manifests": []},
        {"manifests": [{"digest": api.BASE_IMAGE.rsplit("@", 1)[1],
                          "platform": {"os": "linux", "architecture": "arm64"}}]},
        {"manifests": [{"digest": "sha256:" + "0" * 64,
                          "platform": {"os": "linux", "architecture": "amd64"}}]},
    ]:
        with pytest.raises(ValueError):
            api.verify_parent_index(json.dumps(changed).encode())
    with pytest.raises(ValueError):
        api.verify_parent_index(
            b'{"manifests":[],"manifests":[{"digest":"sha256:'
            + api.BASE_IMAGE.rsplit("@sha256:", 1)[1].encode()
            + b'","platform":{"architecture":"amd64","os":"linux"}}]}'
        )


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def test_dependency_inventory_is_complete_canonical_and_package_pinned(api, tmp_path):
    mathlib = tmp_path / "mathlib"
    package = mathlib / ".lake/packages/dep"
    package.mkdir(parents=True)
    (mathlib / ".lake/build/lib/lean").mkdir(parents=True)
    (mathlib / ".lake/build/lib/lean/Root.olean").write_bytes(b"root-cache")
    (package / "Dep.lean").write_text("def dep : Nat := 1\n")
    git(package, "init", "-q")
    git(package, "add", ".")
    git(package, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "dep")
    git(package, "remote", "add", "origin", "https://example.invalid/dep")
    commit, tree = git(package, "rev-parse", "HEAD"), git(package, "rev-parse", "HEAD^{tree}")
    (mathlib / "lake-manifest.json").write_text(json.dumps({"packages": [
        {"name": "dep", "url": "https://example.invalid/dep", "rev": commit},
    ]}))
    publisher = api.load_producer_module(ROOT)
    policy = {"source": {"commit": "a" * 40, "tree": "b" * 40}}
    inventory, raw = api.build_dependency_inventory(mathlib, policy, publisher)
    assert raw == publisher.contract.canonical_bytes(inventory)
    assert inventory["packages"][0]["commit"] == commit
    assert inventory["packages"][0]["tree"] == tree
    assert {entry["path"] for entry in inventory["files"]} == {
        "build/lib/lean/Root.olean", "packages/dep/Dep.lean",
    }
    publisher.verify_dependency_inventory(mathlib / ".lake", inventory, hashlib.sha256(raw).hexdigest())


def test_existing_or_symlink_acquisition_root_is_rejected(api, tmp_path):
    available = tmp_path / "new"
    api.require_new_work_root(available)
    available.mkdir()
    (available / "state").write_text("not fresh")
    with pytest.raises(ValueError): api.require_new_work_root(available)
    link = tmp_path / "link"
    link.symlink_to(available, target_is_directory=True)
    with pytest.raises(ValueError): api.require_new_work_root(link)


def test_trust_policy_pins_publication_source_producer_and_wrapper(api, tmp_path):
    fixture = ROOT / "conformance/source_catalogue_v1/fixtures"
    root = tmp_path / "catalogue"
    (root / "shards").mkdir(parents=True)
    manifest = json.loads((fixture / "manifest.json").read_bytes())
    for source, target in [(fixture / "manifest.json", root / "manifest.json"),
                           (fixture / "search.json", root / "search.json"),
                           (fixture / "shard.json", root / manifest["shards"][0]["path"])]:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    source_policy = {"catalogue_id": manifest["catalogue_id"], "source": {
        key: manifest["source"][key] for key in ["repository", "commit", "tree", "lean_toolchain"]},
        "modules": [{key: module[key] for key in ["module", "path", "sha256", "size_bytes"]}
                    for module in manifest["modules"]]}
    producer = manifest["extractor"]
    wrapper = {"source_commit": "9" * 40, "sources": [
        {"path": "scripts/qualify_mathlib_source_catalogue_v1.py", "sha256": "8" * 64},
    ]}
    policy = api.build_trust_policy(root, source_policy, b"source-policy", producer, wrapper)
    assert policy["manifest"]["sha256"] == hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    assert policy["source"]["commit"] == "a" * 40
    assert policy["producer"] == producer
    assert policy["qualification_wrapper"] == wrapper
    assert policy["result"]["authority"] == "NONE"


def test_dedicated_workflow_has_heavy_generation_and_independent_isolation_contract():
    workflow = ROOT / ".github/workflows/mathgraph-source-catalogue-v1.yml"
    assert workflow.is_file()
    text = workflow.read_text()
    assert "runs-on: ubuntu-24.04" in text
    assert "timeout-minutes: 60" in text
    assert "scripts/qualify_mathlib_source_catalogue_v1.py" in text
    assert "--minimum-free-gib 12" in text
    assert "mathgraph-source-catalogue-v1-generated" in text
    assert "mathgraph-source-catalogue-v1-independent" in text
    assert "needs: generate-and-compare" in text
    assert "conformance/source_catalogue_v1/run_isolated.py" in text
    assert "--backend docker" in text
    assert "--network none" in text
    assert "python:3.11-slim@sha256:e529028263dbe6910a2d96f7d2b8f5266385e917fd45d286ef166977c094a51e" in text


@pytest.mark.parametrize("workflow_name", [
    "mathgraph-org-v1.yml", "mathgraph-protocol-conformance-v1.yml",
])
def test_light_workflows_watch_committed_catalogue_contracts(workflow_name):
    text = (ROOT / ".github/workflows" / workflow_name).read_text()
    for watched in [
        "conformance/source_catalogue_v1/**",
        "website/public/catalogues/mathlib/v4.34.1/**",
        "scripts/qualify_mathlib_source_catalogue_v1.py",
    ]:
        assert watched in text
