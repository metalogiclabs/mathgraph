"""Independent native controls for evidence-seeking three-outcome merge decisions."""
import base64
import os
from pathlib import Path
import unittest

from merge_decision_lab import CASES, _select, experiment
from upstream_encoding_transfer import domain, oracle

def truth(cases):
    return {
        "reference":[oracle(x) for x in cases],
        "standard_alphabet":[base64.b64encode(x).rstrip(b"=") for x in cases],
        "unstripped_padding":[base64.urlsafe_b64encode(x) for x in cases],
        "trailing_zero_loss":[oracle(x.rstrip(b"\x00") if len(x)%3==0 else x)
                              for x in cases],
    }

class MergeDecisionTests(unittest.TestCase):
    def test_three_cases_frozen(self):
        self.assertEqual(CASES,(
            ("defective_green_tests","standard_alphabet",(1,2,3)),
            ("correct_but_initially_unknown","reference",(1,2,3)),
            ("correct_but_observation_forbidden","reference",(3,)),
        ))

    def test_minimum_basis_independently_verified(self):
        samples=domain()
        self.assertEqual(len(samples),1026)
        r=_select(samples,truth(samples),(1,2,3))
        self.assertEqual(r["status"],"MINIMUM_BASIS")
        self.assertEqual(r["tests_hex"],["00","f80000"])
        self.assertEqual(r["synthetic_cost"],6)
        self.assertEqual(r["independent_minimum_cost"],6)
        self.assertEqual(r["eligible_input_count"],1023)

    def test_forbidden_evidence_has_named_obstruction(self):
        samples=domain()
        r=_select(samples,truth(samples),(3,))
        self.assertEqual(r["status"],"OBSTRUCTION")
        self.assertEqual(r["unsplittable"],["unstripped_padding"])
        self.assertIsNone(r["synthetic_cost"])
        self.assertEqual(r["eligible_input_count"],256)

    def test_cost_shifts_when_one_byte_channel_forbidden(self):
        samples=domain()
        r=_select(samples,truth(samples),(2,3))
        self.assertEqual(r["tests_hex"],["0000","f80000"])
        self.assertEqual(r["synthetic_cost"],7)

    def test_no_observation_no_target_authority(self):
        samples=domain()
        r=_select(samples,truth(samples),())
        self.assertEqual(r["status"],"OBSTRUCTION")
        self.assertCountEqual(r["unsplittable"],
            ("standard_alphabet","trailing_zero_loss","unstripped_padding"))

    def test_real_source_native_decisions_and_authority_withdrawal(self):
        folder=os.environ.get("MATHGRAPH_PINNED_UPSTREAM")
        if not folder:
            self.skipTest("requires independent pinned upstream checkout")
        report=experiment(Path(folder))
        self.assertEqual(report["schema"],"mathgraph.evidence-seeking-merge-review.v1")
        self.assertEqual(report["model_provenance"],"OFFLINE_SCRIPTED_DECISIONS_NO_NEW_NEBIUS_CALL")
        self.assertEqual(report["actions_performed"],"READ_ONLY_SIMULATED_MERGE_REVIEW_NO_UPSTREAM_CHANGES")
        outcomes=report["cases"]
        self.assertEqual({k:v["final_state"] for k,v in outcomes.items()},{
            "defective_green_tests":"REJECTED",
            "correct_but_initially_unknown":"WARRANTED_BOUNDED",
            "correct_but_observation_forbidden":"UNKNOWN",
        })
        for name,x in outcomes.items():
            self.assertEqual(x["target_initially"],"UNKNOWN")
            self.assertEqual(x["fixed_suite_baseline"],"WARRANTED_ONLY_FOR_EXISTING_TESTS")
            steps=x["transitions"]
            self.assertEqual(steps[0]["state"],"WARRANTED_BOUNDED")
            self.assertEqual(steps[1]["state"],"UNKNOWN")
            self.assertTrue(all(s["state"] in
                ("UNKNOWN","REJECTED","WARRANTED_BOUNDED") for s in steps))
            if name=="correct_but_observation_forbidden":
                self.assertEqual(x["release_permission"],"NONE")
                self.assertNotIn("expanded_receipt",x)
            else:
                self.assertEqual(steps[-2]["step"],"source_changed_after_testing")
                self.assertEqual(steps[-2]["state"],"REJECTED")
                self.assertEqual(steps[-1]["state"],x["final_state"])
                self.assertEqual(
                    x["expanded_receipt"]["command"][-1],
                    "test_mathgraph_acquired.py")

if __name__=="__main__":
    unittest.main()
