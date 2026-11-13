"""Independent local tests of typed action compiler and inference contract."""
from __future__ import annotations
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from typed_action_agent import (
    ACTION_SCHEMA, ENCODERS, PADDING, NebiusTypedProvider,
    ScriptedTypedProvider, compile_typed_action,
)
from upstream_nebius_agent import DEFAULT_MODEL, validate_function, perform
from upstream_encoding_transfer import pinned_source, UPSTREAM_COMMIT


class FakeResponse:
    def __init__(self, result):
        self.data=json.dumps(result).encode()
        self.headers={"x-request-id":"mock-typed-call"}
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size): return self.data[:size]


def response(action, finish="stop", model=DEFAULT_MODEL):
    return {
        "model":model,
        "id":"mock-completion",
        "choices":[{"finish_reason":finish,
            "message":{"role":"assistant","content":json.dumps(action)}}]
    }


class TypedCompilerTests(unittest.TestCase):
    def test_all_four_finite_actions_have_safe_ast(self):
        for encoder in ENCODERS:
            for padding in PADDING:
                with self.subTest(encoder=encoder,padding=padding):
                    source=compile_typed_action({"encoder":encoder,"padding":padding})
                    self.assertEqual(source.count("def base64_encode"),1)
                    self.assertIn("want_bytes(string)",source)
                    validate_function(source)
                    self.assertNotIn("__import__",source)

    def test_reject_arbitrary_code_and_outside_grammar(self):
        attacks=[
            None, "python code",
            {"encoder":"__import__('os')","padding":"retain"},
            {"encoder":"urlsafe_b64encode","padding":"strip","code":"exec('bad')"},
            {"encoder":"urlsafe_b64encode","padding":"rm -rf /"},
            {"encoder":"urlsafe_b64encode"},
            {"encoder":1,"padding":"strip"},
        ]
        for attack in attacks:
            with self.subTest(attack=attack), self.assertRaises(ValueError):
                compile_typed_action(attack)

    def test_two_field_json_schema(self):
        self.assertEqual(set(ACTION_SCHEMA["properties"]),{"encoder","padding"})
        self.assertEqual(ACTION_SCHEMA["additionalProperties"],False)

    def test_scripted_provider_explicit_provenance(self):
        provider=ScriptedTypedProvider()
        first=provider.propose("defect",[],1)
        second=provider.propose("defect",[],2)
        self.assertIn("SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS",first.provider)
        self.assertNotEqual(first.source,second.source)
        self.assertEqual(provider.actions[1]["action"]["encoder"],"urlsafe_b64encode")
        self.assertEqual(provider.actions[1]["action"]["padding"],"strip")

    def test_nebius_key_absent_fails(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,"NEBIUS_API_KEY_NOT_CONFIGURED"):
                NebiusTypedProvider()

    def test_nebius_nvidia_requirement(self):
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"fixture-key"}):
            with self.assertRaisesRegex(ValueError,"NVIDIA_OPEN_MODEL_REQUIRED"):
                NebiusTypedProvider(model="some-other-model")

    def test_valid_mock_inference_returns_compiled_patch(self):
        action={"encoder":"urlsafe_b64encode","padding":"strip"}
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"mock-not-secret"}):
            provider=NebiusTypedProvider()
            with patch("typed_action_agent.request.urlopen",
                       return_value=FakeResponse(response(action))) as transport:
                proposal=provider.propose("buggy", [("00","AA"),("f80000","-AAA")],1)
                self.assertIn('urlsafe_b64encode(string).rstrip(b"=")',proposal.source)
                self.assertEqual(proposal.provider,"nebius-token-factory")
                self.assertEqual(proposal.request_id,"mock-typed-call")
                sent=json.loads(transport.call_args.args[0].data)
                self.assertEqual(sent["guided_json"],ACTION_SCHEMA)
                self.assertEqual(sent["response_format"],{"type":"json_object"})
                self.assertEqual(sent["chat_template_kwargs"]["enable_thinking"],False)
                self.assertLessEqual(sent["max_tokens"],512)
                self.assertNotIn("mock-not-secret",json.dumps(sent))
                self.assertEqual(provider.actions[0]["compiler_output_sha256"],
                                 __import__("hashlib").sha256(proposal.source.encode()).hexdigest())

    def test_model_output_is_always_untrusted(self):
        cases=[
            response({"encoder":"open","padding":"strip"}),
            response({"encoder":"urlsafe_b64encode","padding":"strip","shell":"rm"}),
            response({"encoder":"urlsafe_b64encode","padding":"strip"},finish="length"),
            response({"encoder":"urlsafe_b64encode","padding":"strip"},model="other"),
            {"choices":[{"message":{"content":None},"finish_reason":"stop"}]},
            {"choices":[{"message":{"content":"<code>"}}]},
        ]
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"mock-not-secret"}):
            for case in cases:
                with self.subTest(case=case), patch(
                        "typed_action_agent.request.urlopen",
                        return_value=FakeResponse(case)):
                    provider=NebiusTypedProvider()
                    with self.assertRaises(ValueError):
                        provider.propose("buggy", [], 1)
                    self.assertFalse(provider.actions)

    def test_provider_never_logs_exception_body_or_key(self):
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"mock-not-secret"}):
            provider=NebiusTypedProvider()
            with patch("typed_action_agent.request.urlopen",
                       side_effect=RuntimeError("mock-not-secret private request")):
                with self.assertRaisesRegex(RuntimeError,"NEBIUS_INFERENCE_UNVERIFIED") as error:
                    provider.propose("buggy",[],1)
                self.assertNotIn("mock-not-secret",str(error.exception))

    def test_bounded_to_two_attempts(self):
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"mock-not-secret"}):
            provider=NebiusTypedProvider()
            with self.assertRaisesRegex(ValueError,"OUT_OF_BUDGET"):
                provider.propose("buggy",[],3)


class PinnedNativeTypedTests(unittest.TestCase):
    def setUp(self):
        checkout=os.environ.get("MATHGRAPH_PINNED_UPSTREAM")
        if not checkout:
            self.skipTest("Requires exact external Pallets checkout")
        self.checkout=Path(checkout)
        pinned_source(self.checkout)

    def test_scripted_finite_choice_restores_evidence(self):
        provider=ScriptedTypedProvider()
        report=perform(self.checkout,provider,max_attempts=2)
        self.assertEqual(report["source"]["commit"],UPSTREAM_COMMIT)
        self.assertEqual(report["fixed_suite_baseline"],"WARRANTED")
        self.assertEqual(report["evidence_seeking_detection"],"REJECTED")
        self.assertEqual(report["final_state"],"WARRANTED")
        attempts=[e for e in report["events"] if e["step"]=="model_repair_attempt"]
        self.assertEqual([x["state"] for x in attempts],["REJECTED","WARRANTED"])
        self.assertEqual(len(provider.actions),2)
        self.assertTrue(all(x.get("request_id") is None for x in attempts))

    def test_single_wrong_typed_action_cannot_warrant(self):
        report=perform(self.checkout,ScriptedTypedProvider(),max_attempts=1)
        self.assertEqual(report["final_state"],"REJECTED")


if __name__=="__main__":
    unittest.main()
