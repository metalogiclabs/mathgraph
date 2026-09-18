import unittest

from mathgraph.abgp.analysis import analyze_p
from mathgraph.abgp.arm_p import (
    RetainedStructure,
    acquire_dev_structure,
    audit_p_episode_independence,
    generate_p_independent_episodes,
    p_independent_analysis_input,
    p_episode_resource_audit,
    run_p_dev_records,
)


class ABGPArmPTests(unittest.TestCase):
    def test_retained_structure_restart_is_byte_exact(self):
        structure = acquire_dev_structure()
        text = structure.to_text()
        restored = RetainedStructure.from_text(text)
        self.assertEqual(restored, structure)
        self.assertEqual(restored.to_text(), text)
        self.assertEqual(restored.digest, structure.digest)

    def test_future_boundary_has_zero_verifier_and_zero_search(self):
        records = run_p_dev_records(24)
        for record in records:
            self.assertEqual(record.future_verifier_calls, 0)
            self.assertEqual(record.future_reconstruction_search_count, 0)
            self.assertFalse(record.applicability_used_target_labels)
            self.assertTrue(record.source_distinct)
            self.assertFalse(record.forbidden_shared_features)

    def test_sham_wrong_class_and_targeted_deletion_are_causal_controls(self):
        records = run_p_dev_records(24)
        for record in records:
            self.assertNotEqual(record.retained_object_digest, record.sham_object_digest)
            self.assertNotEqual(record.retained_object_digest, record.wrong_class_object_digest)
            self.assertGreater(record.reacquisition_search_count_after_deletion, 0)
            self.assertEqual(record.post_deletion_correct, record.cold_correct)

    def test_p_is_deterministic_from_dev_seeds(self):
        self.assertEqual(run_p_dev_records(16), run_p_dev_records(16))

    def test_independent_episode_generator_has_one_acquisition_per_unit(self):
        episodes = generate_p_independent_episodes(32)
        self.assertEqual(len(episodes), 32)
        self.assertEqual(len({episode.acquisition_seed_digest for episode in episodes}), 32)
        for index, episode in enumerate(episodes):
            self.assertEqual(episode.episode_index, index)
            self.assertEqual(episode.future_contexts, (0, 1, 2, 3))
            self.assertEqual(episode.future_task_count, 4)
            self.assertEqual(episode.cross_restart_state_keys, ("retained_object_bytes",))
            self.assertEqual(episode.future_verifier_calls, 0)
            self.assertEqual(episode.future_reconstruction_search_count, 0)
            self.assertTrue(episode.restart_byte_exact)
            self.assertEqual(episode.reacquired_episode_success, episode.retained_episode_success)
            self.assertEqual(episode.reacquired_episode_success, 1)

    def test_independence_audit_counts_only_acquisitions_as_n(self):
        episodes = generate_p_independent_episodes(64)
        audit = audit_p_episode_independence(episodes)
        self.assertEqual(audit["inferential_unit"], "independent_acquisition_episode")
        self.assertEqual(audit["primary_n"], 64)
        self.assertEqual(audit["future_tasks_per_episode"], 4)
        self.assertTrue(audit["all_acquisition_seed_material_unique"])
        self.assertTrue(audit["all_future_seed_material_unique"])
        self.assertTrue(audit["one_acquisition_per_episode"])
        self.assertTrue(audit["nested_tasks_not_counted_as_n"])

    def test_episode_analysis_collapses_four_futures_to_one_binary_unit(self):
        episodes = generate_p_independent_episodes(48)
        raw = p_independent_analysis_input(episodes)
        self.assertEqual(raw["inferential_unit"], "independent_acquisition_episode")
        self.assertEqual(raw["future_tasks_per_episode"], 4)
        self.assertEqual(len(raw["retained"]), 48)
        self.assertTrue(all(len(values) == 48 for values in raw["baselines"].values()))
        self.assertEqual(raw["primary_episode_rule"], "all_four_context_probes_correct")
        self.assertIn("targeted_deletion", raw["baselines"])
        self.assertGreater(raw["reacquisition_search_count"], 0)
        self.assertTrue(raw["reacquisition_restored"])

        analysis = analyze_p(raw)
        self.assertEqual(analysis["analysis_mode"], "INDEPENDENT_EPISODE_POSTERIOR_BISIMULATION")
        self.assertEqual(len(analysis["component_pvalues"]), 7)
        self.assertIn("targeted_deletion", analysis["component_pvalues"])
        self.assertTrue(analysis["targeted_deletion_gate"])
        self.assertGreaterEqual(analysis["effect"], 0.05)

    def test_episode_resource_audit_is_deterministic_and_scales_by_acquisition(self):
        audit = p_episode_resource_audit(4096)
        self.assertEqual(audit["independent_acquisition_episodes"], 4096)
        self.assertEqual(audit["future_tasks_per_episode"], 4)
        self.assertEqual(audit["hard_restarts"], 0)
        self.assertEqual(audit["serialization_roundtrips"], 4096)
        self.assertFalse(audit["executed_isolation"])
        self.assertEqual(audit["future_invocations"], 4096 * 4)
        self.assertEqual(audit["maximum_policy_candidates_per_acquisition"], 24)
        self.assertEqual(audit["maximum_acquisition_candidate_checks"], 4096 * 24)
        self.assertEqual(audit, p_episode_resource_audit(4096))


if __name__ == "__main__":
    unittest.main()
