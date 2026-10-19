"""Source-neutral protocol controls; these are NOT native PKC or L4YAML tests."""
import unittest

from protocol import Obligation, assess, judge


class ProtocolQualification(unittest.TestCase):
    def setUp(self):
        self.stamp = {"source": "sha1", "native": "sha2", "meaning": "sha3"}
        self.valid = Obligation("valid", "repo@sha1", "MATCH", "ASSERTED",
                                ("source", "native", "meaning"), "declared")
        self.bad = Obligation("bad", "repo@sha1", "MISMATCH", "ASSERTED",
                              ("source", "native", "meaning"), "declared")

    def test_valid_and_mismatch(self):
        self.assertEqual(judge(self.valid, self.stamp, self.stamp), "SCOPED_AGREEMENT")
        self.assertEqual(judge(self.bad, self.stamp, self.stamp), "DIVERGENT_BOUNDED")

    def test_unresolved_authority_never_promoted(self):
        o = Obligation("x", "repo@sha1", "MATCH", "UNRESOLVED",
                       ("source",), "pending contract")
        self.assertEqual(judge(o, self.stamp, self.stamp), "UNKNOWN_CONTRACT")

    def test_annotation_cannot_claim_semantic_agreement(self):
        o = Obligation("x", "repo@sha1", "MATCH", "ANNOTATION",
                       ("source",), "free text")
        self.assertEqual(judge(o, self.stamp, self.stamp), "NO_SEMANTIC_ASSERTION")

    def test_unsupported_not_false(self):
        o = Obligation("x", "repo@sha1", "UNSUPPORTED", "ASSERTED",
                       ("source",), "parser outside scope")
        self.assertEqual(judge(o, self.stamp, self.stamp), "UNKNOWN_INTERPRETATION")

    def test_missing_and_changed_dependency(self):
        for field in self.stamp:
            changed = dict(self.stamp)
            changed[field] = "mutant"
            self.assertEqual(judge(self.valid, changed, self.stamp),
                             "UNKNOWN_WITHDRAWN_OR_CHANGED")
            del changed[field]
            self.assertEqual(judge(self.bad, changed, self.stamp),
                             "UNKNOWN_WITHDRAWN_OR_CHANGED")

    def test_empty_evidence_never_promotes(self):
        o = Obligation("x", "repo@sha1", "MATCH", "ASSERTED", (), "declared")
        self.assertEqual(judge(o, self.stamp, self.stamp), "UNKNOWN_INCOMPLETE")

    def test_unrecognized_is_unknown(self):
        o = Obligation("x", "repo@sha1", "MAGIC", "ASSERTED",
                       ("source",), "unknown")
        self.assertEqual(judge(o, self.stamp, self.stamp), "UNKNOWN_RELATION")

    def test_dependency_changes_selectively(self):
        a = self.valid
        b = Obligation("other", "repo2@sha2", "MATCH", "ASSERTED",
                       ("other_source",), "independent")
        required = {**self.stamp, "other_source": "sha4"}
        changed = dict(required, native="mutated")
        out = assess((a, b), changed, required)
        self.assertEqual(out["valid"], "UNKNOWN_WITHDRAWN_OR_CHANGED")
        self.assertEqual(out["other"], "SCOPED_AGREEMENT")

    def test_duplicate_case_rejected(self):
        with self.assertRaises(ValueError):
            assess((self.valid, self.valid), self.stamp, self.stamp)


if __name__ == "__main__":
    unittest.main()
