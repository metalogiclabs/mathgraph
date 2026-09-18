import importlib.util
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class ExecutedPTests(unittest.TestCase):
    def api(self):
        name = 'mathgraph.abgp.executed_p'
        self.assertIsNotNone(importlib.util.find_spec(name), 'P needs an executed process boundary, not a serialization flag')
        return __import__(name, fromlist=['*'])

    def test_fresh_worker_cannot_read_files_network_parent_fds_or_launch_processes(self):
        api = self.api()
        with TemporaryDirectory() as d:
            secret = Path(d) / 'source-secret.txt'
            secret.write_text('DO_NOT_CROSS_RESTART')
            with secret.open() as handle:
                os.set_inheritable(handle.fileno(), True)
                response = api.run_worker({'operation': 'probe', 'path': str(secret), 'fd': handle.fileno()})
        self.assertNotEqual(response['pid'], os.getpid())
        self.assertEqual(response['sandbox']['seccomp_mode'], 2)
        self.assertEqual(response['sandbox']['no_new_privs'], 1)
        for event in ('file_read', 'file_write', 'raw_open', 'network', 'fork', 'exec', 'inherited_fd'):
            self.assertTrue(response['probes'][event]['blocked'], event)
        self.assertNotIn('DO_NOT_CROSS_RESTART', json.dumps(response))

    def test_invocation_refuses_source_examples_and_target_labels(self):
        api = self.api()
        for extra in ({'examples': [[0, 0]]}, {'target_policy': [0, 1, 2, 3]}, {'cache': {}}, {'verifier': True}):
            with self.subTest(extra=extra), self.assertRaises(api.WorkerProtocolError):
                api.run_worker({'operation': 'invoke', 'retained': None, 'contexts': [0, 1, 2, 3], **extra})

    def test_retention_deletion_and_reacquisition_are_separate_executions(self):
        api = self.api()
        result = api.execute_episode((2, 0, 3, 1))
        runs = result['runs']
        self.assertEqual(len({r['pid'] for r in runs.values()}), len(runs))
        self.assertEqual(runs['retained']['actions'], [2, 0, 3, 1])
        self.assertEqual(runs['deleted']['actions'], runs['cold']['actions'])
        self.assertNotEqual(runs['retained']['actions'], runs['deleted']['actions'])
        self.assertIsNone(runs['ablation']['retained'])
        self.assertTrue(runs['ablation']['removed'])
        self.assertEqual(runs['reacquired']['actions'], runs['retained']['actions'])
        self.assertGreater(runs['acquire']['candidate_checks'], 0)
        self.assertGreater(runs['reacquire']['candidate_checks'], 0)
        self.assertEqual(runs['retained']['trace']['candidate_checks'], 0)
        self.assertEqual(runs['retained']['trace']['source_example_reads'], 0)
        self.assertEqual(result['scores']['retained'], 1)
        self.assertEqual(result['scores']['deleted'], 0)

    def test_same_information_posterior_is_not_deliberately_weakened(self):
        api = self.api()
        result = api.execute_episode((2, 0, 3, 1))
        self.assertEqual(result['runs']['posterior']['posterior_size'], 1)
        self.assertEqual(result['runs']['posterior_invocation']['actions'], [2, 0, 3, 1])
        self.assertEqual(result['scores']['posterior'], result['scores']['retained'])
        self.assertFalse(result['structural_advantage_over_posterior'])

    def test_joint_bayes_optimizes_episode_success_not_four_marginal_ties(self):
        api = self.api()
        response = api.run_worker({'operation': 'posterior', 'examples': []})
        self.assertEqual(response['posterior_size'], 24)
        self.assertEqual(response['joint_actions'], [0, 1, 2, 3])
        self.assertEqual(response['joint_success_probability'], '1/24')

    def test_posterior_crosses_restart_as_weights_not_a_retained_capability(self):
        api = self.api()
        response = api.run_worker({'operation': 'posterior', 'examples': [[0, 2], [1, 0], [2, 3], [3, 1]]})
        self.assertNotIn('retained', response)
        self.assertEqual(sum(response['posterior_weights']), 1)
        inv = api.run_worker({'operation': 'posterior_invoke', 'posterior_weights': response['posterior_weights'], 'contexts': [0, 1, 2, 3]})
        self.assertFalse(inv['acquisition_code_loaded'])
        self.assertEqual(inv['actions'], [2, 0, 3, 1])

    def test_wrong_lineage_deletion_preserves_object(self):
        api = self.api()
        acquired = api.run_worker({'operation': 'acquire', 'examples': [[0, 2], [1, 0], [2, 3], [3, 1]]})
        result = api.run_worker({'operation': 'delete', 'retained': acquired['retained'], 'lineage': 'unrelated'})
        self.assertFalse(result['removed'])
        self.assertEqual(result['retained'], acquired['retained'])

    def test_tampered_retained_bytes_cannot_be_invoked(self):
        api = self.api()
        acquired = api.run_worker({'operation': 'acquire', 'examples': [[0, 2], [1, 0], [2, 3], [3, 1]]})
        data = dict(acquired['retained'])
        data['policy'] = [0, 1, 2, 3]
        with self.assertRaises(api.WorkerProtocolError):
            api.run_worker({'operation': 'invoke', 'retained': data, 'contexts': [0, 1, 2, 3]})

    def test_out_of_scope_query_returns_unknown_not_reconstruction(self):
        api = self.api()
        result = api.run_worker({'operation': 'invoke', 'retained': None, 'contexts': [5]})
        self.assertEqual(result['actions'], [None])
        self.assertEqual(result['trace']['candidate_checks'], 0)

    def test_invocation_image_does_not_contain_acquisition_handler(self):
        api = self.api()
        result = api.run_worker({'operation': 'invoke', 'retained': None, 'contexts': [0]})
        self.assertEqual(result.get('available_operations'), ['delete', 'invoke', 'probe'])
        self.assertFalse(result.get('acquisition_code_loaded', True))
        with self.assertRaises(api.WorkerProtocolError):
            api.run_worker({'operation': 'acquire', 'examples': []}, worker_kind='invocation')

    def test_sandbox_failure_is_not_silently_downgraded(self):
        api = self.api()
        with self.assertRaises(api.WorkerProtocolError):
            api.run_worker({'operation': 'probe', 'path': '/etc/hostname', 'fd': 99}, seccomp_library='/no/such/library.so')

    def test_runtime_batch_records_actual_random_draws_and_their_descendants(self):
        api = self.api()
        self.assertTrue(hasattr(api, 'trace_p_episodes'))
        batch = api.trace_p_episodes(2)
        audit = batch['ancestry']
        self.assertTrue(audit['structurally_disjoint_random_ancestors'])
        self.assertEqual(audit['independent_cluster_count'], 2)
        self.assertFalse(audit['statistical_independence_proved'])
        self.assertEqual(len(batch['episodes']), 2)
        self.assertTrue(all(e['scores']['posterior'] == e['scores']['retained'] for e in batch['episodes']))

    def test_other_namespaces_cannot_trigger_an_executed_batch(self):
        api = self.api()
        self.assertTrue(hasattr(api, 'trace_p_episodes'))
        with self.assertRaises(ValueError):
            api.trace_p_episodes(2, namespace='not-an-authorized-development-namespace')

    def test_forbidden_environment_is_not_inherited(self):
        api = self.api()
        os.environ['ABGP_PRIVATE_ACQUISITION_CACHE'] = 'private-untracked-state'
        try:
            result = api.run_worker({'operation': 'probe', 'path': '/etc/hostname', 'fd': 99})
        finally:
            del os.environ['ABGP_PRIVATE_ACQUISITION_CACHE']
        self.assertNotIn('ABGP_PRIVATE_ACQUISITION_CACHE', result['environment_keys'])
        self.assertFalse(result['project_modules_loaded'])


if __name__ == '__main__':
    unittest.main()
