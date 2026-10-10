"""Mathematical and fail-closed controls independent of a built JPL parser."""
import unittest

from research.l4yaml_external_acceptance_v1 import (
    fixtures, independent_event_check, SCHEMA, suite_expected_accept, decode_yaml_suite_space_only,
)


class L4YAMLExternalModelTests(unittest.TestCase):
    def test_anchor_policy_has_real_separator(self):
        for case in fixtures():
            if case.family == "self-reference-separator":
                self.assertTrue(independent_event_check(case.normative_events))
                self.assertFalse(independent_event_check(case.current_events))

    def test_unknown_anchor_rejected_under_both_policies(self):
        cases = [c for c in fixtures() if c.family == "undefined-alias-control"]
        self.assertEqual(len(cases), 4)
        for case in cases:
            self.assertFalse(independent_event_check(case.normative_events))
            self.assertFalse(independent_event_check(case.current_events))

    def test_sibling_alias_after_completed_anchor_allowed(self):
        cases = [c for c in fixtures() if c.family == "declared-alias-control"]
        self.assertEqual(len(cases), 4)
        for case in cases:
            self.assertTrue(independent_event_check(case.normative_events))
            self.assertTrue(independent_event_check(case.current_events))

    def test_document_reset_kills_alias_support(self):
        cases = [c for c in fixtures() if c.family == "document-reset"]
        for case in cases:
            self.assertFalse(independent_event_check(case.normative_events))

    def test_named_tag_guards(self):
        byid = {c.id: c for c in fixtures()}
        self.assertTrue(independent_event_check(byid["tag-declared"].normative_events))
        self.assertFalse(independent_event_check(byid["tag-undeclared"].normative_events))
        self.assertFalse(independent_event_check(byid["tag-document-reset"].normative_events))

    def test_lexical_quotes_and_comments_do_not_create_alias_events(self):
        cases = [c for c in fixtures() if c.family == "lexical-control"]
        self.assertEqual(len(cases), 4)
        for case in cases:
            self.assertTrue(independent_event_check(case.normative_events))
            self.assertEqual(case.normative_events, (("begin", ""),))

    def test_filename_and_mutant_anchors_are_unique(self):
        names = [c.id for c in fixtures()]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreater(len(names), 25)

    def test_independent_yaml_suite_fail_metadata_is_the_oracle(self):
        # Public corpus uses a typed 'fail: true', not key 'error'.
        self.assertFalse(suite_expected_accept({"tags": "error anchor", "fail": True}))
        self.assertFalse(suite_expected_accept({"tags": "error directive tag", "fail": True}))
        self.assertTrue(suite_expected_accept({"tags": "alias anchor"}))
        self.assertTrue(suite_expected_accept({"tags": "alias", "fail": False}))
        with self.assertRaises(ValueError):
            suite_expected_accept({"tags": "error anchor"})
        with self.assertRaises(ValueError):
            suite_expected_accept({"tags": "tag", "fail": "true"})

    def test_visible_space_source_encoding_is_not_literal_unicode(self):
        self.assertEqual(decode_yaml_suite_space_only("key:␣\\n"), "key: \\n".replace("\\n", "\n"))
        self.assertEqual(decode_yaml_suite_space_only("plain"), "plain")
        for symbol in ("↵", "∎", "»", "⇔", "←", "→"):
            with self.subTest(symbol=symbol):
                with self.assertRaisesRegex(ValueError, "UNSUPPORTED_YAML_SUITE_ENCODING"):
                    decode_yaml_suite_space_only(symbol)

    def test_full_yaml_language_claim_is_not_encapsulated(self):
        self.assertEqual(SCHEMA, "mathgraph.l4yaml.external-acceptance-audit.v1")


if __name__ == "__main__":
    unittest.main()
