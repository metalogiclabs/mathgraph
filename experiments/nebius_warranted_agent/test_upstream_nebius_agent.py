"""Independent controls for the pinned real-project Nemotron repair adapter.

Only the explicitly scripted provider runs in CI. Mock HTTP never authenticates
to Nebius; no network result is represented as genuine model evidence.
"""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from upstream_nebius_agent import (
    DEFAULT_MODEL, ENDPOINT, NebiusProvider, ORIGINAL_FUNCTION,
    Proposal, ScriptedProvider, WRONG_FIRST, only_function,
    replace_function, validate_function, perform,
)
from upstream_encoding_transfer import (
    ENCODING_PATH, UPSTREAM_COMMIT, mutate, pinned_source
)

class ContractTests(unittest.TestCase):
    def test_valid_repair_and_wrong_first_are_admitted(self):
        validate_function(ORIGINAL_FUNCTION)
        validate_function(WRONG_FIRST)

    def test_forbid_arbitrary_imports_and_effects(self):
        trials = [
            "import os\n" + ORIGINAL_FUNCTION,
            'def base64_encode(string):\n    string = want_bytes(string)\n    return __import__("os").getenv("TOKEN")\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    return open("/etc/passwd").read()\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    return base64.urlsafe_b64encode(string).decode()\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    return base64.urlsafe_b64encode(string).rstrip(b"BAD")\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    exec("bad")\n    return base64.urlsafe_b64encode(string)\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    return (lambda: string)()\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    return base64.urlsafe_b64encode(string + b"secret")\n',
            'def base64_encode(string):\n    string = want_bytes(string)\n    return base64.urlsafe_b64encode(string).rstrip(b"=") if True else b""\n',
            'def base64_encode(string, extras=None):\n    string = want_bytes(string)\n    return base64.urlsafe_b64encode(string)\n',
        ]
        for code in trials:
            with self.subTest(code=code), self.assertRaises(ValueError):
                validate_function(code)

    def test_no_unbounded_model_payload(self):
        with self.assertRaises(ValueError):
            validate_function(ORIGINAL_FUNCTION + " " * 16000)

    def test_replace_only_target_function_without_touching_neighbors(self):
        code = (b"import base64\n\n" +
                ORIGINAL_FUNCTION.encode() +
                b"\ndef after():\n    return 99\n")
        output = replace_function(code, WRONG_FIRST)
        self.assertIn(b"def after():\n    return 99\n", output)
        self.assertIn(b"return base64.urlsafe_b64encode(string)\n", output)
        self.assertNotIn(b'.rstrip(b"=")', output)
        self.assertEqual(only_function(output).strip(), WRONG_FIRST.strip())

    def test_missing_api_key_fails_before_any_model_claim(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "NEBIUS_API_KEY"):
                NebiusProvider(DEFAULT_MODEL)

    def test_nvidia_model_required(self):
        with patch.dict(os.environ, {"NEBIUS_API_KEY":"unused"}):
            with self.assertRaisesRegex(ValueError, "NVIDIA"):
                NebiusProvider("some-other-provider/model")

    def test_mock_http_response_not_authentic_evidence(self):
        class FakeResponse:
            headers = {"x-request-id":"mock-id"}
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def read(self,_): return json.dumps({
                "model":DEFAULT_MODEL,
                "choices":[{"message":{"content":json.dumps(
                    {"function_source":ORIGINAL_FUNCTION})}}]}).encode()
        with patch.dict(os.environ, {"NEBIUS_API_KEY":"test-not-a-secret"}):
            p=NebiusProvider(DEFAULT_MODEL)
            with patch("upstream_nebius_agent.request.urlopen", return_value=FakeResponse()) as open_request:
                result=p.propose("buggy", [("f8","-A")],1)
                self.assertEqual(result.source, ORIGINAL_FUNCTION)
                self.assertEqual(result.request_id,"mock-id")
                self.assertEqual(result.provider,"nebius-token-factory")
                self.assertEqual(open_request.call_args.kwargs["timeout"],60)
                request_body=json.loads(open_request.call_args.args[0].data)
                self.assertEqual(request_body["model"],DEFAULT_MODEL)
                self.assertEqual(request_body["chat_template_kwargs"],
                                 {"enable_thinking":False})
                self.assertEqual(request_body["max_tokens"],2048)
            self.assertNotIn("test-not-a-secret",repr(result))

    def test_null_text_diagnostic_is_safe_and_fail_closed(self):
        class FakeResponse:
            headers = {"x-request-id":"mock-empty"}
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def read(self,_):
                return json.dumps({
                    "model":DEFAULT_MODEL,
                    "choices":[{"finish_reason":"length",
                        "message":{"content":None,"reasoning_content":"private thought"}}]
                }).encode()
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"test-not-a-secret"}):
            provider=NebiusProvider(DEFAULT_MODEL)
            with patch("upstream_nebius_agent.request.urlopen",return_value=FakeResponse()):
                with self.assertRaisesRegex(ValueError,
                    "NEBIUS_RESPONSE_NOT_TEXT:finish=length:reasoning_present=1") as err:
                    provider.propose("buggy",[],1)
                self.assertNotIn("private thought",str(err.exception))
                self.assertNotIn("test-not-a-secret",str(err.exception))

class SourceNativeTests(unittest.TestCase):
    def setUp(self):
        checkout=os.environ.get("MATHGRAPH_PINNED_UPSTREAM")
        if not checkout:
            self.skipTest("source-native test requires pinned external checkout")
        self.checkout=Path(checkout)
        pinned_source(self.checkout)

    def test_scripted_real_upstream_repair_is_evidence_scoped(self):
        report=perform(self.checkout,ScriptedProvider(),max_attempts=3)
        self.assertEqual(report["source"]["commit"],UPSTREAM_COMMIT)
        self.assertFalse(report["source"]["upstream_bug_claim"])
        self.assertEqual(report["provider"],"ScriptedProvider")
        self.assertEqual(report["fixed_suite_baseline"],"WARRANTED")
        self.assertEqual(report["evidence_seeking_detection"],"REJECTED")
        self.assertEqual(report["final_state"],"WARRANTED")
        attempts=[e for e in report["events"] if "attempt" in e]
        self.assertEqual([e["state"] for e in attempts],["REJECTED","WARRANTED"])
        self.assertTrue(all(e["provider"]=="SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS"
                            for e in attempts))
        self.assertEqual(report["frozen_experiment"]["tests_hex"],["00","f80000"])
        self.assertEqual(report["frozen_experiment"]["minimum_synthetic_cost"],6)
        self.assertEqual([e["state"] for e in report["events"][-2:]],
                         ["REJECTED","WARRANTED"])

    def test_one_attempt_cannot_falsely_warrant(self):
        report=perform(self.checkout,ScriptedProvider(),max_attempts=1)
        self.assertEqual(report["final_state"],"REJECTED")
        self.assertEqual(report["events"][-1]["state"],"REJECTED")

if __name__=="__main__":
    unittest.main()
