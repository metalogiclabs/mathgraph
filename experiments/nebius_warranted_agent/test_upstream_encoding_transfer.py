"""Offline unit controls for the exact-source upstream-transfer harness."""
import base64
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from upstream_encoding_transfer import (
    ENCODING_BLOB, TEST_BLOB, EXPANDED_COMMAND, NATIVE_COMMAND, EXPRESSION,
    MUTANTS, Receipt, acquired_tests, digest, domain, independent_minimum_bound,
    minimum_separator, mutate, oracle, process_env, qualify, snapshot,
)

def synthetic_observations(inputs):
    return {
        "reference": [oracle(x) for x in inputs],
        "standard_alphabet": [base64.b64encode(x).rstrip(b"=") for x in inputs],
        "unstripped_padding": [base64.urlsafe_b64encode(x) for x in inputs],
        "trailing_zero_loss": [
            oracle(x.rstrip(b"\x00") if len(x) % 3 == 0 else x)
            for x in inputs
        ],
    }

class UpstreamTransferTests(unittest.TestCase):
    def test_frozen_domain_and_oracle(self):
        values=domain()
        self.assertEqual(len(values),len(set(values)))
        self.assertIn(b"\xfb",values)
        self.assertIn(b"\x00\x00\x00",values)
        self.assertEqual(oracle(b"\xfb"),b"-w")
        self.assertEqual(oracle(b"abc"),b"YWJj")

    def test_independent_selector_minimum(self):
        values=domain()
        observations=synthetic_observations(values)
        basis=minimum_separator(values, observations)
        self.assertEqual(basis["status"],"MINIMUM_BASIS")
        self.assertEqual(len(basis["tests_hex"]),2)
        self.assertEqual(basis["total_synthetic_cost"],6)
        self.assertEqual(independent_minimum_bound(basis["cover_records"]),6)
        selected=[bytes.fromhex(value) for value in basis["tests_hex"]]
        for mutant in ("standard_alphabet","unstripped_padding","trailing_zero_loss"):
            self.assertTrue(any(observations[mutant][values.index(x)] != oracle(x)
                                for x in selected))

    def test_obstruction_without_permitted_test(self):
        inputs=(b"abc",)
        result=minimum_separator(inputs,synthetic_observations(inputs))
        self.assertEqual(result["status"],"OBSTRUCTION")
        self.assertCountEqual(result["unsplittable"],
                              ("standard_alphabet","unstripped_padding","trailing_zero_loss"))

    def test_exact_upstream_mutation_guard(self):
        source="def base64_encode(string):\n    " + EXPRESSION + "\n"
        for name,replacement in MUTANTS.items():
            with self.subTest(name=name):
                changed=mutate(source.encode(),name).decode()
                self.assertEqual(changed.count(replacement),1)
                self.assertEqual(changed.count(EXPRESSION),0)
        with self.assertRaises(ValueError):
            mutate(b"wrong bytes", "standard_alphabet")
        with self.assertRaises(ValueError):
            mutate(source.encode(), "unknown")

    def test_generated_tests_expected_values(self):
        source=acquired_tests((b"\xfb",b"\x00\x00\x00")).decode()
        self.assertIn("bytes.fromhex('fb')",source)
        self.assertIn("bytes.fromhex('2d77')",source)
        self.assertIn("bytes.fromhex('000000')",source)
        self.assertIn("bytes.fromhex('41414141')",source)
        self.assertNotIn("eval(",source)

    def test_snapshot_binding_changes_with_source_and_tests(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"src"/"itsdangerous").mkdir(parents=True)
            (root/"src"/"itsdangerous"/"encoding.py").write_text("source")
            (root/"test_encoding.py").write_text("tests")
            before=snapshot(root)
            receipt=Receipt("672971d66a2ef9f85151e53283113f33d642dabd",
                digest(b"original"),before,before,NATIVE_COMMAND,0,digest(b"pass"),
                "finished","2026-10-26")
            self.assertEqual(qualify(root,receipt,digest(b"original"),NATIVE_COMMAND)[0],"WARRANTED")
            self.assertEqual(qualify(root,None,digest(b"original"),NATIVE_COMMAND)[0],"UNKNOWN")
            self.assertEqual(qualify(root,receipt,digest(b"foreign"),NATIVE_COMMAND)[0],"REJECTED")
            self.assertEqual(qualify(root,replace(receipt,command=("echo","ok")),
                                      digest(b"original"),NATIVE_COMMAND)[0],"REJECTED")
            (root/"test_mathgraph_acquired.py").write_text("new test")
            self.assertEqual(qualify(root,receipt,digest(b"original"),NATIVE_COMMAND)[0],"REJECTED")
            self.assertNotEqual(snapshot(root),before)

    def test_no_secret_propagation(self):
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ",{"NEBIUS_API_KEY":"DO_NOT_LEAK","SOME_SECRET":"DO_NOT_LEAK"}):
                env=process_env(Path(tmp))
                self.assertNotIn("NEBIUS_API_KEY",env)
                self.assertNotIn("SOME_SECRET",env)

    def test_upstream_blob_pins_are_full_sha1(self):
        self.assertEqual(len(ENCODING_BLOB),40)
        self.assertEqual(len(TEST_BLOB),40)

if __name__ == "__main__":
    unittest.main()
