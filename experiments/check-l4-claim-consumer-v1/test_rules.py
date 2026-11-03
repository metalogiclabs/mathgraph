import unittest
from rules import remove_empty_ctors
class Mutation(unittest.TestCase):
    def test_removes_only_the_two_declared_empty_tail_constructors(self):
        text='other\n    | nil (x : Nat) : Other x\n'
        for n in ['Seq','Map']:
            text+=f'  inductive TCompact{n}Tail : Prop where\n    | nil (n : Nat) (s : SurfPos) :\n        TCompact{n}Tail n s s ([])\n    | cons : Other\n'
        changed=remove_empty_ctors(text)
        self.assertNotEqual(changed,text)
        self.assertIn('| nil (x : Nat) : Other x',changed)
        self.assertEqual(changed.count('| cons'),2)
        self.assertNotIn('Tail n s s ([])',changed)
    def test_missing_or_duplicated_mutation_target_is_unknown(self):
        for text in ['', '    | nil (n : Nat) (s : SurfPos) :\n        TCompactSeqTail n s s ([])\n'*2]:
            with self.assertRaises(ValueError):remove_empty_ctors(text)
import json,copy,hashlib
from pathlib import Path
from rules import admit
HERE=Path(__file__).parent
C=json.loads((HERE/'contract.json').read_text());SHA='a'*40
# Hand-declared matrix: modules compile in all arms; named constructor consumer
# is available only at head/restoration; a weakened offer always fails P's consumer.
def qualified():
    def ok(name='consumer'):return {'exit':0,'complete':True,'stdout':(f"'MathGraphClaim.{name}' depends on axioms: [propext]\n" if name in ['consumer','offered'] else f"'MathGraphClaim.{name}' does not depend on any axioms\n"),'stderr':''}
    def fail(message):return {'exit':1,'complete':True,'stdout':message,'stderr':''}
    rows={}
    for arm,strong in [('base',False),('head',True),('head_deleted',False),('head_restored',True)]:
        rows[arm]={'module':ok(),'source_witness':ok('sourceEmptyTails'),'strong_consumer':ok() if strong else fail('error(lean.unknownIdentifier): Unknown constant `L4YAML.Proofs.Serialization.TraceOf.TCompactSeqTail.nil`\nerror(lean.unknownIdentifier): Unknown constant `L4YAML.Proofs.Serialization.TraceOf.TCompactMapTail.nil`'),'weak_offer':ok('offered'),'weak_consumer':fail('error: Type mismatch: Or ... expected EmptyTailTrace')}
    return {'schema':'mathgraph.claim-consumer.receipt.v1','controller_sha':SHA,'repository':'metalogiclabs/L4YAML','base_sha':'1f97fbf881da6d1b9e2a7b9c547d1d3306f518ff','head_sha':'1153d648425fb15f6fe49061544f7ffe4bdcb520','contract_sha256':hashlib.sha256((HERE/'contract.json').read_bytes()).hexdigest(),'probes_sha256':C['probes_sha256'],'source_preserved':True,'shared_dependencies_identical':True,'surface_identical':True,'generator_outputs_match_checked_in':True,'restoration_identical':True,'arms':rows,'law':ok('weakeningDoesNotAuthorize')}
class Admission(unittest.TestCase):
    def test_complete_chain_admits_bounded_proof_and_named_api_obstruction(self):
        r=admit(qualified(),SHA)
        self.assertEqual(r['state'],'WARRANTED_BOUNDED')
        self.assertEqual(r['terminal_form'],'VERIFIED_PROOF')
        self.assertEqual(r['whole_generator_correctness'],'UNKNOWN')
    def test_missing_or_wrong_source_never_promotes(self):
        for field,value in [('arms',{}),('head_sha','0'*40),('controller_sha','b'*40),('source_preserved',False),('contract_sha256','0'*64),('shared_dependencies_identical',False),('generator_outputs_match_checked_in',False),('restoration_identical',False)]:
            r=qualified();r[field]=value;self.assertEqual(admit(r,SHA)['state'],'UNKNOWN',field)
    def test_compiler_failure_is_not_a_named_api_obstruction(self):
        r=qualified();r['arms']['base']['strong_consumer']['stdout']='import not found';self.assertEqual(admit(r,SHA)['state'],'UNKNOWN')
    def test_compilation_with_sorry_or_other_axioms_is_not_proof(self):
        r=qualified();r['arms']['head']['strong_consumer']['stdout']='depends on axioms: [sorryAx]';self.assertEqual(admit(r,SHA)['state'],'UNKNOWN')
    def test_timeout_or_wrong_mutation_outcome_does_not_qualify(self):
        for edit in [lambda r:r['arms']['head']['module'].update(exit=124,complete=False),lambda r:r['arms']['head_deleted']['strong_consumer'].update(exit=0),lambda r:r['arms']['head']['weak_consumer'].update(exit=0)]:
            r=qualified();edit(r);self.assertEqual(admit(r,SHA)['state'],'UNKNOWN')
    def test_build_progress_timing_does_not_change_restored_semantic_observations(self):
        r=qualified();r['arms']['head_restored']['module']['stdout']='Built Node (different elapsed time)';self.assertEqual(admit(r,SHA)['state'],'WARRANTED_BOUNDED')
    def test_unrelated_error_mentioning_constructor_names_remains_unknown(self):
        r=qualified()
        for arm in ['base','head_deleted']:r['arms'][arm]['strong_consumer']['stdout']='error: maximum recursion depth reached while elaborating ⟨TCompactSeqTail.nil n s, TCompactMapTail.nil n s⟩'
        self.assertEqual(admit(r,SHA)['state'],'UNKNOWN')
    def test_extra_compiler_error_alongside_expected_rejection_is_unknown(self):
        r=qualified();r['arms']['base']['strong_consumer']['stdout']+='\nerror: maximum recursion depth reached';self.assertEqual(admit(r,SHA)['state'],'UNKNOWN')

    def test_standard_axiom_is_explicit_and_additional_axiom_is_rejected(self):
        r=qualified();a=admit(r,SHA);self.assertEqual(a['state'],'WARRANTED_BOUNDED');self.assertEqual(a['proof_assumptions']['strong_consumer'],['propext']);self.assertEqual(a['axiom_free_claim'],'REJECTED')
        r['arms']['head']['strong_consumer']['stdout']="'MathGraphClaim.consumer' depends on axioms: [propext, Classical.choice]\n";self.assertEqual(admit(r,SHA)['state'],'UNKNOWN')
class Report(unittest.TestCase):
    def test_report_connects_claim_consumer_assumptions_and_limits(self):
        from report import render
        text=render(qualified(),SHA)
        for required in ['WARRANTED_BOUNDED','propext','head_deleted','P ∨ True','not a new bug discovery','UNKNOWN']:
            self.assertIn(required,text)
    def test_incomplete_report_never_shows_a_supported_claim(self):
        from report import render
        text=render({},SHA);self.assertIn('UNKNOWN',text);self.assertNotIn('WARRANTED_BOUNDED',text)
