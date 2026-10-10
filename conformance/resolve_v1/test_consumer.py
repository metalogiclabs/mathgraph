"""Independent contract tests; no producer imports or generated expectations."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ConsumerTests(unittest.TestCase):
    def consumer(self):
        path = HERE / "consumer.py"
        self.assertTrue(path.exists(), "Standalone consumer is missing")
        spec = importlib.util.spec_from_file_location("standalone_resolve", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def inputs(self):
        self.assertTrue((HERE / "fixtures/bundle.json").exists(), "Canonical bundle is missing")
        return ((HERE / "fixtures/bundle.json").read_bytes(), (HERE / "trust-policy.json").read_bytes())

    def test_strict_json_rejects_ambiguous_or_nonfinite_values(self):
        c = self.consumer()
        for raw in [b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'[]']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                c.parse_json(raw)

    def test_historical_seven_states_and_temporal_boundaries(self):
        c = self.consumer()
        bundle, policy = self.inputs()
        report = c.replay(bundle, policy, digest(policy))
        self.assertEqual(report["historical_evidence_qualification"], "PINNED_INPUTS_QUALIFIED_UNDER_POLICY")
        self.assertEqual(report["current_applicability"], "UNKNOWN")
        self.assertEqual(report["freshness"], "NOT_CHECKED")
        self.assertEqual(report.get("revocation_or_supersession"), "NOT_CHECKED")
        self.assertEqual(report["action_authorization"], "NONE")
        self.assertEqual(report["lifecycle"], "IMMUTABLE_HISTORICAL_SNAPSHOT")
        self.assertEqual(report["historical_resolution"], {
            "openai.original_support.1": {"before": "SOURCE_DOCUMENTED", "after": "STALE", "changed": True},
            "openai.original_support.2": {"before": "SOURCE_DOCUMENTED", "after": "STALE", "changed": True},
            "openai.original_support.3": {"before": "SOURCE_DOCUMENTED", "after": "STALE", "changed": True},
            "openai.theorem.1": {"before": "UNKNOWN", "after": "UNKNOWN", "changed": False},
            "openai.theorem.2": {"before": "UNKNOWN", "after": "UNKNOWN", "changed": False},
            "openai.theorem.3": {"before": "UNKNOWN", "after": "UNKNOWN", "changed": False},
            "jpl.l4yaml.finite_parser_acceptance": {"before": "WARRANTED_BOUNDED", "after": "WARRANTED_BOUNDED", "changed": False},
        })
        self.assertEqual(c.replay(bundle, policy, digest(policy)), report)

    def test_bundle_and_member_substitution_fail_even_with_new_self_hashes(self):
        c = self.consumer()
        raw, policy = self.inputs()
        original = json.loads(raw)
        for name in ["record.json", "history.md", "jpl-record.json"]:
            for mode in ["bytes", "rehash", "size", "extra"]:
                bundle = copy.deepcopy(original)
                member = bundle["members"][name]
                if mode in {"bytes", "rehash"}:
                    data = base64.b64decode(member["data"]) + b" "
                    member["data"] = base64.b64encode(data).decode()
                    if mode == "rehash":
                        member.update(size=len(data), sha256=digest(data))
                elif mode == "size":
                    member["size"] = True
                else:
                    member["url"] = "https://untrusted.invalid"
                with self.subTest(name=name, mode=mode), self.assertRaises(ValueError):
                    c.replay(canonical(bundle), policy, digest(policy))
        for key, value in [("schema", "unknown"), ("current_applicability", "CURRENT"), ("trust_policy_sha256", digest(policy))]:
            bundle = copy.deepcopy(original)
            bundle[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.replay(canonical(bundle), policy, digest(policy))
        bundle = copy.deepcopy(original)
        bundle["provenance"]["producer"]["commit"] = "0" * 40
        with self.assertRaises(ValueError):
            c.replay(canonical(bundle), policy, digest(policy))

    def test_external_policy_pin_is_required_and_replacements_fail(self):
        c = self.consumer()
        bundle, raw = self.inputs()
        policy = json.loads(raw)
        policy["admissions"]["mathgraph.l4yaml.48-case-qualification"]["verifier"] = "arbitrary"
        with self.assertRaises(ValueError):
            c.replay(bundle, canonical(policy), digest(raw))
        for pin in ["", "0" * 64, None]:
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                c.replay(bundle, raw, pin)

    def test_same_length_rehashed_record_cannot_replace_authorized_bytes(self):
        c = self.consumer()
        raw, policy = self.inputs()
        bundle = json.loads(raw)
        member = bundle["members"]["record.json"]
        record = json.loads(base64.b64decode(member["data"]))
        record["sources"]["openai"]["notice_date"] = "2026-10-08"
        record.pop("snapshot_sha256")
        record["snapshot_sha256"] = digest(canonical(record).rstrip(b"\n"))
        changed = canonical(record)
        self.assertEqual(len(changed), 5290)
        self.assertNotEqual(digest(changed), member["sha256"])
        member.update(data=base64.b64encode(changed).decode(), sha256=digest(changed))
        with self.assertRaisesRegex(ValueError, "member pin mismatch"):
            c.replay(canonical(bundle), policy, digest(policy))

    def test_producer_states_are_comparison_assertions_not_resolution_inputs(self):
        c = self.consumer()
        raw, policy = self.inputs()
        members = json.loads(raw)["members"]
        record = json.loads(base64.b64decode(members["record.json"]["data"]))
        record["resolutions"]["openai.theorem.1"]["after"] = "REFUTED"
        with self.assertRaisesRegex(ValueError, "producer status assertion mismatch"):
            c.replay_record(record, json.loads(base64.b64decode(members["jpl-record.json"]["data"])), base64.b64decode(members["history.md"]["data"]), json.loads(policy))

    def test_boolean_assertions_cannot_be_replaced_by_numbers(self):
        c = self.consumer()
        raw, policy = self.inputs()
        members = json.loads(raw)["members"]
        record = json.loads(base64.b64decode(members["record.json"]["data"]))
        record["resolutions"]["openai.original_support.1"]["changed"] = 1
        with self.assertRaisesRegex(ValueError, "producer status assertion mismatch"):
            c.replay_record(record, json.loads(base64.b64decode(members["jpl-record.json"]["data"])), base64.b64decode(members["history.md"]["data"]), json.loads(policy))
        changed = json.loads(policy)
        changed["provenance"]["prior_independent_replay"]["independently_owned"] = 0
        replacement = canonical(changed)
        with self.assertRaisesRegex(ValueError, "unsupported authority profile"):
            c.replay(raw, replacement, digest(replacement))

    def test_semantic_mutations_are_rejected_after_transport_admission(self):
        c = self.consumer()
        raw, policy_raw = self.inputs()
        bundle = json.loads(raw)
        record = json.loads(base64.b64decode(bundle["members"]["record.json"]["data"]))
        jpl = json.loads(base64.b64decode(bundle["members"]["jpl-record.json"]["data"]))
        notice = base64.b64decode(bundle["members"]["history.md"]["data"])
        policy = json.loads(policy_raw)
        mutations = [
            lambda r: r.update(schema="unsupported"),
            lambda r: r.update(id="different-record"),
            lambda r: r["resolutions"]["openai.theorem.1"].update(after="REFUTED", changed=True),
            lambda r: r["derivation"]["claims"][0].update(kind="universal"),
            lambda r: r["derivation"]["claims"][0].update(scope="all mathematics"),
            lambda r: r["derivation"]["receipts"][0].update(id="forged-receipt"),
            lambda r: r["derivation"]["routes"][0].update(relation="generalization"),
            lambda r: r["derivation"].update(assumptions=["unverified"]),
            lambda r: r["sources"]["openai"].update(commit="0" * 40),
            lambda r: r["derivation"].update(withdrawn_evidence=[]),
            lambda r: r["publisher_notice"]["documents"][0].update(mathematical_truth="FALSE"),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(record)
            mutate(changed)
            changed.pop("snapshot_sha256")
            changed["snapshot_sha256"] = digest(canonical(changed).rstrip(b"\n"))
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                c.replay_record(changed, jpl, notice, policy)
        for field, value in [("verifier", "unknown"), ("assumptions", ["extra"]), ("scope", "universal")]:
            changed = copy.deepcopy(policy)
            changed["admissions"]["mathgraph.l4yaml.48-case-qualification"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                c.replay_record(record, jpl, notice, changed)

    def test_three_file_cli_is_deterministic_and_has_only_stdlib_imports(self):
        self.consumer()
        bundle, policy = self.inputs()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for src, name in [(HERE / "consumer.py", "consumer.py"), (HERE / "fixtures/bundle.json", "bundle.json"), (HERE / "trust-policy.json", "trust-policy.json")]:
                shutil.copyfile(src, directory / name)
            command = [sys.executable, "-I", "-S", "consumer.py", "--bundle", "bundle.json", "--policy", "trust-policy.json", "--policy-sha256", digest(policy)]
            first = subprocess.run(command, cwd=directory, capture_output=True)
            second = subprocess.run(command, cwd=directory, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            audit = subprocess.run(command + ["--audit-imports"], cwd=directory, capture_output=True)
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertEqual(audit.stdout, first.stdout)
            origins = json.loads(audit.stderr)["import_origins"]
            self.assertTrue(origins)
            for name, origin in origins.items():
                self.assertFalse(any(x in name for x in ("mathgraph", "publisher", "website", "discover", "develop")), name)
                self.assertNotIn("site-packages", origin)
                self.assertNotIn(str(ROOT), origin)
            self.assertEqual(sorted(p.name for p in directory.iterdir()), ["bundle.json", "consumer.py", "trust-policy.json"])
            missing_pin = subprocess.run(command[:-2], cwd=directory, capture_output=True)
            self.assertNotEqual(missing_pin.returncode, 0)

    def test_packager_reproduces_fixture_and_refuses_unpinned_inputs(self):
        self.consumer()
        bundle, policy = self.inputs()
        packager = ROOT / "scripts/package_mathgraph_resolve_v1.py"
        self.assertTrue(packager.exists(), "Deterministic packager is missing")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            notice = base64.b64decode(json.loads(bundle)["members"]["history.md"]["data"])
            (directory / "notice.md").write_bytes(notice)
            command = [sys.executable, str(packager), "--history", str(directory / "notice.md"), "--out", str(directory / "bundle.json")]
            result = subprocess.run(command, cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((directory / "bundle.json").read_bytes(), bundle)
            (directory / "notice.md").write_bytes(notice + b" ")
            result = subprocess.run(command, cwd=ROOT, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((directory / "bundle.json").read_bytes(), bundle)

    def test_isolation_harness_requires_actual_supported_isolation(self):
        harness = HERE / "run_isolated.py"
        self.assertTrue(harness.exists(), "Physical isolation harness is missing")
        _, policy = self.inputs()
        command = [sys.executable, str(harness), "--policy-sha256", digest(policy), "--backend", "docker", "--image-id", "python:3.11-slim"]
        result = subprocess.run(command, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"immutable image ID", result.stderr)
        command[-1] = "sha256:" + "0" * 64
        # An absent executable must be a failure, never an isolation skip.
        result = subprocess.run(command, capture_output=True, env={"PATH": "/nonexistent"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"ISOLATION_FAILED", result.stderr)


def synthetic():
    claims = [{"id": x, "kind": "documentary", "scope": "test:exact"} for x in ("root", "child", "unrelated", "cycle-a", "cycle-b", "missing")]
    receipts = [{"id": x, "kind": "documentary", "scope": "test:exact"} for x in ("one", "two", "other")]
    admissions = {r["id"]: {"kind": r["kind"], "scope": r["scope"], "verifier": "synthetic-document-v1", "assumptions": [], "source": "synthetic", "outcome": "SUPPORT"} for r in receipts}
    routes = [
        {"conclusion": "root", "premises": [], "evidence": ["one"]},
        {"conclusion": "root", "premises": [], "evidence": ["two"]},
        {"conclusion": "child", "premises": ["root"], "evidence": []},
        {"conclusion": "unrelated", "premises": [], "evidence": ["other"]},
        {"conclusion": "cycle-a", "premises": ["cycle-b"], "evidence": []},
        {"conclusion": "cycle-b", "premises": ["cycle-a"], "evidence": []},
        {"conclusion": "missing", "premises": ["cycle-a"], "evidence": ["other"]},
    ]
    return {"claims": claims, "receipts": receipts, "routes": routes, "withdrawn_evidence": []}, admissions


class SyntheticTests(unittest.TestCase):
    consumer = ConsumerTests.consumer
    def test_alternatives_descendants_unrelated_cycles_and_missing_support(self):
        c = self.consumer()
        graph, admissions = synthetic()
        before = c.resolve(graph, admissions, {"synthetic-document-v1"})
        self.assertEqual(before, {"root": "SOURCE_DOCUMENTED", "child": "SOURCE_DOCUMENTED", "unrelated": "SOURCE_DOCUMENTED", "cycle-a": "UNKNOWN", "cycle-b": "UNKNOWN", "missing": "UNKNOWN"})
        graph["withdrawn_evidence"] = ["one"]
        self.assertEqual(c.resolve(graph, admissions, {"synthetic-document-v1"}), before)
        graph["withdrawn_evidence"] = ["one", "two"]
        after = c.resolve(graph, admissions, {"synthetic-document-v1"})
        self.assertEqual(after["root"], "UNKNOWN")
        self.assertEqual(after["child"], "UNKNOWN")
        self.assertEqual(after["unrelated"], "SOURCE_DOCUMENTED")
        self.assertEqual(c.compare(before, after)["child"]["after"], "STALE")

    def test_conjunctive_receipts_and_all_routes_removed(self):
        c = self.consumer()
        graph, admissions = synthetic()
        graph["routes"] = [route for route in graph["routes"] if route["conclusion"] != "root"]
        graph["routes"].append({"conclusion": "root", "premises": [], "evidence": ["one", "two"]})
        before = c.resolve(graph, admissions, {"synthetic-document-v1"})
        graph["withdrawn_evidence"] = ["one"]
        self.assertEqual(c.resolve(graph, admissions, {"synthetic-document-v1"})["root"], "UNKNOWN")
        graph["withdrawn_evidence"] = []
        graph["routes"] = [route for route in graph["routes"] if route["conclusion"] != "root"]
        after = c.resolve(graph, admissions, {"synthetic-document-v1"})
        self.assertEqual(c.compare(before, after)["root"]["after"], "STALE")
        self.assertEqual(c.compare(before, after)["child"]["after"], "STALE")
        self.assertEqual(after["unrelated"], "SOURCE_DOCUMENTED")
        graph["routes"].reverse()
        graph["claims"].reverse()
        self.assertEqual(c.resolve(graph, admissions, {"synthetic-document-v1"}), after)

    def test_scope_kind_generalization_and_unresolved_references_fail_closed(self):
        c = self.consumer()
        graph, admissions = synthetic()
        for mutation in [
            lambda g: g["claims"][0].update(scope="all scopes"),
            lambda g: g["claims"][1].update(kind="formal"),
            lambda g: g["routes"][0].update(relation="equivalence"),
            lambda g: g["routes"][0].update(premises=["absent"]),
            lambda g: g["routes"][0].update(evidence=[]),
            lambda g: g["claims"].append(g["claims"][0]),
        ]:
            changed = copy.deepcopy(graph)
            mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                c.resolve(changed, admissions, {"synthetic-document-v1"})

    def test_refutation_requires_checked_exact_scope_finite_countermodel(self):
        c = self.consumer()
        graph = {"claims": [{"id": "commutative", "kind": "formal", "scope": "magma:commutative:order=2"}], "receipts": [{"id": "countermodel", "kind": "formal", "scope": "magma:commutative:order=2"}], "routes": [{"conclusion": "commutative", "premises": [], "evidence": ["countermodel"]}], "withdrawn_evidence": []}
        receipt = {"kind": "formal", "scope": "magma:commutative:order=2", "source": "synthetic", "verifier": "finite-magma-noncommutative-v1", "assumptions": [], "outcome": "REFUTE", "witness": {"schema": "finite-magma-countermodel.v1", "table": [[0, 0], [1, 0]], "assignment": [0, 1]}}
        allowed = {"finite-magma-noncommutative-v1"}
        self.assertEqual(c.resolve(graph, {"countermodel": receipt}, allowed), {"commutative": "REFUTED"})
        for mutation in [lambda r: r.pop("witness"), lambda r: r.update(witness_sha256="f" * 64), lambda r: r["witness"].update(table=[[0, 1], [1, 0]]), lambda r: r["witness"].update(assignment=[0, 0]), lambda r: r["witness"].update(table=[[0, 2], [1, 0]]), lambda r: r.update(scope="all magmas"), lambda r: r.update(verifier="label-only"), lambda r: r.update(assumptions=["commutativity"])]:
            changed = copy.deepcopy(receipt)
            mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                c.resolve(graph, {"countermodel": changed}, allowed)
        with self.assertRaises(ValueError):
            c.resolve(graph, {"countermodel": receipt}, set())
        graph["withdrawn_evidence"] = ["countermodel"]
        self.assertEqual(c.resolve(graph, {"countermodel": receipt}, allowed), {"commutative": "UNKNOWN"})


if __name__ == "__main__":
    unittest.main()
