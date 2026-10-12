"""Independent, standard-library-only replay of authority-free source catalogues."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
EXPECTED = {
    "source_status": "SOURCE_INDEXED",
    "independent_verification": "NOT_CHECKED",
    "current_applicability": "NOT_CHECKED",
    "freshness": "PINNED_HISTORICAL_SOURCE",
    "authorization": "NONE",
    "authority": "NONE",
}


def test_independent_consumer_exists():
    assert importlib.util.find_spec("conformance.source_catalogue_v1.consumer"), "independent consumer is absent"


@pytest.fixture
def api():
    return importlib.import_module("conformance.source_catalogue_v1.consumer")


@pytest.fixture
def publication(tmp_path):
    root = tmp_path / "catalogue"
    (root / "shards").mkdir(parents=True)
    manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
    shutil.copyfile(FIXTURES / "manifest.json", root / "manifest.json")
    shutil.copyfile(FIXTURES / "search.json", root / "search.json")
    shutil.copyfile(FIXTURES / "shard.json", root / manifest["shards"][0]["path"])
    policy = tmp_path / "trust-policy.json"
    shutil.copyfile(FIXTURES / "trust-policy.json", policy)
    return root, policy


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_canonical(api, path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(api.canonical_bytes(value))


def repin_shard(api, root: Path, manifest: dict, shard: dict) -> None:
    previous = root / manifest["shards"][0]["path"]
    raw = api.canonical_bytes(shard)
    sha = hashlib.sha256(raw).hexdigest()
    metadata = manifest["shards"][0]
    metadata.update(path=f"shards/{sha}.json", sha256=sha, size_bytes=len(raw),
                    object_count=len(shard["objects"]), relation_count=len(shard["relations"]),
                    omitted_type_references=len(shard["omissions"]["type_references"]),
                    omitted_imports=len(shard["omissions"]["imports"]),
                    omitted_declarations=len(shard["omissions"]["declarations"]))
    if previous.exists():
        previous.unlink()
    write_canonical(api, root / metadata["path"], shard)


def repin_manifest(api, root: Path, policy_path: Path, manifest: dict, policy: dict) -> str:
    write_canonical(api, root / "manifest.json", manifest)
    raw = (root / "manifest.json").read_bytes()
    policy["manifest"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    write_canonical(api, policy_path, policy)
    return digest(policy_path)


def test_replays_tiny_fixture_and_derives_only_non_authoritative_axes(api, publication):
    root, policy = publication
    assert api.replay(root, policy, digest(policy)) == EXPECTED
    validated = api.validate_publication(root, policy, digest(policy))
    assert validated["manifest"]["extensions"][0]["payload"]["authority"] == "EXECUTE"
    assert validated["result"] == EXPECTED
    assert validated["result"]["authority"] == "NONE"


def test_consumer_matches_restricted_jcs_vectors_without_producer_imports(api):
    vectors = json.loads((HERE.parents[1] / "tests/fixtures/source_catalogue_v1/canonical-vectors.json").read_bytes())
    for vector in vectors:
        assert api.canonical_bytes(vector["value"]) == vector["canonical"].encode("utf-8")
    source = (HERE / "consumer.py").read_text()
    imports = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(name == "mathgraph" or name.startswith("mathgraph.")
                   or name == "mathgraph_protocol" or name.startswith("mathgraph_protocol.") for name in imports)


@pytest.mark.parametrize("raw,code", [
    (b'{"schema":1,"schema":2}', "DUPLICATE_JSON_KEY"),
    (b'{"n":NaN}', "NONFINITE_JSON_NUMBER"),
    (b'{"n":1.0}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":1e3}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":1e999}', "NONFINITE_JSON_NUMBER"),
    (b'{"n":-0}', "UNSUPPORTED_JSON_VALUE"),
    (b'\xef\xbb\xbf{}', "INVALID_UTF8"),
    (b'{"n":"\\ud800"}', "UNSUPPORTED_JSON_VALUE"),
])
def test_strict_decoder_declines_permissive_json(api, raw, code):
    with pytest.raises(api.CatalogueReplayError) as error:
        api.strict_load(raw, maximum=4096, canonical=False)
    assert error.value.code == code


@pytest.mark.parametrize("mutation", [
    "manifest_newline", "manifest_duplicate", "policy_bytes", "search_bytes", "missing_shard",
    "wrong_commit", "wrong_tree", "wrong_toolchain", "wrong_module_digest", "wrong_producer",
])
def test_pins_and_exact_bytes_fail_closed(api, publication, mutation):
    root, policy_path = publication
    manifest = json.loads((root / "manifest.json").read_bytes())
    policy = json.loads(policy_path.read_bytes())
    expected_policy_sha = digest(policy_path)
    if mutation == "manifest_newline":
        (root / "manifest.json").write_bytes((root / "manifest.json").read_bytes() + b"\n")
    elif mutation == "manifest_duplicate":
        raw = (root / "manifest.json").read_text()
        (root / "manifest.json").write_text(raw.replace('{"authority":', '{"authority":"NONE","authority":', 1))
    elif mutation == "policy_bytes":
        policy["source"]["commit"] = "0" * 40
        write_canonical(api, policy_path, policy)
    elif mutation == "search_bytes":
        (root / "search.json").write_bytes(b"[]")
    elif mutation == "missing_shard":
        (root / manifest["shards"][0]["path"]).unlink()
    elif mutation == "wrong_commit":
        manifest["source"]["commit"] = "0" * 40
        write_canonical(api, root / "manifest.json", manifest)
    elif mutation == "wrong_tree":
        manifest["source"]["tree"] = "0" * 40
        write_canonical(api, root / "manifest.json", manifest)
    elif mutation == "wrong_toolchain":
        manifest["source"]["lean_toolchain"]["value"] = "leanprover/lean4:v4.35.0"
        write_canonical(api, root / "manifest.json", manifest)
    elif mutation == "wrong_module_digest":
        manifest["modules"][0]["sha256"] = "0" * 64
        write_canonical(api, root / "manifest.json", manifest)
    elif mutation == "wrong_producer":
        manifest["extractor"]["source_commit"] = "0" * 40
        write_canonical(api, root / "manifest.json", manifest)
    with pytest.raises(api.CatalogueReplayError):
        api.replay(root, policy_path, expected_policy_sha)


@pytest.mark.parametrize("mutation", [
    "terminal_form", "verified_status", "execute_authorization", "critical_extension", "schema_version",
    "unknown_object_type", "evidence_edge", "implication", "equivalence", "assumptions", "unknown_endpoint",
])
def test_semantic_and_authority_mutations_remain_declined_even_when_rehashed(api, publication, mutation):
    root, policy_path = publication
    manifest = json.loads((root / "manifest.json").read_bytes())
    policy = json.loads(policy_path.read_bytes())
    shard = json.loads((root / manifest["shards"][0]["path"]).read_bytes())
    if mutation == "terminal_form":
        shard["objects"][0]["terminal_form"] = "VERIFIED_PROOF"
    elif mutation == "verified_status":
        shard["objects"][0]["verification_status"] = "VERIFIED"
    elif mutation == "execute_authorization":
        shard["objects"][0]["authorization"] = "EXECUTE"
    elif mutation == "critical_extension":
        shard["extensions"] = [{"id": "future", "version": 1, "critical": True, "payload": {}}]
    elif mutation == "schema_version":
        shard["catalogue_version"] = 2
    elif mutation == "unknown_object_type":
        shard["objects"][0]["kind"] = "recursor"
    elif mutation == "evidence_edge":
        shard["relations"][0]["type"] = "EVIDENCE_SUPPORTS"
    elif mutation == "implication":
        shard["relations"][0]["logical_implication"] = True
    elif mutation == "equivalence":
        shard["relations"][0]["semantic_equivalence"] = True
    elif mutation == "assumptions":
        shard["relations"][0]["assumptions"] = []
    elif mutation == "unknown_endpoint":
        shard["relations"][0]["target_id"] = "object-" + "0" * 64
    repin_shard(api, root, manifest, shard)
    manifest["counts"]["relations"] = len(shard["relations"])
    manifest["counts"]["objects"] = len(shard["objects"])
    pin = repin_manifest(api, root, policy_path, manifest, policy)
    with pytest.raises(api.CatalogueReplayError):
        api.replay(root, policy_path, pin)


def test_rehashed_but_unapproved_catalogue_and_revision_generalization_are_rejected(api, publication):
    root, policy_path = publication
    manifest = json.loads((root / "manifest.json").read_bytes())
    policy = json.loads(policy_path.read_bytes())
    original_policy_sha = digest(policy_path)
    manifest["source"]["commit"] = "0" * 40
    policy["source"]["commit"] = "0" * 40
    repin_manifest(api, root, policy_path, manifest, policy)
    with pytest.raises(api.CatalogueReplayError, match="POLICY_PIN_MISMATCH"):
        api.replay(root, policy_path, original_policy_sha)


def test_noncritical_extension_is_preserved_but_cannot_promote_result(api, publication):
    root, policy_path = publication
    manifest = json.loads((root / "manifest.json").read_bytes())
    policy = json.loads(policy_path.read_bytes())
    manifest["extensions"].append({"id": "opaque.future", "version": 7, "critical": False,
                                   "payload": {"terminal_form": "VERIFIED_PROOF", "authority": "EXECUTE"}})
    pin = repin_manifest(api, root, policy_path, manifest, policy)
    validated = api.validate_publication(root, policy_path, pin)
    assert validated["manifest"]["extensions"][-1]["payload"]["authority"] == "EXECUTE"
    assert validated["result"] == EXPECTED


def test_cli_isolated_stdlib_import_audit_and_deterministic_output(api, publication):
    root, policy = publication
    command = [sys.executable, "-I", "-S", "-B", str(HERE / "consumer.py"),
               "--catalogue-root", str(root), "--policy", str(policy),
               "--policy-sha256", digest(policy), "--audit-imports"]
    first = subprocess.run(command, check=True, capture_output=True)
    second = subprocess.run(command, check=True, capture_output=True)
    assert first.stdout == second.stdout == api.canonical_bytes(EXPECTED)
    audit = json.loads(first.stderr)
    assert audit["isolated"] and audit["no_site"] and audit["dont_write_bytecode"]
    assert audit["forbidden_imports"] == []
    assert audit["network_access"] == "NOT_USED"


@pytest.mark.skipif(sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file(),
                    reason="native isolation qualification is available only on macOS")
def test_native_runner_mounts_only_declared_inputs_and_denies_network(api, publication):
    root, policy = publication
    command = [sys.executable, str(HERE / "run_isolated.py"), "--backend", "macos",
               "--catalogue-root", str(root), "--policy", str(policy),
               "--policy-sha256", digest(policy)]
    result = subprocess.run(command, capture_output=True, check=True)
    assert result.stdout == api.canonical_bytes(EXPECTED)
    metadata = json.loads(result.stderr)
    assert metadata["probe"]["network_denied"] is True
    assert metadata["probe"]["repository_unavailable"] is True
    assert metadata["replays_identical"] is True
    assert metadata["probe"]["inputs"] == sorted([
        "consumer.py", "trust-policy.json", "catalogue/manifest.json", "catalogue/search.json",
        "catalogue/shards/aa35bb93934c33d67afa4ccd25b8109d7a96c06eeee817a5bc1d6eb5921aed1a.json",
    ])
