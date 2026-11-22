"""Behavioral checks for the independent, finite JUnit status reference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
RUNNER = HERE / "report-status-reference.py"
CORPUS = HERE / "report-status-cases.json"


class ReportStatusReferenceTests(unittest.TestCase):
    def reference(self):
        self.assertTrue(RUNNER.is_file(), "The finite status reference is not implemented")
        spec = importlib.util.spec_from_file_location("report_status_reference", RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_reference(self, runner, output):
        return subprocess.run(
            [sys.executable, str(runner), str(output)],
            capture_output=True, text=True, timeout=10,
        )

    def test_empty_error_child_is_failed_in_rows_and_summary(self):
        observed = self.reference().observe(
            '<testsuite><testcase classname="pkg" name="setup" time="0.01">'
            '<error message="setup failed"/></testcase></testsuite>'
        )
        self.assertEqual(observed, {
            "accepted": True,
            "rows": [["pkg.setup", "FAIL", "fail", "0.01"]],
            "count": 1,
            "summary": {"total": 1, "passed": 0, "failed": 1,
                        "skipped": 0, "css": "fail"},
        })

    def test_error_with_body_is_a_failed_outcome(self):
        observed = self.reference().observe(
            '<testsuite><testcase name="teardown"><error type="RuntimeError">'
            'teardown failed</error></testcase></testsuite>'
        )
        self.assertEqual(observed["rows"], [[".teardown", "FAIL", "fail", "0"]])
        self.assertEqual(observed["summary"], {
            "total": 1, "passed": 0, "failed": 1, "skipped": 0, "css": "fail",
        })

    def test_ordinary_outcomes_preserve_order_and_attributes(self):
        observed = self.reference().observe(
            '<testsuites><testsuite><testcase classname="pkg" name="ok" time="0.1"/>'
            '<testcase name="bad"><failure/></testcase>'
            '<testcase name="later"><skipped/></testcase></testsuite></testsuites>'
        )
        self.assertEqual(observed, {
            "accepted": True,
            "rows": [["pkg.ok", "PASS", "pass", "0.1"],
                     [".bad", "FAIL", "fail", "0"],
                     [".later", "SKIP", "skip", "0"]],
            "count": 3,
            "summary": {"total": 3, "passed": 1, "failed": 1,
                        "skipped": 1, "css": "fail"},
        })

    def test_error_state_does_not_leak_into_the_next_case(self):
        observed = self.reference().observe(
            '<testsuite><testcase name="bad"><error/></testcase>'
            '<testcase name="ok"/></testsuite>'
        )
        self.assertEqual(observed["rows"], [
            [".bad", "FAIL", "fail", "0"], [".ok", "PASS", "pass", "0"],
        ])
        self.assertEqual(observed["summary"], {
            "total": 2, "passed": 1, "failed": 1, "skipped": 0, "css": "fail",
        })

    def test_text_comments_cdata_and_nested_metadata_are_not_outcomes(self):
        payloads = [
            '<system-out>&lt;error/&gt;<![CDATA[<error/>]]><!-- <error/> --></system-out>',
            '<properties><property name="metadata"><error/></property></properties>',
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                observed = self.reference().observe(
                    '<testsuite><testcase name="ok">' + payload + '</testcase></testsuite>'
                )
                self.assertEqual(observed["rows"], [[".ok", "PASS", "pass", "0"]])
                self.assertEqual(observed["summary"], {
                    "total": 1, "passed": 1, "failed": 0, "skipped": 0, "css": "pass",
                })

    def test_malformed_xml_cannot_be_reported_as_an_observation(self):
        with self.assertRaises(ET.ParseError):
            self.reference().observe('<testsuite><testcase name="bad"></testsuite>')

    def test_cli_qualifies_all_eight_cases_and_binds_actual_inputs(self):
        self.reference()
        self.assertTrue(CORPUS.is_file(), "The frozen status corpus is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reference.json"
            completed = self.run_reference(RUNNER, output)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text())
        self.assertEqual(result["runner_sha256"], hashlib.sha256(RUNNER.read_bytes()).hexdigest())
        self.assertEqual(result["corpus_sha256"], hashlib.sha256(CORPUS.read_bytes()).hexdigest())
        self.assertEqual([r["id"] for r in result["records"]], [
            "plain_pass", "assertion_failure", "skipped_case", "error_empty",
            "error_text", "error_then_pass", "mixed_outcomes", "error_text_control",
        ])
        by_id = {r["id"]: r["observed"] for r in result["records"]}
        self.assertEqual(by_id["error_empty"]["rows"], [[".bad", "FAIL", "fail", "0"]])
        self.assertEqual(by_id["mixed_outcomes"]["summary"], {
            "total": 4, "passed": 1, "failed": 2, "skipped": 1, "css": "fail",
        })

    def assert_mutation_refused(self, case_id, mutate):
        self.reference()
        self.assertTrue(CORPUS.is_file(), "The frozen status corpus is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / RUNNER.name
            shutil.copyfile(RUNNER, runner)
            cases = json.loads(CORPUS.read_text())
            mutate(next(c for c in cases if c["id"] == case_id))
            (root / CORPUS.name).write_text(json.dumps(cases))
            output = root / "reference.json"
            completed = self.run_reference(runner, output)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("REFERENCE_EXPECTATION_MISMATCH: " + case_id, completed.stderr)
            self.assertFalse(output.exists(), "A refused corpus must not produce a receipt")

    def test_cli_refuses_a_literal_expectation_that_calls_an_error_a_pass(self):
        def mutate(case):
            case["expected"]["rows"] = [[".bad", "PASS", "pass", "0"]]
            case["expected"]["summary"] = {
                "total": 1, "passed": 1, "failed": 0, "skipped": 0, "css": "pass",
            }
        self.assert_mutation_refused("error_empty", mutate)

    def test_cli_refuses_a_literal_count_that_drops_a_case(self):
        self.assert_mutation_refused(
            "mixed_outcomes", lambda case: case["expected"].update(count=3),
        )

    def test_cli_refuses_an_input_change_that_removes_the_error(self):
        self.assert_mutation_refused(
            "error_empty", lambda case: case.update(
                input='<testsuite><testcase name="bad"><system-out>&lt;error/&gt;'
                      '</system-out></testcase></testsuite>'
            ),
        )


if __name__ == "__main__":
    unittest.main()
