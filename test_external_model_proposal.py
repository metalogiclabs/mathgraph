import json
import unittest
from unittest.mock import patch

from external_model_proposal import ExternalNemotronProposal, ExternalTask


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
        self.headers = {"x-request-id": "fixture-request"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.payload[:limit]


class ExternalProposalTests(unittest.TestCase):
    def setUp(self):
        self.task = ExternalTask(
            task_id="django__django-13512",
            source_repo="django/django",
            source_commit="b79088306513d5ed76d31ac40ab3c15f858946ea",
            source_file="django/forms/fields.py",
            source_file_sha256="7e2675d83e075f0ccb252abfefc13efe853c5ac9ed4c36c9581c8f5c15db4dcf",
            issue="Unicode JSON escapes are displayed in admin.",
            function_excerpt="def prepare_value(self, value):\n    return json.dumps(value, cls=self.encoder)",
        )

    def test_missing_key_and_wrong_model_fail_before_network(self):
        with self.assertRaisesRegex(RuntimeError, "NEBIUS_API_KEY_NOT_CONFIGURED"):
            ExternalNemotronProposal(api_key="")
        with self.assertRaisesRegex(ValueError, "NVIDIA_OPEN_MODEL_REQUIRED"):
            ExternalNemotronProposal(api_key="fixture", model="other/model")

    def test_proposal_is_untrusted_source_not_execution_authority(self):
        payload = {"model": "nvidia/nemotron-3-super-120b-a12b", "choices": [{
            "finish_reason": "stop", "message": {"content": json.dumps({
                "function_source": "def prepare_value(self, value):\n    return json.dumps(value, cls=self.encoder, ensure_ascii=False)"
            })}}]}
        observed = {}
        def fake_open(req, timeout):
            observed["payload"] = json.loads(req.data)
            return FakeResponse(payload)
        with patch("external_model_proposal.request.urlopen", side_effect=fake_open):
            result = ExternalNemotronProposal(api_key="fixture-secret").propose(self.task)
        self.assertEqual(result.status, "UNVERIFIED_PROPOSAL")
        self.assertEqual(result.task_id, self.task.task_id)
        self.assertIn("ensure_ascii=False", result.function_source)
        self.assertEqual(result.request_id, "fixture-request")
        self.assertEqual(observed["payload"]["model"], "nvidia/nemotron-3-super-120b-a12b")
        self.assertNotIn("fixture-secret", json.dumps(observed["payload"]))

    def test_rejects_model_identity_mismatch_and_schema_inflation(self):
        for response in [
            {"model": "different/model", "choices": [{"message": {"content": '{"function_source":"pass"}'}}]},
            {"choices": [{"message": {"content": '{"function_source":"pass","approve":true}'}}]},
        ]:
            with self.subTest(response=response):
                with patch("external_model_proposal.request.urlopen", return_value=FakeResponse(response)):
                    with self.assertRaises(ValueError):
                        ExternalNemotronProposal(api_key="fixture").propose(self.task)

    def test_prompt_source_size_is_bounded(self):
        too_large = ExternalTask(**{**self.task.__dict__, "issue": "a" * 20000})
        with self.assertRaisesRegex(ValueError, "TASK_INPUT_TOO_LARGE"):
            ExternalNemotronProposal(api_key="fixture").propose(too_large)


if __name__ == "__main__":
    unittest.main()
