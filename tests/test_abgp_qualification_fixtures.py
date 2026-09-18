import json
import unittest

from mathgraph.abgp.qualification_fixtures import qualification_fixtures


EXPECTED_IDS = {
    "A_PLANTED_GROWTH",
    "A_BAYES_SUFFICIENT",
    "A_REENCODING_ONLY",
    "A_SHAM_EQUIVALENT",
    "A_DIRECT_ANSWER_LEAK",
    "B_PLANTED_TRANSFER",
    "B_TARGET_BISIM_SUFFICIENT",
    "B_POSTERIOR_SUFFICIENT",
    "B_SHUFFLED_ONLY",
    "B_TRANSLATION_LEAK",
    "G_PLANTED_DOSE_RESPONSE",
    "G_NULL_RELEVANCE",
    "G_GLOBAL_DAMAGE_ONLY",
    "G_REVERSED_RELEVANCE",
    "G_POSTHOC_LABELS",
    "P_PLANTED_PERSISTENCE",
    "P_POSTERIOR_MEMORY_SUFFICIENT",
    "P_TARGET_BISIM_SUFFICIENT",
    "P_SHAM_SUFFICIENT",
    "P_NONCAUSAL_RETENTION",
    "P_RESTART_LEAK",
}


class ABGPQualificationFixtureTests(unittest.TestCase):
    def test_inventory_is_frozen_and_complete(self):
        fixtures = qualification_fixtures()
        self.assertEqual({fixture.fixture_id for fixture in fixtures}, EXPECTED_IDS)
        self.assertEqual(len(fixtures), len(EXPECTED_IDS))
        self.assertEqual(
            {fixture.fixture_class for fixture in fixtures},
            {"PLANTED_POSITIVE", "ORDINARY_EXPLANATION", "BROKEN_MECHANICS"},
        )

    def test_raw_input_is_blind_to_expected_fixture_metadata(self):
        for fixture in qualification_fixtures():
            payload = json.dumps(fixture.raw_input, sort_keys=True)
            self.assertNotIn("fixture_class", payload)
            self.assertNotIn("expected_verdict", payload)
            self.assertNotIn("expected_reason_codes", payload)
            self.assertTrue(fixture.namespace.startswith(("ABGP-QUAL-", "ABGP-DEV-")))
            self.assertNotIn("ABGP-CONFIRM", fixture.namespace)

    def test_strengthened_ordinary_explanation_controls_are_present(self):
        fixtures = {f.fixture_id: f for f in qualification_fixtures()}
        a = fixtures["A_PLANTED_GROWTH"].raw_input
        self.assertEqual(
            set(a["baselines"]),
            {"fixed_language_bayes", "sham_expansion", "equal_compute_recheck"},
        )

        b = fixtures["B_PLANTED_TRANSFER"].raw_input
        self.assertIn("acquisition_posterior_target_bisimulation_bayes", b)
        self.assertEqual(len(set(b["direction_labels"])), 12)
        self.assertEqual(len(b["intervention_agreement"]), len(b["treatment"]) * 4)

        g = fixtures["G_PLANTED_DOSE_RESPONSE"].raw_input
        self.assertTrue(all("world_id" in record for record in g["pairs"]))
        self.assertEqual(len({record["world_id"] for record in g["pairs"]}), len(g["max_dose_relevant"]))

        p = fixtures["P_PLANTED_PERSISTENCE"].raw_input
        self.assertIn("target_only_bisimulation_bayes", p["baselines"])
        self.assertIn("posterior_only_retained_bayes", p["baselines"])
        self.assertIn("targeted_deletion", p["baselines"])
        self.assertEqual(len(p["baselines"]["targeted_deletion"]), len(p["retained"]))

    def test_planted_positive_witnesses_are_machine_checkable(self):
        fixtures = [f for f in qualification_fixtures() if f.fixture_class == "PLANTED_POSITIVE"]
        self.assertEqual({f.arm for f in fixtures}, {"A", "B", "G", "P"})
        for fixture in fixtures:
            self.assertIsInstance(fixture.witness, dict)
            self.assertTrue(fixture.witness.get("satisfiable"))
            self.assertTrue(fixture.witness.get("causal_status_known_by_construction"))


if __name__ == "__main__":
    unittest.main()
