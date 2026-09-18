import json
import tempfile
import unittest
from pathlib import Path


class ImplementationQualificationTests(unittest.TestCase):
    def api(self):
        from mathgraph.abgp.implementation_qualification import run_implementation_qualification
        return run_implementation_qualification

    def test_qualification_uses_executed_matrix_not_synthetic_fixture_verdict(self):
        result = self.api()(a_count=12, b_worlds_per_direction=3, g_worlds=6, p_count=4)
        self.assertEqual(result['schema'], 'abgp.implementation-qualification.v1')
        self.assertEqual(result['mode'], 'DEV_EXECUTED_IMPLEMENTATION_QUALIFICATION')
        self.assertTrue(result['implementation_qualified'])
        self.assertFalse(result['complete_pass_power_qualified'])
        self.assertFalse(result['freeze_authorized'])
        self.assertFalse(result['confirmatory_namespace_used'])
        self.assertEqual(result['design_status'], 'FROZEN')
        self.assertEqual(result['generator_kinds'], {
            'A': 'executed_structural_construction',
            'B': 'independently_generated_cross_grammar',
            'G': 'causal_cell_evaluator_world_randomization',
            'P': 'hard_restart_source_distinct_structural_persistence',
        })
        self.assertEqual(set(result['scientific_dev_verdicts']), {'A', 'B', 'G', 'P'})
        self.assertEqual(result['scientific_interpretation'],
                         'DEV_IMPLEMENTATION_QUALIFICATION_NOT_CONFIRMATORY_EVIDENCE')

    def test_all_text_implementation_requirements_are_explicitly_mapped(self):
        result = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        mapping = result['requirement_evidence']
        self.assertEqual(set(mapping), {
            'A_information_boundary', 'B_grammar_independence',
            'G_world_exchangeability', 'P_restart_persistence',
            'inferential_ancestry', 'analysis_binding',
        })
        for key, row in mapping.items():
            self.assertTrue(row['implemented'], key)
            self.assertTrue(row['evidence'], key)
        for arm in 'ABGP':
            self.assertTrue(result['ancestry'][arm]['no_shared_generated_ancestor_across_scored_units'])
            self.assertFalse(result['ancestry'][arm]['statistical_independence_proved_by_this_audit'])

    def test_hash_manifest_binds_normative_and_executed_code(self):
        result = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        hashes = result['hash_manifest']
        required = {
            'preregistration/abgp-design-manifest-v1.json',
            'preregistration/abgp-analysis-plan-v1.json',
            'mathgraph/abgp/executed_a.py',
            'mathgraph/abgp/executed_b.py',
            'mathgraph/abgp/executed_g.py',
            'mathgraph/abgp/executed_p_structural.py',
            'mathgraph/abgp/executed_matrix.py',
            'mathgraph/abgp/analysis.py',
        }
        self.assertTrue(required <= set(hashes))
        self.assertTrue(all(len(value) == 64 for value in hashes.values()))

    def test_artifact_writer_is_canonical_and_replayable(self):
        from mathgraph.abgp.implementation_qualification import (
            write_implementation_qualification,
        )
        result = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'qualification.json'
            write_implementation_qualification(path, result)
            first = path.read_text(encoding='utf-8')
            self.assertTrue(first.endswith('\n'))
            self.assertEqual(json.loads(first), result)
            write_implementation_qualification(path, json.loads(first))
            self.assertEqual(path.read_text(encoding='utf-8'), first)

    def test_confirmation_namespace_cannot_be_used(self):
        with self.assertRaises(ValueError):
            self.api()(a_count=4, b_worlds_per_direction=1, g_worlds=2, p_count=1,
                       namespace='ABGP-CONFIRM-v1')


if __name__ == '__main__':
    unittest.main()
