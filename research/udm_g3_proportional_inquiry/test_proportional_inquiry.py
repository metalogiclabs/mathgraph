import unittest
from proportional_inquiry import select_proportionate_observation, token_counts, WARRANT, SCHEMA

SHA='1'*40
DIGEST='2'*64

def arm(mode, status=WARRANT):
    return {'mode': mode, 'status': status, 'proposal_sha256': DIGEST,
            'base': {'status': 'FAIL_NATIVE_ASSERTION', 'count': 1},
            'head': {'status': 'PASS_SOURCE_NATIVE', 'count': 1},
            'ablation': {'status': 'UNKNOWN_ZERO_NAMED_TESTS', 'count': 0},
            'restoration': {'status': 'FAIL_NATIVE_ASSERTION', 'count': 1}}

def obj(b, d):
    return {'schema': SCHEMA, 'base_sha': SHA, 'head_sha': SHA,
            'results': [b, d]}

class MinimalConsequenceTests(unittest.TestCase):
    def test_direct_only_blocks_needless_expansion(self):
        r=select_proportionate_observation(obj(arm('bridge','UNKNOWN_REJECTED_TEST_STATIC_ADMISSION'),arm('direct')))
        self.assertEqual(r['selected_observer'], 'direct')
        self.assertEqual(r['new_grammar_necessary_for_goal'], 'NO')
        self.assertEqual(r['strict_g3'], 'UNKNOWN')
    def test_both_warrants_do_not_infer_distinct_operator_equivalence(self):
        r=select_proportionate_observation(obj(arm('bridge'),arm('direct')))
        self.assertEqual(r['selected_observer'], 'direct')
        self.assertEqual(r['fair_comparison'], 'BOTH_WITNESSED_SAME_VERSION_BOUNDARY')
    def test_bridge_only_does_not_prove_necessary_language(self):
        r=select_proportionate_observation(obj(arm('bridge'),arm('direct','UNKNOWN_NO_NEW_BASE_NATIVE_WITNESS')))
        self.assertEqual(r['status'], 'CANDIDATE_EXTENSION_WITH_NATIVE_WITNESS')
        self.assertEqual(r['new_grammar_necessary_for_goal'], 'UNKNOWN')
    def test_no_native_witness_refuses_promotion(self):
        r=select_proportionate_observation(obj(arm('bridge','UNKNOWN'),arm('direct','UNKNOWN')))
        self.assertEqual(r['status'], 'UNKNOWN_NO_VERIFIED_SOURCE_WITNESS')
    def test_wrong_source_sha_fails_closed(self):
        receipt=obj(arm('bridge'),arm('direct'));receipt['base_sha']='bad'
        self.assertEqual(select_proportionate_observation(receipt)['status'],'UNKNOWN_INVALID_RECEIPT')
    def test_duplicate_modes_fail_closed(self):
        self.assertEqual(select_proportionate_observation(obj(arm('direct'),arm('direct')))['status'],'UNKNOWN_INVALID_RECEIPT')
    def test_forged_native_success_fails_closed(self):
        forged=arm('direct');forged.pop('restoration')
        self.assertEqual(select_proportionate_observation(obj(arm('bridge','UNKNOWN'),forged))['status'],'UNKNOWN_INVALID_RECEIPT')
    def test_token_cost_is_not_dollar_economics(self):
        r={'schema':'mathgraph.g2.go-observer-proposals.v1','calls':[
         {'mode':'bridge','usage':{'input_tokens':123,'output_tokens':45}},
         {'mode':'direct','usage':{'input_tokens':120,'output_tokens':43}}]}
        x=token_counts(r)
        self.assertEqual(x['status'],'OBSERVED_TOKEN_COUNTS_ONLY')
        self.assertNotIn('dollars', x)
    def test_invalid_token_counts_fail_closed(self):
        r={'schema':'mathgraph.g2.go-observer-proposals.v1','calls':[
         {'mode':'bridge','usage':{'input_tokens':True,'output_tokens':1}},
         {'mode':'direct','usage':{'input_tokens':123,'output_tokens':1}}]}
        self.assertEqual(token_counts(r)['status'],'UNKNOWN_USAGE_RECEIPT')

if __name__=='__main__':unittest.main()