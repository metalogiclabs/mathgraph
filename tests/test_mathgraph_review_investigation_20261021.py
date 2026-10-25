"""Evidence investigation decision comparison, with equal-information baseline.

Historical native external subject: goccy/go-yaml PR #958, recorded by pinned
research evidence. This is a replay of KNOWN findings, not novel discovery.
"""
import json, unittest
from mathgraph_check.warrant_resolution import Claim,Receipt,Route,resolve_graph

S="goccy/go-yaml#958@a34b94ecb553bb5a693296c30232a89026db79ca"
O="goccy/go-yaml#872@preexisting"
claims=[Claim("pr_repairs","formal",S),Claim("pr_no_introduced_regressions","formal",S),
        Claim("separate_issue_fix","formal",O),Claim("review_decision","formal",S)]
receipts=[Receipt("native_pr_matrix","formal",S),Receipt("original_suite","formal",S),
          Receipt("native_issue_repair","formal",O),Receipt("comparison_review","formal",S)]
routes=[Route("pr_repairs",("native_pr_matrix",)),
        Route("pr_no_introduced_regressions",("native_pr_matrix","original_suite")),
        Route("separate_issue_fix",("native_issue_repair",)),
        Route("review_decision",("comparison_review",),("pr_repairs","pr_no_introduced_regressions"))]

def recompute(withdrawn):
    return dict(resolve_graph(claims,routes,receipts,withdrawn=frozenset(withdrawn)).states)

def plain_baseline(withdrawn):
    # Competent conventional baseline receives SAME claims, routes and receipts.
    known=set(r.id for r in receipts)-set(withdrawn)
    supported=set()
    while True:
        next_={r.conclusion for r in routes if set(r.evidence)<=known and set(r.premises)<=supported}
        if next_==supported:return {c.id:("WARRANTED_BOUNDED" if c.id in supported else "UNKNOWN") for c in claims}
        supported=next_

class EvidenceInvestigation(unittest.TestCase):
    def test_competent_equal_information_baseline_matches_every_withdrawal(self):
        import itertools
        ids=[r.id for r in receipts]
        for bits in itertools.product([False,True],repeat=len(ids)):
            gone=[id for id,b in zip(ids,bits) if b]
            self.assertEqual(recompute(gone),plain_baseline(gone))
    def test_native_pr_receipt_loss_cannot_be_silently_explained_by_inherited_issue(self):
        result=recompute(["native_pr_matrix"])
        self.assertEqual(result["pr_repairs"],"UNKNOWN")
        self.assertEqual(result["review_decision"],"UNKNOWN")
        self.assertEqual(result["separate_issue_fix"],"WARRANTED_BOUNDED")
    def test_missing_separate_issue_receipt_does_not_falsely_block_author_pr(self):
        result=recompute(["native_issue_repair"])
        self.assertEqual(result["review_decision"],"WARRANTED_BOUNDED")
        self.assertEqual(result["separate_issue_fix"],"UNKNOWN")
    def test_no_receipt_is_authenticated_by_value_object(self):
        self.assertEqual(recompute([])["review_decision"],"WARRANTED_BOUNDED")
        # This is conditional receipt admission ONLY. Its provenance and
        # factual semantics MUST be checked at another authority boundary.

if __name__=="__main__":unittest.main()
