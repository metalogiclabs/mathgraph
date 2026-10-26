"""Adversarial controls for model-proposed observation plans.

Mocks do not authenticate Nebius. Only a source-pinned workflow using a
private GitHub Actions secret can support a real inference claim.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from model_observation_merge import (
    ACTION_SCHEMA, NemotronObservationPlanner, ProposedAction, RIVALS,
    ScriptedPlanner, certify_action, menu_from_native, run_review,
)
from merge_decision_lab import _select
from upstream_encoding_transfer import domain, oracle


def independent_table(inputs):
    return {
        "reference":[oracle(v) for v in inputs],
        "standard_alphabet":[base64.b64encode(v).rstrip(b"=") for v in inputs],
        "unstripped_padding":[base64.urlsafe_b64encode(v) for v in inputs],
        "trailing_zero_loss":[oracle(v.rstrip(b"\x00") if len(v)%3==0 else v)
                              for v in inputs],
    }


class ObservationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=domain()
        cls.table=independent_table(cls.inputs)

    def test_scripted_planner_passes_all_three_frozen_cases(self):
        for case,lengths in (
            ("defective_green_tests",(1,2,3)),
            ("correct_but_initially_unknown",(1,2,3)),
            ("correct_but_observation_forbidden",(3,)),
        ):
            with self.subTest(case=case):
                exact=_select(self.inputs,self.table,lengths)
                menu=menu_from_native(self.inputs,self.table,lengths)
                proposal=ScriptedPlanner().propose(case,menu,lengths,1)
                result=certify_action(proposal.action,menu,exact)
                if exact["status"]=="OBSTRUCTION":
                    self.assertEqual(result["status"],"ACCEPTED_OBSTRUCTION")
                    self.assertEqual(result["unseparable"],["unstripped_padding"])
                else:
                    self.assertEqual(result["status"],"ACCEPTED_MINIMUM_BASIS")
                    self.assertEqual(result["cost"],6)

    def test_no_model_fabricated_approval_is_admitted(self):
        lengths=(1,2,3)
        exact=_select(self.inputs,self.table,lengths)
        menu=menu_from_native(self.inputs,self.table,lengths)
        bad=[
            None, "", [], {"decision":"approve", "tests_hex":["00"],"unseparable":[]},
            {"decision":"acquire", "tests_hex":["00"],"unseparable":[]},
            {"decision":"acquire", "tests_hex":["ffffffff"],"unseparable":[]},
            {"decision":"acquire", "tests_hex":["00","00"],"unseparable":[]},
            {"decision":"obstruction","tests_hex":[],"unseparable":[]},
            {"decision":"acquire","tests_hex":["00"],"unseparable":[],"shell":"rm -rf /"},
            {"decision":"acquire","tests_hex":[1],"unseparable":[]},
        ]
        for action in bad:
            with self.subTest(action=action),self.assertRaises(ValueError):
                certify_action(action,menu,exact)

    def test_wrong_obstruction_fails_closed(self):
        exact=_select(self.inputs,self.table,(3,))
        menu=menu_from_native(self.inputs,self.table,(3,))
        for action in (
            {"decision":"obstruction","tests_hex":[],"unseparable":[]},
            {"decision":"obstruction","tests_hex":[],"unseparable":["standard_alphabet"]},
            {"decision":"acquire","tests_hex":[],"unseparable":[]},
            {"decision":"obstruction","tests_hex":["f80000"],"unseparable":["unstripped_padding"]},
        ):
            with self.subTest(action=action),self.assertRaises(ValueError):
                certify_action(action,menu,exact)

    def test_uninformed_or_expensive_action_is_refused(self):
        exact=_select(self.inputs,self.table,(1,2,3))
        menu=menu_from_native(self.inputs,self.table,(1,2,3))
        first=ScriptedPlanner().propose("good",menu,(1,2,3),1).action
        self.assertEqual(certify_action(first,menu,exact)["cost"],6)
        extra=next((x["hex"] for x in menu if x["hex"] not in first["tests_hex"]),None)
        if extra is not None:
            more=dict(first,tests_hex=first["tests_hex"]+[extra])
            with self.assertRaisesRegex(ValueError,"TESTS_NOT_MINIMUM_COST"):
                certify_action(more,menu,exact)

    def test_absent_secret_and_rejected_non_nvidia_model(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,"NEBIUS_API_KEY_NOT_CONFIGURED"):
                NemotronObservationPlanner()
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"local-fake-nonsecret"}):
            with self.assertRaisesRegex(ValueError,"NVIDIA_OPEN_MODEL_REQUIRED"):
                NemotronObservationPlanner(model="other/model")

    def test_mock_nebius_schema_and_auth_header_not_logged(self):
        action={"decision":"acquire","tests_hex":["00","f80000"],"unseparable":[]}
        class FakeResponse:
            headers={"x-request-id":"mock-2026"}
            def __enter__(self): return self
            def __exit__(self,*_):return False
            def read(self,_): return json.dumps({
                "model":"nvidia/nemotron-3-super-120b-a12b",
                "choices":[{"finish_reason":"stop",
                           "message":{"content":json.dumps(action)}}],
            }).encode()
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"local-fake-nonsecret"}):
            provider=NemotronObservationPlanner()
            with patch("model_observation_merge.request.urlopen",return_value=FakeResponse()) as spy:
                response=provider.propose("defective_green_tests",
                    menu_from_native(self.inputs,self.table,(1,2,3)),(1,2,3),1)
                self.assertEqual(response.request_id,"mock-2026")
                self.assertEqual(response.action,action)
                self.assertEqual(response.provider,"nebius-token-factory")
                body=json.loads(spy.call_args.args[0].data)
                self.assertEqual(body["guided_json"],ACTION_SCHEMA)
                self.assertEqual(body["chat_template_kwargs"],{"enable_thinking":False})
                self.assertNotIn("local-fake-nonsecret",json.dumps(body))
                self.assertNotIn("local-fake-nonsecret",repr(response))

    def test_invalid_response_refused_without_inference_claim(self):
        class FakeResponse:
            headers={}
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self,_):return b'{"choices":[{"message":{"content":null}}]}'
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"local-fake-nonsecret"}):
            provider=NemotronObservationPlanner()
            with patch("model_observation_merge.request.urlopen",return_value=FakeResponse()):
                with self.assertRaisesRegex(ValueError,"NEBIUS_ACTION_RESPONSE_MALFORMED"):
                    provider.propose("x",[],(),1)

    def test_native_three_outcome_model_proposal_loop(self):
        upstream=os.environ.get("MATHGRAPH_PINNED_UPSTREAM")
        if not upstream:
            self.skipTest("requires independently checked out upstream")
        result=run_review(Path(upstream),ScriptedPlanner())
        states={k:v["source_native_verdict"] for k,v in result["cases"].items()}
        self.assertEqual(states,{
            "defective_green_tests":"REJECTED",
            "correct_but_initially_unknown":"WARRANTED_BOUNDED",
            "correct_but_observation_forbidden":"UNKNOWN",
        })
        for item in result["cases"].values():
            self.assertEqual(item["proposal_state"],"ACCEPTED")
            self.assertEqual(len(item["proposals"]),1)
        self.assertEqual(result["cases"]["correct_but_initially_unknown"]["merge_permission"],
                         "REVIEW_ONLY_BOUNDED")
        self.assertTrue(result["no_upstream_write"])
        self.assertTrue(result["model_cannot_approve_merge"])


if __name__=="__main__":
    unittest.main()
