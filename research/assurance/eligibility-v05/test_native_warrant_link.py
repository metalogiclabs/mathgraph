"""Frozen-scope research-only native-evidence -> existing BoundaryWarrant probe.

Inputs are exact public PR #282 artifact ZIPs downloaded in the workflow.
No mission-owner approval, new native compilation, or change to production.
Requires real ZIP bytes. Missing artifacts fail closed (never zero-test-green).
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from mathgraph_check.boundary_warrant import (
    Subject, Obligation, Relation, Verification, Conclusion, Dependency,
    BoundaryWarrant, required_dependencies, scope_identity, resolve_boundaries,
)
from mathgraph_check.warrant_resolution import Receipt

PR282_HEAD = "2b0e21e94e64ca54ff35c1d4572c60b3b6049720"
FRET_SHA = "cf0f913cc15c41705e803593297e89cd6056b839"
NATIVE_ZIP_SHA256 = "a273ad97e46f3a6501eec4eb8837ae0fc3293d46e28089819740619e5cb0c8d6"
QUAL_ZIP_SHA256 = "b767a44b8f1d4790e3a25cc4d21134d8c8bf260d55381b84306aba6505f9685a"
EXPECTED_SPECS = {
    "source": "61cdfdb56da7463f3fb220381649c011efb6d0a5177a841255540186f2b3ea15",
    "challenger": "cc16408a46782573397b8d6f06857fb011651adac90d1c8a9379213c9aef7100",
}
EXPECTED_MAP = "dc8649dfeefbccd35f1df8afbf25f8e14b10cc0ff97551b8b6aa79724f79ea2f"
CASES = ("simultaneous", "next_tick", "no_coast", "no_boost")
VARIANTS = ("source", "challenger")
SCHEMA = "mathgraph.check.rocket-native-replay.v1"


def digest_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def verify_historical_artifacts(native_zip: Path, qual_zip: Path, output: Path) -> None:
    """Exact prior artifact provenance; parse raw receipts, don't trust their labels."""
    if digest_file(native_zip) != NATIVE_ZIP_SHA256:
        raise ValueError("NATIVE_ZIP_CHANGED")
    if digest_file(qual_zip) != QUAL_ZIP_SHA256:
        raise ValueError("INDEPENDENT_ZIP_CHANGED")
    for zipped in (native_zip, qual_zip):
        with zipfile.ZipFile(zipped) as archive:
            for item in archive.namelist():
                if "/" in item or item.startswith("."):
                    raise ValueError("UNEXPECTED_ARCHIVE_PATH")
            archive.extractall(output)

    native = json.loads((output / "native-result.json").read_text())
    qual = json.loads((output / "independent-qualification.json").read_text())
    declaration = json.loads((output / "source-declaration.json").read_text())
    if native.get("schema") != SCHEMA:
        raise ValueError("WRONG_NATIVE_SCHEMA")
    if native.get("source_pins") != {
        "fret": FRET_SHA,
        "r2u2": "2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a",
    }:
        raise ValueError("WRONG_SOURCE_PINS")
    if native.get("source_sha256") != EXPECTED_SPECS or native.get("map_sha256") != EXPECTED_MAP:
        raise ValueError("WRONG_SPEC_OR_MAP_REFERENCE")
    if native.get("native_oracle_positions") != 64:
        raise ValueError("WRONG_CENSUS")
    if (native.get("overall"), native.get("auto_repair"), native.get("repair_authority")) != (
        "UNKNOWN", "DENIED", "UNKNOWN"
    ):
        raise ValueError("UNJUSTIFIED_NATIVE_AUTHORITY")
    if any(k in native for k in ("owner_approved", "operator", "authorized", "semantic_truth")):
        raise ValueError("SELF_ASSERTED_OWNER_AUTHORITY")
    if qual.get("schema") != "mathgraph.check.rocket-native-qualification.v1":
        raise ValueError("WRONG_QUAL_SCHEMA")
    if (qual.get("positions"), qual.get("native_scope"), qual.get("intent_status"),
        qual.get("permission"), qual.get("repair")) != (
        64, "WARRANTED_BOUNDED_EXACT_CASES", "UNKNOWN", "ADVISORY_ONLY", "DENIED"
    ):
        raise ValueError("UNSUPPORTED_QUAL_PROMOTION")
    if qual.get("artifact_sha256") != native.get("binary_sha256"):
        raise ValueError("INDEPENDENT_BINARY_MISMATCH")
    if qual.get("monitor_sha256") != native.get("monitor_executable_sha256"):
        raise ValueError("INDEPENDENT_MONITOR_MISMATCH")
    if (declaration.get("operational_owner_authority"),
        declaration.get("repair_permission")) != ("UNKNOWN", "DENIED"):
        raise ValueError("DECLARATION_PROMOTION")
    if declaration.get("actual_fret_export") != "(BOOST -> (F[0,7] COAST))":
        raise ValueError("WRONG_EXPORTED_SOURCE")
    if declaration.get("constructed_comparison") != "(BOOST -> (F[1,7] COAST))":
        raise ValueError("COMPARISON_SCOPE_CHANGED")
    for variant in VARIANTS:
        if digest_file(output / (variant + ".c2po")) != EXPECTED_SPECS[variant]:
            raise ValueError("SOURCE_CHANGED")
        if digest_file(output / (variant + ".map")) != EXPECTED_MAP:
            raise ValueError("MAP_CHANGED")
        if digest_file(output / (variant + ".bin")) != native["binary_sha256"][variant]:
            raise ValueError("BINARY_CHANGED")
    obs = native.get("observations", [])
    if len(obs) != 8:
        raise ValueError("OBSERVATION_COUNT_MISMATCH")
    seen = set()
    for row in obs:
        case, variant = row.get("scenario"), row.get("variant")
        if case not in CASES or variant not in VARIANTS:
            raise ValueError("WRONG_OBSERVATION_CASE")
        seen.add((case, variant))
        values = json.loads((output / (case + ".json")).read_text())
        if len(values) != 8:
            raise ValueError("WRONG_TRACE_LENGTH")
        minimum = 0 if variant == "source" else 1
        expected = []
        for t in range(8):
            successors = values[t + minimum:min(t + 8, 8)]
            expected.append(not bool(values[t]["BOOST"]) or
                            any(bool(value["COAST"]) for value in successors))
        if row.get("native") != expected or row.get("oracle") != expected:
            raise ValueError("FINITE_ORACLE_MISMATCH")
    if seen != set((c, v) for c in CASES for v in VARIANTS):
        raise ValueError("MISSING_OBSERVATIONS")


def build_warrants(out: Path):
    """Construct receipts ONLY AFTER independently pinned artifact checks."""
    dec_digest = digest_file(out / "source-declaration.json")
    warrants = []
    for variant in VARIANTS:
        study_policy = {
            "scope": "FOUR_EIGHT_TICK_BOOLEAN_CASES_ONLY",
            "variant": variant,
            "native_artifact": NATIVE_ZIP_SHA256,
            "qual_artifact": QUAL_ZIP_SHA256,
            "approved_action": "ADVISORY_ONLY",
            "mission_authority": "UNKNOWN",
        }
        (out / ("policy-" + variant + ".json")).write_text(
            json.dumps(study_policy, sort_keys=True) + "\n")
        subject = Subject("NASA-SW-VnV/fret", FRET_SHA, dec_digest)
        statement = ("source FRETish [0,7] native finite verdicts" if variant == "source"
                     else "researcher-constructed [1,7] native finite comparison")
        obligation = Obligation(
            "rocket-native-" + variant, statement, "STUDY_SCOPED_NOT_MISSION_OWNER",
            digest_bytes(statement.encode()),
        )
        relation = Relation(
            "implementation_fidelity_finite",
            "native decoded Boolean verdicts equal independently recomputed finite oracle",
            (("variant", variant), ("domain", "4x8 Boolean traces"), ("source", PR282_HEAD)),
        )
        verification = Verification(
            "native", "rocket-qualifier-" + variant, digest_file(out / ("policy-" + variant + ".json")),
            ("no mission approval", "no untested-input extension", "no fresh native execution"),
            "receipt-" + variant,
        )
        dependencies = list(required_dependencies(subject, obligation, relation, verification))
        for filename in (variant + ".c2po", variant + ".map", variant + ".bin",
                         "native-result.json", "independent-qualification.json",
                         "source-declaration.json"):
            dependencies.append(Dependency(
                "evidence", "artifact:" + variant + ":" + filename,
                digest_file(out / filename),
            ))
        warrant = BoundaryWarrant(
            subject, obligation, relation, verification,
            Conclusion("SUPPORTED", ("64 finite verdicts only", "no operational intent or repair grant")),
            tuple(dependencies),
        )
        receipt = Receipt(verification.receipt_id, "native", scope_identity(warrant))
        warrants.append((warrant, receipt))
    return warrants


def measured_live_dependencies(admitted, out: Path):
    """Re-read actual bytes; DO NOT accept a caller-supplied 'current' fingerprint."""
    fresh = {}
    for warrant, receipt in admitted:
        live_subject = replace(
            warrant.subject, source_sha256=digest_file(out / "source-declaration.json"))
        variant = warrant.obligation.id.removeprefix("rocket-native-")
        live_verification = replace(
            warrant.verification,
            policy_sha256=digest_file(out / ("policy-" + variant + ".json")),
        )
        for dep in required_dependencies(
            live_subject, warrant.obligation, warrant.relation, live_verification
        ):
            if dep.key in fresh and fresh[dep.key] != dep.sha256:
                raise ValueError("COLLIDING_CURRENT_DEPENDENCY")
            fresh[dep.key] = dep.sha256
        for dep in warrant.dependencies:
            if dep.role == "evidence":
                filename = dep.key.split(":", 2)[2]
                fresh[dep.key] = digest_file(out / filename)
    return fresh


class NativeWarrantIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        native_zip = Path(os.environ["ROCKET_NATIVE_ZIP"])
        qual_zip = Path(os.environ["ROCKET_QUAL_ZIP"])
        verify_historical_artifacts(native_zip, qual_zip, self.out)
        self.admitted = build_warrants(self.out)
        self.original_mapping = measured_live_dependencies(self.admitted, self.out)

    def states(self, current=None):
        result = resolve_boundaries(
            self.admitted,
            measured_live_dependencies(self.admitted, self.out) if current is None else current
        )
        return {w.obligation.id: result.states["boundary:" + scope_identity(w)]
                for w, receipt in self.admitted}

    def test_exact_pinned_native_receipts_support_only_finite_claims(self):
        self.assertEqual(self.states(), {
            "rocket-native-source": "WARRANTED_BOUNDED_NATIVE",
            "rocket-native-challenger": "WARRANTED_BOUNDED_NATIVE",
        })
        self.assertNotIn("mission_owner_approval", self.states())

    def test_stale_caller_fingerprint_is_not_authority(self):
        initial = self.states(self.original_mapping)
        p = self.out / "source.c2po"
        p.write_bytes(p.read_bytes() + b"\n-- deliberate source mutation\n")
        stale_mapping_wrongly_says = self.states(self.original_mapping)
        actual = self.states()
        self.assertEqual(initial, stale_mapping_wrongly_says)  # negative control on trusting metadata
        self.assertEqual(actual["rocket-native-source"], "UNKNOWN")
        self.assertEqual(actual["rocket-native-challenger"], "WARRANTED_BOUNDED_NATIVE")

    def test_policy_change_withdraws_only_dependent_warrant(self):
        p = self.out / "policy-source.json"
        p.write_bytes(p.read_bytes() + b" ")
        self.assertEqual(self.states()["rocket-native-source"], "UNKNOWN")
        self.assertEqual(self.states()["rocket-native-challenger"], "WARRANTED_BOUNDED_NATIVE")

    def test_source_declaration_change_withdraws_both(self):
        p = self.out / "source-declaration.json"
        p.write_bytes(p.read_bytes() + b" ")
        self.assertEqual(self.states(), {
            "rocket-native-source": "UNKNOWN",
            "rocket-native-challenger": "UNKNOWN",
        })

    def test_forged_owner_flag_is_refused_by_admission(self):
        p = self.out / "native-result.json"
        report = json.loads(p.read_text())
        report["owner_approved"] = True
        p.write_text(json.dumps(report))
        self.assertEqual(self.states()["rocket-native-source"], "UNKNOWN")
        self.assertEqual(self.states()["rocket-native-challenger"], "UNKNOWN")
        with self.assertRaisesRegex(ValueError, "NATIVE_ZIP_CHANGED"):
            # A changed native ZIP would fail exact external ZIP pin before processing claims.
            with zipfile.ZipFile(Path(self.tmp.name) / "forged.zip", "w") as z:
                z.write(p, arcname="native-result.json")
            verify_historical_artifacts(Path(self.tmp.name) / "forged.zip",
                                        Path(os.environ["ROCKET_QUAL_ZIP"]), self.out)

    def test_independent_archive_checksum_is_a_real_boundary(self):
        p = self.out / "independent-qualification.json"
        p.write_bytes(p.read_bytes() + b"\n")
        self.assertEqual(self.states(), {
            "rocket-native-source": "UNKNOWN",
            "rocket-native-challenger": "UNKNOWN",
        })


if __name__ == "__main__":
    unittest.main()
