"""Task 3 orchestration binds acquisition separately from the Task 2 producer."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import re
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
    assert api.PRODUCER_COMMIT == "d98f217d7e43cf74bfdb180dd953e98a29388f48"
    assert set(api.QUALIFICATION_WRAPPER_FILES) == {
        ".github/workflows/mathgraph-source-catalogue-v1.yml",
        "conformance/source_catalogue_v1/consumer.py",
        "conformance/source_catalogue_v1/run_isolated.py",
        "conformance/source_catalogue_v1/stdlib_conformance.py",
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
    (package / "README.md").write_text("dependency documentation\n")
    (package / "docs").mkdir()
    (package / "docs/README.md").symlink_to("../README.md")
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
        "build/lib/lean/Root.olean", "packages/dep/Dep.lean", "packages/dep/README.md",
        "packages/dep/docs/README.md",
    }
    link = next(entry for entry in inventory["files"] if entry["path"] == "packages/dep/docs/README.md")
    assert link == {"path": "packages/dep/docs/README.md", "sha256": hashlib.sha256(b"../README.md").hexdigest(),
                    "size_bytes": 12, "mode": "120000", "target": "../README.md"}
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


def test_selected_native_module_outputs_are_pruned_before_inventory(api, tmp_path):
    mathlib = tmp_path / "mathlib"
    build = mathlib / ".lake/build/lib/lean"
    selected = build / "Mathlib/Data/Nat/Basic"
    unrelated = build / "Mathlib/Data/Nat/Defs.olean"
    selected.parent.mkdir(parents=True)
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    expected = {
        "lib/lean/Mathlib/Data/Nat/Basic.olean",
        "lib/lean/Mathlib/Data/Nat/Basic.olean.private",
        "lib/lean/Mathlib/Data/Nat/Basic.olean.server",
        "lib/lean/Mathlib/Data/Nat/Basic.ir",
        "lib/lean/Mathlib/Data/Nat/Basic.ir.sig",
    }
    for relative in expected:
        path = mathlib / ".lake/build" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative.encode())
    unrelated.write_bytes(b"unrelated")
    policy = {"modules": [{"module": "Mathlib.Data.Nat.Basic"}]}
    assert set(api._prune_selected_outputs(mathlib, policy)) == expected
    assert unrelated.read_bytes() == b"unrelated"
    assert not any((mathlib / ".lake/build" / relative).exists() for relative in expected)


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


def test_generated_artifact_checksum_manifest_closes_exact_relative_inventory(api, tmp_path):
    output = tmp_path / "output"
    (output / "catalogue").mkdir(parents=True)
    (output / "evidence").mkdir()
    (output / "catalogue/manifest.json").write_bytes(b"manifest")
    (output / "trust-policy.json").write_bytes(b"policy")
    (output / "evidence/qualification-report.json").write_bytes(b"report")
    entries = api.write_artifact_checksum_manifest(output)
    assert [entry["path"] for entry in entries] == [
        "catalogue/manifest.json", "evidence/qualification-report.json", "trust-policy.json",
    ]
    lines = (output / "evidence/artifact-checksums.txt").read_text().splitlines()
    assert lines == [f'{entry["sha256"]}  {entry["path"]}' for entry in entries]
    assert all(not line.split("  ", 1)[1].startswith("/") for line in lines)


def test_generation_orchestrator_runtime_identity_is_explicit(api):
    identity = api.host_runtime_identity()
    assert identity["implementation"] == "cpython"
    assert identity["version"]
    assert identity["cache_tag"].startswith("cpython-")
    assert Path(identity["executable"]).is_absolute()
    assert re.fullmatch(r"[0-9a-f]{64}", identity["executable_sha256"])
    assert set(identity) == {
        "implementation", "version", "cache_tag", "executable", "executable_sha256",
        "runner_os", "runner_arch", "runner_image_os", "runner_image_version",
    }


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
    assert '--expected-wrapper-commit "$GITHUB_SHA"' in text
    assert "--network none" in text
    assert "python:3.11-slim@sha256:e529028263dbe6910a2d96f7d2b8f5266385e917fd45d286ef166977c094a51e" in text
    assert text.count("python-version: '3.11.17'") == 2
    assert "pip install" not in text
    assert "python -I -S -B conformance/source_catalogue_v1/stdlib_conformance.py" in text
    for line in text.splitlines():
        if line.lstrip().startswith("- uses:"):
            assert re.search(r"@[0-9a-f]{40}(?:\s|$)", line), line
    assert 'sha256sum conformance.json host-runtime.json replay.json isolation.json qualification-report.json size-report.json publication-checksums.txt' in text
    assert "sha256sum -c artifact-checksums.txt" in text
    assert "sha256sum -c evidence/artifact-checksums.txt" in text
    assert "find . -type f ! -path './evidence/artifact-checksums.txt'" in text
    assert "artifact-digest: ${{ steps.upload-independent.outputs.artifact-digest }}" in text
    assert "trust-policy-sha256: ${{ steps.pin-generated-output.outputs.trust-policy-sha256 }}" in text
    assert "artifact-checksums-sha256: ${{ steps.pin-generated-output.outputs.artifact-checksums-sha256 }}" in text
    assert "id: pin-generated-output" in text and '>> "$GITHUB_OUTPUT"' in text
    assert 'needs.generate-and-compare.outputs.trust-policy-sha256' in text
    assert 'needs.generate-and-compare.outputs.artifact-checksums-sha256' in text
    assert text.count('sha256sum "$generated/trust-policy.json"') == 1
    assert '--artifact-checksums-sha256 "$artifact_checksums_sha"' in text


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
