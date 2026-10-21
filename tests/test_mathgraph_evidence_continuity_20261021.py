"""Exhaustive finite evidence-continuity experiment; not native software semantic transport.

Three source revisions, conjunctive and alternative supports, explicit withdrawal,
and a separate brute-force Boolean derivation oracle.
"""
import itertools
import unittest
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph

CLAIMS = [Claim(k,"formal","revision-series-v1") for k in ("api","integration","deploy","unrelated")]
RECEIPTS = [Receipt(k,"formal","revision-series-v1") for k in
            ("api_test","integration_test","alternate_integration","deployment_approval","other_test")]
ROUTES = [
 Route("api",("api_test",)),
 Route("integration",("integration_test",),("api",)),
 Route("integration",("alternate_integration",)),
 Route("deploy",("deployment_approval",),("integration",)),
 Route("unrelated",("other_test",)),
]
IDS = tuple(r.id for r in RECEIPTS)

def oracle(live):
    """Independent exhaustive enumeration of all 2^4 candidate claim sets."""
    names=tuple(c.id for c in CLAIMS)
    fixed=[]
    for flags in itertools.product((False,True),repeat=len(names)):
        state={k for k,b in zip(names,flags) if b}
        active={r.conclusion for r in ROUTES if set(r.evidence)<=live
                and set(r.premises)<=state}
        if state==active: fixed.append(state)
    if not fixed: raise AssertionError("no fixed point")
    least=min(fixed,key=len)
    if any(not least<=f for f in fixed): raise AssertionError("not a least fixed point")
    return least

class EvidenceContinuityExhaustive(unittest.TestCase):
    def test_all_32_evidence_states_against_independent_oracle(self):
        for bits in itertools.product((False,True), repeat=len(IDS)):
            live={r for r,yes in zip(IDS,bits) if yes}
            withdrawn=frozenset(set(IDS)-live)
            got=resolve_graph(CLAIMS,ROUTES,RECEIPTS,withdrawn=withdrawn)
            expected=oracle(live)
            actual={k for k,v in got.states.items() if v=="WARRANTED_BOUNDED"}
            self.assertEqual(actual,expected,withdrawn)

    def test_semantic_change_without_new_receipt_cannot_transport_evidence(self):
        # Evidence pinned to one source revision cannot support a distinct one
        old=Receipt("old-api-pass","formal","repo@revA")
        new=Claim("new-api-safety","formal","repo@revB")
        with self.assertRaisesRegex(ValueError,"CROSS_BOUNDARY"):
            resolve_graph([new],[Route(new.id,(old.id,))],[old])

    def test_unrelated_change_preserves_explicitly_independent_warrant(self):
        live=resolve_graph(CLAIMS,ROUTES,RECEIPTS,withdrawn=frozenset({"api_test"}))
        self.assertEqual(live.states["api"],"UNKNOWN")
        self.assertEqual(live.states["unrelated"],"WARRANTED_BOUNDED")

    def test_naive_global_reuse_is_wrong_when_assumptions_withdrawn(self):
        before=resolve_graph(CLAIMS,ROUTES,RECEIPTS)
        after=resolve_graph(CLAIMS,ROUTES,RECEIPTS,
                            withdrawn=frozenset({"api_test","alternate_integration"}))
        naive_cache=dict(before.states)
        self.assertEqual(naive_cache["deploy"],"WARRANTED_BOUNDED")
        self.assertEqual(after.states["deploy"],"UNKNOWN")
        self.assertEqual(after.states["unrelated"],"WARRANTED_BOUNDED")

if __name__=="__main__": unittest.main()
