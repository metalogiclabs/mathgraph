#!/usr/bin/env python3
"""Stdlib-only adversarial checks for the independent catalogue consumer."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("independent consumer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONSUMER = load_module("source_catalogue_v1_independent_consumer", HERE / "consumer.py")
RUNNER = load_module("source_catalogue_v1_isolation_runner", HERE / "run_isolated.py")
PASSED_CASES: set[str] = set()

STRICT_JSON_CASES = [
    (b'{"schema":1,"schema":2}', "DUPLICATE_JSON_KEY"),
    (b'{"n":NaN}', "NONFINITE_JSON_NUMBER"),
    (b'{"n":1.0}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":1e3}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":1e999}', "NONFINITE_JSON_NUMBER"),
    (b'{"n":-0}', "UNSUPPORTED_JSON_VALUE"),
    (b'\xef\xbb\xbf{}', "INVALID_UTF8"),
    (b'{"n":"\\ud800"}', "UNSUPPORTED_JSON_VALUE"),
]
PIN_MUTATIONS = [
    "manifest_newline", "manifest_duplicate", "policy_bytes", "search_bytes", "missing_shard",
    "wrong_commit", "wrong_tree", "wrong_toolchain", "wrong_module_digest", "wrong_producer",
]
SEMANTIC_MUTATIONS = [
    "terminal_form", "verified_status", "execute_authorization", "critical_extension", "schema_version",
    "unknown_object_type", "evidence_edge", "implication", "equivalence", "assumptions", "unknown_endpoint",
]
POLICY_IDENTITY_MUTATIONS = ["empty_producer", "duplicate_producer", "duplicate_wrapper"]
EXPECTED_CASES = {
    "exact_fixture", "consumer_import_audit", "unauthorized_revision", "multiline_range", "oversize_policy",
    "implementation_digests", "noncritical_extension", "cli_determinism",
    *{f"jcs_{index}" for index in range(5)},
    *{f"strict_json_{index}" for index in range(len(STRICT_JSON_CASES))},
    *{f"pin_{name}" for name in PIN_MUTATIONS},
    *{f"semantic_{name}" for name in SEMANTIC_MUTATIONS},
    *{f"policy_{name}" for name in POLICY_IDENTITY_MUTATIONS},
    *{f"isolation_oversize_{name}" for name in ("policy", "manifest", "shard")},
}


def mark(case: str) -> None:
    if case not in EXPECTED_CASES:
        raise AssertionError(f"undeclared conformance case: {case}")
    PASSED_CASES.add(case)


class Publication:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="source-catalogue-conformance-")
        base = Path(self.temporary.name)
        self.root = base / "catalogue"
        (self.root / "shards").mkdir(parents=True)
        self.manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
        shutil.copyfile(FIXTURES / "manifest.json", self.root / "manifest.json")
        shutil.copyfile(FIXTURES / "search.json", self.root / "search.json")
        shutil.copyfile(FIXTURES / "shard.json", self.root / self.manifest["shards"][0]["path"])
        self.policy_path = base / "trust-policy.json"
        shutil.copyfile(FIXTURES / "trust-policy.json", self.policy_path)

    def close(self):
        self.temporary.cleanup()

    def policy_pin(self):
        return hashlib.sha256(self.policy_path.read_bytes()).hexdigest()

    def write(self, path: Path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(CONSUMER.canonical_bytes(value))

    def repin_shard(self, manifest: dict, shard: dict):
        previous = self.root / manifest["shards"][0]["path"]
        raw = CONSUMER.canonical_bytes(shard)
        sha = hashlib.sha256(raw).hexdigest()
        metadata = manifest["shards"][0]
        metadata.update(
            path=f"shards/{sha}.json",
            sha256=sha,
            size_bytes=len(raw),
            object_count=len(shard["objects"]),
            relation_count=len(shard["relations"]),
            omitted_type_references=len(shard["omissions"]["type_references"]),
            omitted_imports=len(shard["omissions"]["imports"]),
            omitted_declarations=len(shard["omissions"]["declarations"]),
        )
        if previous.exists():
            previous.unlink()
        self.write(self.root / metadata["path"], shard)

    def repin_manifest(self, manifest: dict, policy: dict):
        self.write(self.root / "manifest.json", manifest)
        raw = (self.root / "manifest.json").read_bytes()
        policy["manifest"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        self.write(self.policy_path, policy)
        return self.policy_pin()


class IndependentConsumerConformance(unittest.TestCase):
    def test_exact_fixture_replays_without_authority(self):
        publication = Publication()
        self.addCleanup(publication.close)
        self.assertEqual(CONSUMER.replay(publication.root, publication.policy_path,
                                         publication.policy_pin()), EXPECTED)
        mark("exact_fixture")

    def test_restricted_jcs_vectors_and_import_independence(self):
        vectors = json.loads((HERE.parents[1] / "tests/fixtures/source_catalogue_v1/canonical-vectors.json").read_bytes())
        self.assertEqual(len(vectors), 5)
        for index, vector in enumerate(vectors):
            with self.subTest(index=index):
                self.assertEqual(CONSUMER.canonical_bytes(vector["value"]), vector["canonical"].encode("utf-8"))
                mark(f"jcs_{index}")
        imports = []
        for node in ast.walk(ast.parse((HERE / "consumer.py").read_text())):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any(name == "mathgraph" or name.startswith("mathgraph.")
                             or name == "mathgraph_protocol" or name.startswith("mathgraph_protocol.")
                             for name in imports))
        mark("consumer_import_audit")

    def test_strict_decoder_declines_permissive_json(self):
        for index, (raw, code) in enumerate(STRICT_JSON_CASES):
            with self.subTest(index=index):
                with self.assertRaises(CONSUMER.CatalogueReplayError) as raised:
                    CONSUMER.strict_load(raw, maximum=4096, canonical=False)
                self.assertEqual(raised.exception.code, code)
                mark(f"strict_json_{index}")

    def test_pins_and_exact_bytes_fail_closed(self):
        for mutation in PIN_MUTATIONS:
            with self.subTest(mutation=mutation):
                publication = Publication()
                try:
                    manifest = json.loads((publication.root / "manifest.json").read_bytes())
                    policy = json.loads(publication.policy_path.read_bytes())
                    expected_policy_sha = publication.policy_pin()
                    if mutation == "manifest_newline":
                        path = publication.root / "manifest.json"
                        path.write_bytes(path.read_bytes() + b"\n")
                    elif mutation == "manifest_duplicate":
                        path = publication.root / "manifest.json"
                        path.write_text(path.read_text().replace(
                            '{"authority":', '{"authority":"NONE","authority":', 1))
                    elif mutation == "policy_bytes":
                        policy["source"]["commit"] = "0" * 40
                        publication.write(publication.policy_path, policy)
                    elif mutation == "search_bytes":
                        (publication.root / "search.json").write_bytes(b"[]")
                    elif mutation == "missing_shard":
                        (publication.root / manifest["shards"][0]["path"]).unlink()
                    elif mutation == "wrong_commit":
                        manifest["source"]["commit"] = "0" * 40
                        publication.write(publication.root / "manifest.json", manifest)
                    elif mutation == "wrong_tree":
                        manifest["source"]["tree"] = "0" * 40
                        publication.write(publication.root / "manifest.json", manifest)
                    elif mutation == "wrong_toolchain":
                        manifest["source"]["lean_toolchain"]["value"] = "leanprover/lean4:v4.35.0"
                        publication.write(publication.root / "manifest.json", manifest)
                    elif mutation == "wrong_module_digest":
                        manifest["modules"][0]["sha256"] = "0" * 64
                        publication.write(publication.root / "manifest.json", manifest)
                    else:
                        manifest["extractor"]["source_commit"] = "0" * 40
                        publication.write(publication.root / "manifest.json", manifest)
                    with self.assertRaises((CONSUMER.CatalogueReplayError, OSError)):
                        CONSUMER.replay(publication.root, publication.policy_path, expected_policy_sha)
                    mark(f"pin_{mutation}")
                finally:
                    publication.close()

    def test_semantic_and_authority_mutations_decline_after_rehash(self):
        for mutation in SEMANTIC_MUTATIONS:
            with self.subTest(mutation=mutation):
                publication = Publication()
                try:
                    manifest = json.loads((publication.root / "manifest.json").read_bytes())
                    policy = json.loads(publication.policy_path.read_bytes())
                    shard = json.loads((publication.root / manifest["shards"][0]["path"]).read_bytes())
                    if mutation == "terminal_form": shard["objects"][0]["terminal_form"] = "VERIFIED_PROOF"
                    elif mutation == "verified_status": shard["objects"][0]["verification_status"] = "VERIFIED"
                    elif mutation == "execute_authorization": shard["objects"][0]["authorization"] = "EXECUTE"
                    elif mutation == "critical_extension":
                        shard["extensions"] = [{"id": "future", "version": 1, "critical": True, "payload": {}}]
                    elif mutation == "schema_version": shard["catalogue_version"] = 2
                    elif mutation == "unknown_object_type": shard["objects"][0]["kind"] = "recursor"
                    elif mutation == "evidence_edge": shard["relations"][0]["type"] = "EVIDENCE_SUPPORTS"
                    elif mutation == "implication": shard["relations"][0]["logical_implication"] = True
                    elif mutation == "equivalence": shard["relations"][0]["semantic_equivalence"] = True
                    elif mutation == "assumptions": shard["relations"][0]["assumptions"] = []
                    else: shard["relations"][0]["target_id"] = "object-" + "0" * 64
                    publication.repin_shard(manifest, shard)
                    manifest["counts"]["relations"] = len(shard["relations"])
                    manifest["counts"]["objects"] = len(shard["objects"])
                    pin = publication.repin_manifest(manifest, policy)
                    with self.assertRaises(CONSUMER.CatalogueReplayError):
                        CONSUMER.replay(publication.root, publication.policy_path, pin)
                    mark(f"semantic_{mutation}")
                finally:
                    publication.close()

    def test_rehashed_unapproved_revision_declines_under_external_policy_pin(self):
        publication = Publication()
        self.addCleanup(publication.close)
        manifest = json.loads((publication.root / "manifest.json").read_bytes())
        policy = json.loads(publication.policy_path.read_bytes())
        original_pin = publication.policy_pin()
        manifest["source"]["commit"] = "0" * 40
        policy["source"]["commit"] = "0" * 40
        publication.repin_manifest(manifest, policy)
        with self.assertRaises(CONSUMER.CatalogueReplayError):
            CONSUMER.replay(publication.root, publication.policy_path, original_pin)
        mark("unauthorized_revision")

    def test_empty_and_duplicate_source_identities_decline_after_rehash(self):
        for mutation in ("empty_producer", "duplicate_producer", "duplicate_wrapper"):
            with self.subTest(mutation=mutation):
                publication = Publication()
                try:
                    manifest = json.loads((publication.root / "manifest.json").read_bytes())
                    policy = json.loads(publication.policy_path.read_bytes())
                    if mutation == "empty_producer":
                        policy["producer"]["sources"] = []
                        manifest["extractor"] = deepcopy(policy["producer"])
                    elif mutation == "duplicate_producer":
                        policy["producer"]["sources"].append(deepcopy(policy["producer"]["sources"][0]))
                        manifest["extractor"] = deepcopy(policy["producer"])
                    else:
                        policy["qualification_wrapper"]["sources"].append(
                            deepcopy(policy["qualification_wrapper"]["sources"][0])
                        )
                    pin = publication.repin_manifest(manifest, policy)
                    with self.assertRaises(CONSUMER.CatalogueReplayError):
                        CONSUMER.replay(publication.root, publication.policy_path, pin)
                    mark(f"policy_{mutation}")
                finally:
                    publication.close()

    def test_impossible_multiline_source_range_declines_after_rehash(self):
        publication = Publication()
        self.addCleanup(publication.close)
        manifest = json.loads((publication.root / "manifest.json").read_bytes())
        policy = json.loads(publication.policy_path.read_bytes())
        shard = json.loads((publication.root / manifest["shards"][0]["path"]).read_bytes())
        shard["objects"][0]["source"]["range"] = {
            "start": {"line": 2, "column": 90, "byte": 91},
            "end": {"line": 3, "column": 98, "byte": 100},
        }
        publication.repin_shard(manifest, shard)
        pin = publication.repin_manifest(manifest, policy)
        with self.assertRaises(CONSUMER.CatalogueReplayError):
            CONSUMER.replay(publication.root, publication.policy_path, pin)
        mark("multiline_range")

    def test_oversize_policy_and_isolation_inputs_decline_before_whole_read(self):
        publication = Publication()
        self.addCleanup(publication.close)
        raw = b" " * (CONSUMER.MAX_POLICY_BYTES + 1)
        publication.policy_path.write_bytes(raw)
        with self.assertRaises(CONSUMER.CatalogueReplayError):
            CONSUMER.replay(publication.root, publication.policy_path, hashlib.sha256(raw).hexdigest())
        mark("oversize_policy")

        for target in ("policy", "manifest", "shard"):
            with self.subTest(target=target):
                candidate = Publication()
                try:
                    manifest = json.loads((candidate.root / "manifest.json").read_bytes())
                    limits = {"policy": RUNNER.MAX_POLICY_BYTES, "manifest": RUNNER.MAX_MANIFEST_BYTES,
                              "shard": RUNNER.MAX_SHARD_BYTES}
                    selected = {"policy": candidate.policy_path, "manifest": candidate.root / "manifest.json",
                                "shard": candidate.root / manifest["shards"][0]["path"]}[target]
                    changed = b" " * (limits[target] + 1)
                    selected.write_bytes(changed)
                    arguments = SimpleNamespace(
                        catalogue_root=candidate.root,
                        policy=candidate.policy_path,
                        policy_sha256=hashlib.sha256(changed).hexdigest()
                        if target == "policy" else candidate.policy_pin(),
                        backend="docker", image_id="sha256:" + "1" * 64,
                        expected_wrapper_commit="9" * 40,
                        artifact_checksums_sha256="a" * 64,
                    )
                    with self.assertRaisesRegex(ValueError, "input exceeds byte limit"):
                        RUNNER.run(arguments)
                    mark(f"isolation_oversize_{target}")
                finally:
                    candidate.close()

    def test_implementation_digest_evidence_is_exact(self):
        self.assertEqual(RUNNER.implementation_digests(), {
            "consumer.py": hashlib.sha256((HERE / "consumer.py").read_bytes()).hexdigest(),
            "run_isolated.py": hashlib.sha256((HERE / "run_isolated.py").read_bytes()).hexdigest(),
        })
        mark("implementation_digests")

    def test_noncritical_extension_cannot_promote_result(self):
        publication = Publication()
        self.addCleanup(publication.close)
        manifest = json.loads((publication.root / "manifest.json").read_bytes())
        policy = json.loads(publication.policy_path.read_bytes())
        manifest["extensions"].append({"id": "opaque.future", "version": 7, "critical": False,
                                       "payload": {"terminal_form": "VERIFIED_PROOF", "authority": "EXECUTE"}})
        pin = publication.repin_manifest(manifest, policy)
        validated = CONSUMER.validate_publication(publication.root, publication.policy_path, pin)
        self.assertEqual(validated["result"], EXPECTED)
        mark("noncritical_extension")

    def test_cli_isolated_import_audit_and_output_are_deterministic(self):
        publication = Publication()
        self.addCleanup(publication.close)
        command = [sys.executable, "-I", "-S", "-B", str(HERE / "consumer.py"),
                   "--catalogue-root", str(publication.root), "--policy", str(publication.policy_path),
                   "--policy-sha256", publication.policy_pin(), "--audit-imports"]
        first = subprocess.run(command, check=True, capture_output=True)
        second = subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stdout, CONSUMER.canonical_bytes(EXPECTED))
        audit = json.loads(first.stderr)
        self.assertTrue(audit["isolated"] and audit["no_site"] and audit["dont_write_bytecode"])
        self.assertEqual(audit["forbidden_imports"], [])
        self.assertEqual(audit["network_access"], "NOT_USED")
        mark("cli_determinism")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentConsumerConformance)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or PASSED_CASES != EXPECTED_CASES:
        missing = sorted(EXPECTED_CASES - PASSED_CASES)
        extra = sorted(PASSED_CASES - EXPECTED_CASES)
        print(f"conformance case mismatch: missing={missing!r} extra={extra!r}", file=sys.stderr)
        raise SystemExit(1)
    report = {
        "schema": "mathgraph.source-catalogue-independent-conformance.v1",
        "result": "PASS",
        "authority": "NONE",
        "case_count": len(PASSED_CASES),
        "cases": sorted(PASSED_CASES),
        "unittest_methods": result.testsRun,
        "consumer_sha256": hashlib.sha256((HERE / "consumer.py").read_bytes()).hexdigest(),
        "conformance_sha256": hashlib.sha256((HERE / "stdlib_conformance.py").read_bytes()).hexdigest(),
    }
    sys.stdout.buffer.write(CONSUMER.canonical_bytes(report))
