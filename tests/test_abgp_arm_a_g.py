import unittest

from mathgraph.abgp.analysis import analyze_a
from mathgraph.abgp.arm_a import (
    a_growth_analysis_input,
    audit_a_growth_episodes,
    generate_a_dev_records,
    generate_a_growth_episodes,
)
from mathgraph.abgp.arm_g import generate_g_dev_records


class ABGPArmAGTests(unittest.TestCase):
    def test_a_messages_are_nonidentifying_and_budgeted(self):
        records = generate_a_dev_records(24)
        self.assertEqual(len(records), 24)
        for record in records:
            self.assertGreater(record.compatible_optimal_action_count, 1)
            self.assertEqual(record.verifier_message_count, 1)
            self.assertEqual(record.repair_round_count, 1)
            self.assertEqual(record.equal_compute_units, record.verifier_compute_units)
            self.assertTrue(record.seed_digest)

    def test_a_is_deterministic_from_dev_seeds(self):
        self.assertEqual(generate_a_dev_records(16), generate_a_dev_records(16))

    def test_a_growth_episode_has_exact_old_language_collision_and_sealed_future(self):
        episodes = generate_a_growth_episodes(64)
        self.assertEqual(len(episodes), 64)
        self.assertEqual(len({episode.future_seed_digest for episode in episodes}), 64)
        for episode in episodes:
            self.assertNotEqual(episode.acquisition_seed_digest, episode.future_seed_digest)
            self.assertEqual(episode.posterior_action_support, 2)
            self.assertEqual(episode.verifier_message_count, 1)
            self.assertEqual(episode.construction_round_count, 1)
            self.assertEqual(episode.future_verifier_calls, 0)
            self.assertTrue(episode.old_language_complete)
            self.assertTrue(episode.extension_nonmeasurable)
            self.assertTrue(episode.extension_strictly_refines)
            self.assertTrue(episode.action_relevant_collision_witness)
            self.assertTrue(episode.constructor_verified_independently)
            self.assertFalse(episode.future_target_leak)
            self.assertTrue(episode.sham_extension_novel)
            self.assertTrue(episode.sham_budget_matched)

    def test_a_exact_bayes_ceiling_and_information_accounting_are_frozen(self):
        audit = audit_a_growth_episodes(generate_a_growth_episodes(128))
        self.assertEqual(audit["old_language_state_count"], 1)
        self.assertEqual(audit["message_class_count"], 2)
        self.assertEqual(audit["posterior_support_min"], 2)
        self.assertEqual(audit["c0_future"], 0.5)
        self.assertEqual(audit["c1_future"], 1.0)
        self.assertEqual(audit["csubstrate_future"], 1.0)
        self.assertEqual(audit["delta_h_bits"], 1.0)
        self.assertTrue(audit["exact_old_language_completeness"])
        self.assertTrue(audit["old_information_collision_witness"])
        self.assertTrue(audit["fresh_future_seed_separation"])

    def test_a_growth_payload_uses_prospective_future_and_three_primary_controls(self):
        raw = a_growth_analysis_input(generate_a_growth_episodes(256))
        self.assertEqual(
            set(raw["baselines"]),
            {"fixed_language_bayes", "sham_expansion", "equal_compute_recheck"},
        )
        self.assertTrue(raw["representation_growth_gate"])
        self.assertEqual(len(raw["treatment"]), 256)
        self.assertTrue(raw["hard_gates"]["future_no_verifier"])
        self.assertTrue(raw["hard_gates"]["message_nonidentifying"])
        result = analyze_a(raw)
        self.assertEqual(result["analysis_mode"], "STRENGTHENED_REPRESENTATION_GROWTH")
        self.assertGreaterEqual(result["effect"], 0.05)

    def test_a_growth_is_deterministic_from_dev_seeds(self):
        self.assertEqual(generate_a_growth_episodes(64), generate_a_growth_episodes(64))

    def test_g_preclassifies_and_matches_corruption(self):
        records = generate_g_dev_records(8)
        self.assertEqual(len(records), 8 * 5)
        by_world = {}
        for record in records:
            by_world.setdefault(record.world_index, []).append(record)
            self.assertTrue(record.relevance_computed_before_corruption)
            self.assertEqual(record.relevant_corruption_count, record.irrelevant_corruption_count)
            self.assertEqual(record.relevant_corruption_magnitude, record.irrelevant_corruption_magnitude)
            self.assertTrue(record.seed_digest)
            if record.dose > 0:
                self.assertGreater(record.relevant_corruption_count, 0)
        for world_records in by_world.values():
            self.assertEqual(
                [r.dose for r in sorted(world_records, key=lambda r: r.dose)],
                [0.0, 0.1, 0.25, 0.5, 1.0],
            )

    def test_g_is_deterministic_from_dev_seeds(self):
        self.assertEqual(generate_g_dev_records(6), generate_g_dev_records(6))


if __name__ == "__main__":
    unittest.main()
