import json
import subprocess
import tempfile
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parent


def checked(src):
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"candidate_test.go"
        path.write_text(src)
        p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=30)
        # go run -- creates an executable argument "--"; use go build for actual test to avoid ambiguity
        return p


class LexicalAdmitTests(unittest.TestCase):
    def test_candidate_gate(self):
        # Run `go run validate.go path` because `go run --` args are not forwarded
        src='package zerolog\nimport "testing"\nfunc TestMathGraphProposedWitness(t *testing.T){ if 1!=1 { t.Fatal("x") } }\n'
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(src)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=45)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"],"ADMITTED_TEST_ONLY_CANDIDATE")
    def test_side_effect_import_rejected(self):
        src='package zerolog\nimport ("testing";"os/exec")\nfunc TestMathGraphProposedWitness(t *testing.T){ t.Fatal("x") }\n'
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(src)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["reason"],"unsafe_import")
    def test_bounded_go_helper_type_and_method_admitted(self):
        src = ("package zerolog\nimport \"testing\"\n"
               "type observation struct { seen []string }\n"
               "func (h *observation) Run(x string) { h.seen = append(h.seen, x) }\n"
               "func TestMathGraphProposedWitness(t *testing.T){ if 2 != 2 { t.Fatal(\"wrong\") } }\n")
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(src)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["status"],"ADMITTED_TEST_ONLY_CANDIDATE")
    def test_global_state_declaration_remains_rejected(self):
        src = ("package zerolog\nimport \"testing\"\n"
               "var injectedState = true\n"
               "func TestMathGraphProposedWitness(t *testing.T){ t.Fatal(\"x\") }\n")
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(src)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["status"],"UNKNOWN_UNTRUSTED_GO_TEST")
    def test_zero_test_rejected(self):
        src='package zerolog\nimport "testing"\nfunc TestAnother(t *testing.T){ t.Fatal("x") }\n'
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(src)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["status"],"UNKNOWN_UNTRUSTED_GO_TEST")


    def test_generic_package_with_bounded_time_and_sync_admitted(self):
        source = ('package backoff\nimport ("testing";"time";"sync")\n'
                  'func TestMathGraphProposedWitness(t *testing.T){var m sync.Mutex;m.Lock();m.Unlock(); if time.Second<0{t.Fatal("bad")}}\n')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(source)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--","backoff",str(path)],
                             capture_output=True,text=True,timeout=45)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"],"ADMITTED_TEST_ONLY_CANDIDATE")

    def test_wrong_package_is_rejected(self):
        source = ('package backoff\nimport "testing"\n'
                  'func TestMathGraphProposedWitness(t *testing.T){t.Fatal("unreachable")}\n')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(source)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--","zerolog",str(path)],
                             capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["reason"],"wrong_package")

    def test_invalid_expected_package_is_rejected(self):
        source = ('package backoff\nimport "testing"\n'
                  'func TestMathGraphProposedWitness(t *testing.T){t.Fatal("unreachable")}\n')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(source)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--","backoff-not-a-package",str(path)],
                             capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["reason"],"invalid_package")

if __name__=="__main__":unittest.main()
