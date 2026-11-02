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
    def test_zero_test_rejected(self):
        src='package zerolog\nimport "testing"\nfunc TestAnother(t *testing.T){ t.Fatal("x") }\n'
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"candidate.go";path.write_text(src)
            p=subprocess.run(["go","run",str(BASE/"validate.go"),"--",str(path)],capture_output=True,text=True,timeout=45)
            self.assertEqual(json.loads(p.stdout)["status"],"UNKNOWN_UNTRUSTED_GO_TEST")

if __name__=="__main__":unittest.main()
