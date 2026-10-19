"""Consequence-envelope v0 authority-boundary tests.

These are intentionally structural tests, not independent semantic replays.
Run: python -m unittest discover -s conformance/consequence_v0 -v
"""
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "protocol/schemas/consequence-envelope-v0.schema.json").read_text())


def validate_shape(obj):
    """Small strict subset of v0 JSON schema, independent of optional packages."""
    required = set(SCHEMA["required"])
    if not isinstance(obj, dict) or set(obj) != required:
        return False
    if obj["schema_version"] != "mathgraph.consequence-envelope.v0":
        return False
    if obj["kind"] not in SCHEMA["properties"]["kind"]["enum"]:
        return False
    if not all(isinstance(obj[k], str) and obj[k] for k in ("id", "version", "statement", "scope")):
        return False
    def ref(r):
        return isinstance(r, dict) and set(r) == {"locator", "sha256", "size_bytes"} and isinstance(r["locator"], str) and bool(r["locator"]) and isinstance(r["sha256"], str) and len(r["sha256"]) == 64 and all(c in "0123456789abcdef" for c in r["sha256"]) and type(r["size_bytes"]) is int and r["size_bytes"] >= 0
    if not all(v is None or ref(v) for v in (obj["authority"], obj["payload"], obj["assessment"])):
        return False
    if not isinstance(obj["evidence"], list) or not all(ref(v) for v in obj["evidence"]):
        return False
    if not isinstance(obj["relations"], list):
        return False
    for edge in obj["relations"]:
        if not isinstance(edge, dict) or set(edge) != {"type", "target_id", "target_version", "evidence"}:
            return False
        if edge["type"] not in SCHEMA["properties"]["relations"]["items"]["properties"]["type"]["enum"]:
            return False
        if not all(isinstance(edge[k], str) and edge[k] for k in ("target_id", "target_version")):
            return False
        if edge["evidence"] is not None and not ref(edge["evidence"]):
            return False
    return True


def sample():
    return dict(schema_version="mathgraph.consequence-envelope.v0", id="jpl:source-check", version="1", kind="observation", statement="48 bounded cases", scope="jpl:48-cases", authority=None, evidence=[], payload=None, relations=[], assessment=None)


class EnvelopeBoundary(unittest.TestCase):
    def test_minimal_shape(self):
        self.assertTrue(validate_shape(sample()))

    def test_top_level_authority_injection(self):
        x = sample()
        x["qualification"] = "WARRANTED"
        self.assertFalse(validate_shape(x))

    def test_scope_escalation_is_structurally_admitted_but_not_warranted(self):
        x = sample()
        x["scope"] = "universal"
        self.assertTrue(validate_shape(x))
        self.assertNotEqual(x["scope"], sample()["scope"])

    def test_untrusted_assessment_reference_does_not_grant_authority(self):
        x = sample()
        x["assessment"] = dict(locator="forged.json", sha256="0"*64, size_bytes=12)
        self.assertTrue(validate_shape(x))
        self.assertIsNone(sample()["assessment"])

    def test_unwarranted_lineage_is_structurally_admitted(self):
        x = sample()
        x["relations"] = [dict(type="derived_from", target_id="fiction", target_version="1", evidence=None)]
        self.assertTrue(validate_shape(x))

    def test_invalid_digest(self):
        x = sample()
        x["payload"] = dict(locator="source", sha256="bad", size_bytes=1)
        self.assertFalse(validate_shape(x))

    def test_boolean_size_is_invalid(self):
        x = sample()
        x["payload"] = dict(locator="source", sha256="0"*64, size_bytes=True)
        self.assertFalse(validate_shape(x))

    def test_no_authority_from_valid_shape(self):
        x = sample()
        self.assertTrue(validate_shape(x))
        self.assertIsNone(x["authority"])


if __name__ == "__main__":
    unittest.main()
