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
