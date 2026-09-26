"""Regression and admission lifecycle gates; added before implementation."""
import importlib.util
from mathgraph.protected_future import ContinuationStatus as S, ProtectedContinuation as Edge, ProtectedContinuationMachine as Machine
from mathgraph.query_gateway import CrystalQuestion, query_crystal


def test_revoked_counterexample_cannot_remain_authoritative():
    m = Machine('b', ('q',), (Edge('q', 'claim', ('holds',), S.EXCLUDED,
                support_refs=('checker',), evidence_refs=('countermodel',)),))
    q = CrystalQuestion('q', 'claim', ('holds',))
    answer = query_crystal(m, q)
    assert answer.status is S.UNKNOWN, 'Revoked negative evidence must lose authority too'
    assert answer.residual.reason == 'missing_live_support'


def test_independent_admission_boundary_exists():
    assert importlib.util.find_spec('mathgraph.fol_admission') is not None
import os
import shutil
from dataclasses import replace
import pytest
from mathgraph.atp_tptp import FirstOrderResidual, ATPCandidateEvidence
from mathgraph.protected_future import ContinuationStatus as S, ProtectedContinuation as Edge, ProtectedContinuationMachine as Machine
from mathgraph.query_gateway import CrystalQuestion, query_crystal, machine_from_dict, machine_to_dict


def residual(goal='mortal(socrates)'):
    return FirstOrderResidual('socrates', (('r','! [X] : (human(X) => mortal(X))'),('f','human(socrates)')),goal,boundary_ref='test:horn')


def evidence(r, status='Theorem'):
    candidate='CANDIDATE_WARRANTED' if status=='Theorem' else 'CANDIDATE_EXCLUDED'
    return ATPCandidateEvidence('unit-proposer',r.problem_id,r.id,r.tptp_sha256,status,candidate,0,0.,(),(),f'% SZS status {status} for test\n','')


def api():
    from mathgraph import fol_admission
    return fol_admission


def test_independent_horn_check_plan_proves_chain_not_names():
    r=FirstOrderResidual('renamed', (('f','p(b)'),('r1','! [Z] : (p(Z) => r(Z))'),('r2','! [T] : (r(T) => q(T))')), 'q(b)',boundary_ref='b')
    p=api().prepare_check(r)
    assert p.status is S.WARRANTED
    assert 'h2' in p.lean_source and 'h1' in p.lean_source
    assert 'sorry' not in p.lean_source and 'native_decide' not in p.lean_source


@pytest.mark.parametrize('bad', [
    '? [X] : human(X)', '! [X] : (human(X) => mortal(Y))',
    '! [X,Y] : (human(X) => mortal(Y))', 'human(f(a))',
    '~human(socrates)', 'human(socrates) | mortal(socrates)',
    'human(socrates)).\nfof(inject,axiom,$false', '1 = 2',
])
def test_unsupported_or_malformed_input_never_becomes_truth(bad):
    with pytest.raises(ValueError):
        api().prepare_check(FirstOrderResidual('bad',(('a',bad),),'mortal(socrates)'))


def test_reversed_implication_has_actual_finite_countermodel():
    r=FirstOrderResidual('reverse',(('r','! [X] : (human(X) => mortal(X))'),('f','mortal(socrates)')),'human(socrates)')
    plan=api().prepare_check(r)
    assert plan.status is S.EXCLUDED
    assert ('mortal','socrates') in plan.true_atoms
    assert ('human','socrates') not in plan.true_atoms
    assert 'Fin 1' in plan.lean_source


def test_different_constants_do_not_collapse():
    plan=api().prepare_check(residual('mortal(plato)'))
    assert plan.status is S.EXCLUDED
    assert len(plan.constants)==2


def test_boundary_problem_and_candidate_are_bound_before_checker(tmp_path):
    a=api(); r=residual(); m,q=a.initial_query(r)
    changed=residual('human(plato)')
    outcome=a.check_and_admit(m,q,r,evidence(changed),lean='does-not-exist',evidence_dir=tmp_path)
    assert outcome.status is S.UNKNOWN and outcome.reason=='candidate_problem_mismatch'
    assert outcome.machine==m
    mismatch=replace(q,source='unrelated')
    assert a.check_and_admit(m,mismatch,r,evidence(r),lean='does-not-exist',evidence_dir=tmp_path).reason=='question_problem_mismatch'


def test_unsupported_fragment_and_missing_checker_fail_closed(tmp_path):
    a=api(); r=residual(); m,q=a.initial_query(r)
    outcome=a.check_and_admit(m,q,r,evidence(r),lean='does-not-exist',evidence_dir=tmp_path)
    assert outcome.status is S.UNKNOWN and outcome.machine==m
    assert outcome.reason=='checker_unavailable'


def test_false_solver_theorem_cannot_be_admitted(tmp_path):
    a=api(); r=residual('mortal(plato)'); m,q=a.initial_query(r)
    outcome=a.check_and_admit(m,q,r,evidence(r),lean='does-not-exist',evidence_dir=tmp_path)
    assert outcome.status is S.UNKNOWN
    assert outcome.reason=='candidate_semantics_disagree'


def test_metadata_injection_and_colliding_export_names_rejected():
    a=api()
    with pytest.raises(ValueError): a.prepare_check(replace(residual(), boundary_ref='b\nfof(f,axiom,$false).'))
    with pytest.raises(ValueError): a.prepare_check(FirstOrderResidual('x',(('a-b','p(a)'),('a_b','q(a)')),'p(a)'))


def test_revoked_exclusion_does_not_conflict_with_live_proof():
    m=Machine('b',('q',),(
        Edge('q','c',('holds',),S.EXCLUDED,support_refs=('old',),evidence_refs=('e0',)),
        Edge('q','c',('holds',),S.WARRANTED,evidence_refs=('e1',))))
    assert query_crystal(m,CrystalQuestion('q','c',('holds',))).status is S.WARRANTED


def test_partial_outcome_query_does_not_call_distinct_outcomes_conflicting():
    m=Machine('b',('q',),(
        Edge('q','c',('a',),S.EXCLUDED,evidence_refs=('e0',)),
        Edge('q','c',('b',),S.WARRANTED,evidence_refs=('e1',))))
    answer=query_crystal(m,CrystalQuestion('q','c'))
    assert answer.residual.reason!='conflicting_authority'


def require_lean():
    lean=os.environ.get('LEAN', 'lean')
    if not shutil.which(lean):
        if os.environ.get('REQUIRE_LEAN')=='1': pytest.fail('live Lean gate cannot skip')
        pytest.skip('local environment has no Lean; hosted gate requires it')
    return lean


@pytest.mark.parametrize('goal, expected, szs', [('mortal(socrates)',S.WARRANTED,'Theorem'),('mortal(plato)',S.EXCLUDED,'CounterSatisfiable')])
def test_live_lean_admission_replay_and_revocation(goal,expected,szs,tmp_path):
    lean=require_lean(); a=api(); r=residual(goal); m,q=a.initial_query(r)
    assert query_crystal(m,q).status is S.UNKNOWN
    checked=a.check_and_admit(m,q,r,evidence(r,szs),lean=lean,evidence_dir=tmp_path)
    assert checked.status is expected, checked.record
    assert query_crystal(checked.machine,q).status is expected
    assert query_crystal(checked.machine,replace(q,live_supports=())).status is S.UNKNOWN
    restored=machine_from_dict(machine_to_dict(checked.machine))
    assert query_crystal(restored,q).to_dict()==query_crystal(checked.machine,q).to_dict()
    assert checked.record['axioms']==[]
    assert checked.record['validation_mode']=='independent_reproof_or_model_check'
    assert 'certificate' in checked.record['lean_stdout']


def test_live_false_certificate_fails_lean(tmp_path):
    lean=require_lean()
    report=api().check_lean_source('theorem certificate : False := by decide\n#print axioms certificate\n',lean=lean,evidence_dir=tmp_path)
    assert not report['accepted']
