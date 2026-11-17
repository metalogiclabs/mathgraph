"""Authentic C2PO and R2U2 C monitor: no mocks, exact source pins."""

import os
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.fret_authority_pair_v0.authority import (
    check_signal_binding,
    choose_requirement,
)
from research.fret_authority_pair_v0.witness import find_future_distinction


PIN = "2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a"
SIG1_PIN = "9d58a88f30216d8ebbbfc70828974f11ecd1ebeb"
HERE = Path(__file__).resolve().parent


class AuthenticNativePair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = os.environ.get("R2U2_SOURCE")
        if not directory:
            raise unittest.SkipTest("Set R2U2_SOURCE for native qualification")
        cls.source = Path(directory).resolve()
        cls.compiler = cls.source / "compiler/c2po.py"
        cls.monitor = cls.source / "monitors/c/build/r2u2"
        actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cls.source,
                                capture_output=True, text=True, check=True).stdout.strip()
        if actual != PIN:
            raise AssertionError(f"Wrong source pin: {actual} != {PIN}")
        if not cls.monitor.is_file():
            raise AssertionError("Build the native C monitor first: make -C monitors/c")

    def compile(self, folder, spec, header):
        image = Path(folder) / "spec.bin"
        result = subprocess.run([
            sys.executable, str(self.compiler), "--spec", str(HERE / spec),
            "--trace", str(HERE / header), "--output", str(image), "--quiet",
        ], cwd=self.source, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return image

    def replay(self, image, trace):
        run = subprocess.run([str(self.monitor), str(image), str(HERE / trace)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run.stdout.splitlines()

    def test_source_declared_identity_vs_positional_native_monitor(self):
        with tempfile.TemporaryDirectory() as folder:
            image = self.compile(folder, "case_a.c2po", "case_a_matched.csv")
            correct = self.replay(image, "case_a_matched.csv")
            swapped = self.replay(image, "case_a_swapped.csv")
        self.assertEqual(correct, ["0:0,T", "0:1,F"])
        self.assertEqual(swapped, ["0:0,F", "0:1,F"])
        # Bind the pilot policy to actual spec bytes and compiled signal order.
        contract_bytes = ((HERE / "case_a.c2po").read_bytes() + b"\0" +
                          (HERE / "case_a_matched.csv").read_bytes().splitlines()[0])
        source_digest = hashlib.sha256(contract_bytes).hexdigest()
        self.assertEqual(check_signal_binding(
            ("BOOST", "COAST"), ("COAST", "BOOST"), source_digest,
            source_digest, strict_policy_active=True).status, "REFUSE")

    def test_temporal_counterexample_does_not_select_engineer_intent(self):
        witness = find_future_distinction((0, 7), (2, 7), horizon=8,
                                          trigger="BOOST", response="COAST")
        self.assertIsNotNone(witness)
        recorded = (HERE / "case_b_witness.csv").read_text().splitlines()
        self.assertEqual(tuple(int(line.split(",")[1]) for line in recorded[1:]),
                         witness.response_trace)
        with tempfile.TemporaryDirectory() as folder:
            image = self.compile(folder, "case_b.c2po", "case_b_witness.csv")
            output = self.replay(image, "case_b_witness.csv")
        native = {}
        for line in output:
            formula, rest = line.split(":", 1)
            timestamp, verdict = rest.split(",", 1)
            if timestamp == "0":
                native["IMMEDIATE" if formula == "0" else "DELAYED"] = verdict == "T"
        # Hand-derived independent bounded-time oracle, not a C2PO transcription.
        trigger = [1] + [0] * 7
        response = list(witness.response_trace)
        oracle = {"IMMEDIATE": (not trigger[0]) or any(response[0:8]),
                  "DELAYED": (not trigger[0]) or any(response[2:8])}
        self.assertEqual(native, {"IMMEDIATE": True, "DELAYED": False})
        self.assertEqual(oracle, native)
        contract_bytes = ((HERE / "case_b.c2po").read_bytes() + b"\0" +
                          (HERE / "case_b_witness.csv").read_bytes().splitlines()[0])
        source_digest = hashlib.sha256(contract_bytes).hexdigest()
        choice = choose_requirement(native, oracle, source_digest, source_digest,
                                    owner_choices=(),
                                    question=witness.question)
        self.assertEqual((choice.status, choice.scope),
                         ("ABSTAIN", "requirement_selection"))
        self.assertIn("offset 0", choice.question)


class ExistingSIG1NativeBoundary(unittest.TestCase):
    """Check the already-existing SIG1 fork rather than reimplement its parser."""

    @classmethod
    def setUpClass(cls):
        directory = os.environ.get("R2U2_SIG1_SOURCE")
        if not directory:
            raise unittest.SkipTest("Set R2U2_SIG1_SOURCE for SIG1 native qualification")
        cls.source = Path(directory).resolve()
        cls.monitor = cls.source / "monitors/c/build/r2u2_debug"
        cls.compiler = cls.source / "compiler/c2po.py"
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cls.source,
                                capture_output=True, text=True, check=True).stdout.strip()
        if commit != SIG1_PIN:
            raise AssertionError(f"Wrong SIG1 source pin: {commit} != {SIG1_PIN}")
        if not cls.monitor.is_file():
            raise AssertionError("Build SIG1 debug monitor: make -C monitors/c debug")

    def compiled(self, tmp, trace, protected=True):
        image = Path(tmp) / "check.bin"
        command = [sys.executable, str(self.compiler), "--spec", str(HERE / "case_a.c2po"),
                   "--trace", str(HERE / trace), "--output", str(image), "--quiet"]
        if protected:
            command.append("--input-contract")
        result = subprocess.run(command, cwd=self.source,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return image

    def run_sig1(self, image, trace):
        return subprocess.run([str(self.monitor), str(image), str(HERE / trace)],
                              capture_output=True, text=True,
                              env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0:halt_on_error=1"})

    def test_compiled_named_contract_rejects_swapped_header_without_verdict(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = self.compiled(folder, "case_a_matched.csv")
            matched = self.run_sig1(binary, "case_a_matched.csv")
            swapped = self.run_sig1(binary, "case_a_swapped.csv")
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertEqual(matched.stdout.splitlines(), ["0:0,T", "0:1,F"])
        self.assertNotEqual(swapped.returncode, 0)
        self.assertIn("Invalid CSV", swapped.stderr)
        self.assertEqual(swapped.stdout.strip(), "")

    def test_compiling_against_swapped_header_restores_named_verdict(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = self.compiled(folder, "case_a_swapped.csv")
            run = self.run_sig1(binary, "case_a_swapped.csv")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(), ["0:0,T", "0:1,F"])

    def test_legacy_binary_retains_positional_behavior(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = self.compiled(folder, "case_a_matched.csv", protected=False)
            run = self.run_sig1(binary, "case_a_swapped.csv")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(), ["0:0,F", "0:1,F"])


if __name__ == "__main__":
    unittest.main()
