"""Security and finite-lineage controls for the optional Nebius repair adapter."""
import unittest
from upstream_guarded_agent import (
    ScriptedRepair, isolated_patch, validate_replacement,
    MODEL_DEFAULT, ENDPOINT,
)

SOURCE = '''import base64
def base64_encode(string):
    string = want_bytes(string)
    return base64.b64encode(string).rstrip(b"=")

def base64_decode(string):
    return base64.urlsafe_b64decode(string)
'''

class GuardedAgentTests(unittest.TestCase):
    def test_allowed_semantically_correct_repairs(self):
        for candidate in [
            'return base64.urlsafe_b64encode(string).rstrip(b"=")',
            'return base64.b64encode(string).replace(b"+", b"-").replace(b"/", b"_").rstrip(b"=")',
            'return base64.urlsafe_b64encode(string)',
        ]:
            with self.subTest(candidate=candidate):
                validate_replacement(candidate)

    def test_disallow_side_effects_and_code_escape(self):
        for candidate in [
            "import os",
            "return __import__('os').system('echo unsafe')",
            "return open('/tmp/unsafe')",
            "return base64.urlsafe_b64encode(string); exec('x')",
            "return base64.urlsafe_b64encode(string)\nimport os",
            "return base64.urlsafe_b64encode(string).decode()",
            "return base64.urlsafe_b64encode(string).replace(b'/', b'hello')",
            "return base64.urlsafe_b64encode(string).rstrip(b'ABC')",
            "return base64.urlsafe_b64encode(string * 100000)",
            "return base64.urlsafe_b64encode(string).__class__",
            "return str(base64.urlsafe_b64encode(string))",
            "return base64.urlsafe_b64encode(string) if True else b'x'",
        ]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_replacement(candidate)

    def test_patch_only_return_expression(self):
        correct='return base64.urlsafe_b64encode(string).rstrip(b"=")'
        result=isolated_patch(SOURCE.encode(),correct).decode()
        self.assertIn("    "+correct,result)
        self.assertIn("def base64_decode(string):\n    return base64.urlsafe_b64decode(string)",result)
        self.assertEqual(result.count("return base64.urlsafe_b64encode(string).rstrip"),1)
        self.assertNotEqual(result,SOURCE)
        self.assertEqual(isolated_patch(result.encode(),correct),result.encode())

    def test_refuse_missing_or_ambiguous_source_block(self):
        with self.assertRaises(ValueError):
            isolated_patch(b"def unrelated(): pass\n",
                'return base64.urlsafe_b64encode(string).rstrip(b"=")')
        ambiguous=(SOURCE.replace("def base64_decode(string):",
            "    return base64.b64encode(string)\n\ndef base64_decode(string):"))
        with self.assertRaises(ValueError):
            isolated_patch(ambiguous.encode(),
                'return base64.urlsafe_b64encode(string).rstrip(b"=")')

    def test_scripted_provenance_and_failure_first(self):
        provider=ScriptedRepair()
        wrong=provider.propose(SOURCE,[],1)
        right=provider.propose(SOURCE,[],2)
        self.assertEqual(wrong.provider,"SCRIPTED_NOT_NEBIUS")
        self.assertEqual(wrong.model,"none")
        self.assertNotEqual(wrong.replacement_return,right.replacement_return)
        validate_replacement(right.replacement_return)

    def test_nebius_endpoint_never_local_stub(self):
        self.assertEqual(ENDPOINT,"https://api.tokenfactory.nebius.com/v1/chat/completions")
        self.assertTrue(MODEL_DEFAULT.startswith("nvidia/"))

if __name__ == "__main__":
    unittest.main()
