"""Adversarial source-only calibration; no private ZIP or native binary in repo."""
import io
import json
import unittest
import zipfile

from rocket_profile import (
    ALTERNATIVE_FORMULA, BUNDLE_DIGEST, CSV_DIGESTS, FRETISH, FRET_SHA,
    MAP_DIGEST, R2U2_SHA, SOURCE_FORMULA, SPEC_DIGESTS,
    assess_archive, digest, minimal_two_event_witness
)


def fixture_parts():
    document = {
        "source": "NASA-SW-VnV FRET parser FretSemantics.compile (pinned source)",
        "fretish": FRETISH,
        "r2u2_code": SOURCE_FORMULA,
        "delayed_candidate_stream_adaptation": ALTERNATIVE_FORMULA,
        "reference_status": "published example; no independent owner-intent decision",
    }
    parts = {"rocket_formalization.json": json.dumps(document).encode()}
    for name, formula, role in (
        ("rocket_fretish", SOURCE_FORMULA, "actual FRETish R2U2 stream formula [0,7]"),
        ("rocket_delayed", ALTERNATIVE_FORMULA, "comparison [1,7], not owner-approved repair")
    ):
        spec = (
            "-- C2PO Specification Valid with C2PO/R2U2 v4.0 or greater\n"
            "INPUT\n\tBOOST: bool;\n\tCOAST: bool;\nFTSPEC\n"
            f"\tROCKET_RESPONSE: {formula};\n"
        ).encode().replace(b"\n", b"\r\n")
        mapping = b"BOOST:0\r\nCOAST:1\r\n"
        assert digest(spec) == SPEC_DIGESTS[name]
        assert digest(mapping) == MAP_DIGEST
        parts[name + ".c2po"] = spec
        parts[name + ".map"] = mapping
        parts[name + "_receipt.json"] = json.dumps({
            "schema": "mathgraph-r2u2-input-binding-pilot-v1",
            "role": role,
            "fret_commit": FRET_SHA,
            "r2u2_commit": R2U2_SHA,
            "signal_order": ["BOOST", "COAST"],
            "spec_sha256": digest(spec),
            "map_sha256": digest(mapping),
            "binary_sha256": "f" * 64,  # Intentionally untrusted.
        }).encode()

    def trace(boost, coast):
        return [{"BOOST": int(t == boost), "COAST": int(t == coast)} for t in range(8)]

    for name, observations in {
        "rocket_simultaneous": trace(0, 0),
        "rocket_next_tick": trace(0, 1),
        "rocket_no_coast": trace(0, -1),
        "rocket_no_boost": trace(-1, -1),
    }.items():
        csv = ("# BOOST, COAST\r\n" + "".join(
            f'{row["BOOST"]},{row["COAST"]}\n' for row in observations
        )).encode()
        assert digest(csv) == CSV_DIGESTS[name]
        parts[name + ".csv"] = csv
        parts[name + ".json"] = json.dumps(observations).encode()
    return parts


def pack(parts):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED) as archive:
        for name, payload in sorted(parts.items()):
            archive.writestr("pilot_fret_r2u2/" + name, payload)
    return stream.getvalue()


def assessment(parts):
    raw = pack(parts)
    return assess_archive(raw, digest(raw))


class TestRocketProfile(unittest.TestCase):
    def setUp(self):
        self.parts = fixture_parts()

    def test_finite_distinction_and_three_controls(self):
        report = assessment(self.parts)
        self.assertEqual(report["status"], "UNKNOWN")  # Overall.
        self.assertEqual(report["semantic_distinction"], "WARRANTED_BOUNDED_FINITE_ORACLE")
        self.assertEqual(report["finite_expected_verdict_count"], 64)
        self.assertIs(report["case_verdicts"]["simultaneous"]["source_0_7"][0], True)
        self.assertIs(report["case_verdicts"]["simultaneous"]["constructed_1_7"][0], False)
        for name, expected in (("next_tick", True), ("no_coast", False), ("no_boost", True)):
            for variant in ("source_0_7", "constructed_1_7"):
                self.assertIs(report["case_verdicts"][name][variant][0], expected)
        self.assertEqual(report["repair_authority"], "UNKNOWN")
        self.assertEqual(report["automatic_repair"], "DENIED")
        self.assertEqual(report["native_monitor_correspondence"], "UNKNOWN_BINARIES_NOT_IN_BUNDLE")

    def test_exhaustive_unique_two_event_witness(self):
        self.assertEqual(minimal_two_event_witness(), {
            "total_traces": 65536, "minimum_true_event_count": 2,
            "unique_minimum_mask": 257
        })

    def test_only_frozen_source_bundle_is_admitted_by_default(self):
        self.assertNotEqual(digest(pack(self.parts)), BUNDLE_DIGEST)
        self.assertEqual(assess_archive(pack(self.parts))["reason"], "ARCHIVE_IDENTITY_CHANGED")

    def test_changed_source_not_fixed_by_rehashing_envelope(self):
        self.parts["rocket_fretish.c2po"] = self.parts["rocket_fretish.c2po"].replace(
            b"F[0,7]", b"F[1,7]")
        self.assertEqual(assessment(self.parts)["reason"], "SOURCE_MAP_SPEC_MISMATCH:rocket_fretish")

    def test_changed_map_not_fixed_by_rehashing_envelope(self):
        self.parts["rocket_delayed.map"] = b"COAST:0\r\nBOOST:1\r\n"
        self.assertEqual(assessment(self.parts)["reason"], "SOURCE_MAP_SPEC_MISMATCH:rocket_delayed")

    def test_changed_csv_refused(self):
        self.parts["rocket_simultaneous.csv"] = self.parts["rocket_next_tick.csv"]
        self.assertEqual(assessment(self.parts)["reason"], "TRACE_SOURCE_CHANGED:rocket_simultaneous")

    def test_named_data_vs_csv_disagreement_refused(self):
        rows = json.loads(self.parts["rocket_simultaneous.json"])
        rows[0]["COAST"] = 0
        self.parts["rocket_simultaneous.json"] = json.dumps(rows).encode()
        self.assertEqual(assessment(self.parts)["reason"],
                         "TRACE_CSV_IDENTITY_MISMATCH:rocket_simultaneous")

    def test_short_trace_is_not_a_complete_eight_tick_case(self):
        self.parts["rocket_next_tick.json"] = b'[{"BOOST":1,"COAST":0}]'
        self.assertEqual(assessment(self.parts)["reason"],
                         "TRACE_DOMAIN_INVALID:rocket_next_tick")

    def test_changed_unsigned_receipt_refused(self):
        receipt = json.loads(self.parts["rocket_fretish_receipt.json"])
        receipt["spec_sha256"] = "0" * 64
        self.parts["rocket_fretish_receipt.json"] = json.dumps(receipt).encode()
        self.assertEqual(assessment(self.parts)["reason"],
                         "UNSIGNED_RECEIPT_SOURCE_MISMATCH:rocket_fretish")

    def test_owner_approval_field_cannot_grant_authority(self):
        receipt = json.loads(self.parts["rocket_delayed_receipt.json"])
        receipt.update({"owner_approved": True, "owner_signature": "fake"})
        self.parts["rocket_delayed_receipt.json"] = json.dumps(receipt).encode()
        report = assessment(self.parts)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["repair_authority"], "UNKNOWN")
        self.assertFalse(report["repair_eligible"])

    def test_forged_binary_digest_cannot_promote_native_replay(self):
        receipt = json.loads(self.parts["rocket_fretish_receipt.json"])
        receipt["binary_sha256"] = "a" * 64
        self.parts["rocket_fretish_receipt.json"] = json.dumps(receipt).encode()
        report = assessment(self.parts)
        self.assertEqual(report["native_monitor_correspondence"], "UNKNOWN_BINARIES_NOT_IN_BUNDLE")

    def test_missing_map_fails_closed(self):
        del self.parts["rocket_delayed.map"]
        self.assertEqual(assessment(self.parts)["reason"], "MISSING_SOURCE_MEMBER")

    def test_duplicate_json_key_fails_closed(self):
        self.parts["rocket_formalization.json"] = b'{"fretish":"a","fretish":"b"}'
        self.assertEqual(assessment(self.parts)["reason"], "DUPLICATE_JSON_KEY")

    def test_archive_scripts_are_never_executed(self):
        self.parts["arbitrary.py"] = b"raise Exception('must never run')\n"
        self.assertEqual(assessment(self.parts)["semantic_distinction"],
                         "WARRANTED_BOUNDED_FINITE_ORACLE")

    def test_corrupt_zip_never_promoted(self):
        self.assertEqual(assess_archive(b"not-zip", digest(b"not-zip"))["reason"],
                         "INVALID_ARCHIVE")

    def test_wrong_fret_source_commit_refused(self):
        receipt = json.loads(self.parts["rocket_fretish_receipt.json"])
        receipt["fret_commit"] = "a" * 40
        self.parts["rocket_fretish_receipt.json"] = json.dumps(receipt).encode()
        self.assertEqual(assessment(self.parts)["reason"],
                         "UNSIGNED_RECEIPT_SOURCE_MISMATCH:rocket_fretish")


if __name__ == "__main__":
    unittest.main()
