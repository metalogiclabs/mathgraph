import copy
import unittest
import binding


class BindingTests(unittest.TestCase):
    def proposal(self, name):
        return copy.deepcopy(next(p for p in binding.POLICY['proposals'] if p['id'] == name))

    def check(self, name, **kwargs):
        return binding.bind(self.proposal(name), binding.POLICY['subject']['sha256'], **kwargs)

    def test_exact_reference_translation_admitted(self):
        for name in ['attached_ok', 'keyword_ok']:
            self.assertEqual(self.check(name)['status'], 'ADMITTED')

    def test_right_reference_cannot_authorize_wrong_typed_value(self):
        self.assertEqual(self.check('wrong_value')['status'], 'REJECTED')

    def test_true_expression_is_not_the_bound_obligation(self):
        self.assertEqual(self.check('weak_expression')['status'], 'UNKNOWN')
        self.assertEqual(self.check('weak_expression')['reason'], 'EXPRESSION_BINDING_MISMATCH')

    def test_fresh_source_digest_must_match(self):
        r = binding.bind(self.proposal('attached_ok'), '0' * 64)
        self.assertEqual(r['status'], 'UNKNOWN')
        self.assertEqual(r['reason'], 'SOURCE_CHANGED')

    def test_model_cannot_change_the_frozen_proposal(self):
        for field, value in [('reference_id','quoted_redirect'), ('expression','true'),
                             ('expected',[]), ('subject',{}), ('id','not_reviewed')]:
            p = self.proposal('attached_ok'); p[field] = value
            with self.subTest(field=field):
                self.assertEqual(binding.bind(p, binding.POLICY['subject']['sha256'])['status'], 'UNKNOWN')

    def test_missing_oracle_evidence_cannot_admit_expression(self):
        from unittest.mock import patch
        with patch.object(binding.reference, 'evaluate', return_value={
                'Conclusion':{'status':'UNKNOWN'}, 'Verification':{}}):
            self.assertEqual(self.check('attached_ok')['reason'], 'REFERENCE_NOT_SUPPORTED')

    def test_binding_alone_never_authorizes_repair(self):
        self.assertFalse(self.check('attached_ok')['repair_authorized'])

    def inspection(self):
        import hashlib,json
        rows=[{'id':p['id'],'execution':'CANDIDATE_ASSERTION_FAILURE' if p['id'] in ['keyword_ok','wrong_value'] else 'GUARD_PASSED','meaning':'UNVERIFIED'} for p in binding.POLICY['proposals']]
        fixed=copy.deepcopy(rows);fixed[1]['execution']='GUARD_PASSED'
        return {'complete':True,'subject':binding.POLICY['subject'],
                'policy_sha256':hashlib.sha256(json.dumps(binding.POLICY,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
                'source_guard_count':160,'repository_gate_exits':[0,0,0,0],
                'initial':{'rows':rows},'original':{'rows':rows},'repaired':{'rows':fixed},'withdrawn':{'rows':rows}}

    def test_denied_probes_are_retained_but_cannot_become_repair_obligations(self):
        r=binding.qualify(self.inspection())
        self.assertEqual(r['status'],'QUALIFIED_FINITE_CANDIDATE')
        self.assertEqual(r['repair_targets'],['keyword_ok'])
        self.assertEqual(r['excluded_probes'],['wrong_value','weak_expression'])

    def test_paired_evidence_missing_or_withdrawal_changed_cannot_qualify(self):
        for field,value in [('complete',False),('source_guard_count',0),('repository_gate_exits',[0,0,1,0]),('policy_sha256','altered')]:
            x=self.inspection();x[field]=value
            with self.subTest(field=field):self.assertEqual(binding.qualify(x)['status'],'UNKNOWN')
        x=self.inspection();x['withdrawn']=copy.deepcopy(x['repaired'])
        self.assertEqual(binding.qualify(x)['status'],'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
