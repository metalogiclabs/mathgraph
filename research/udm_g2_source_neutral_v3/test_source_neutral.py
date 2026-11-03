"""Source-neutral Go test admission: bounded syntax and fail-closed native counting."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from evaluate import test_summary

HERE=Path(__file__).resolve().parent

def check(code, package="g2_fixture"):
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"witness.go"
        p.write_text(code)
        run=subprocess.run(["go","run",str(HERE/"validate.go"),"--",str(p),package],
            cwd=HERE,capture_output=True,text=True,timeout=45)
        assert run.returncode==0,run.stderr
        return json.loads(run.stdout)

GOOD='package g2_fixture\nimport "testing"\nfunc TestMathGraphProposedWitness(t *testing.T) { t.Fatal("falsifiable") }\n'
class SourceNeutralTests(unittest.TestCase):
    def test_unseen_package_can_be_admitted(self):
        self.assertEqual(check(GOOD)["status"],"ADMITTED_TEST_ONLY_CANDIDATE")
    def test_wrong_package_fails_closed(self):
        self.assertEqual(check(GOOD,"zerolog")["reason"],"wrong_package")
    def test_side_effect_import_is_rejected(self):
        src='package g2_fixture\nimport (_ "fmt"; "testing")\nfunc TestMathGraphProposedWitness(t *testing.T) { t.Fatal("fail") }\n'
        self.assertEqual(check(src)["reason"],"side_effect_import")
    def test_reflect_deep_equal_in_memory_is_allowed(self):
        src=('package g2_fixture\nimport ("testing";"reflect")\n'
             'func TestMathGraphProposedWitness(t *testing.T) { if !reflect.DeepEqual([]int{1},[]int{1}) { t.Fatal("different") } }\n')
        self.assertEqual(check(src)["status"],"ADMITTED_TEST_ONLY_CANDIDATE")

    def test_external_process_import_stays_refused(self):
        src=('package g2_fixture\nimport ("testing";"os/exec")\n'
             'func TestMathGraphProposedWitness(t *testing.T) { t.Fatal("candidate") }\n')
        self.assertEqual(check(src)["reason"],"unsafe_import")

    def test_no_assertion_is_rejected(self):
        src='package g2_fixture\nimport "testing"\nfunc TestMathGraphProposedWitness(t *testing.T) { _ = t }\n'
        self.assertEqual(check(src)["reason"],"no_falsifiable_assertion")
    def test_zero_recognized_is_unknown(self):
        self.assertEqual(test_summary('{"Action":"pass","Package":"pkg"}',0)["status"],"UNKNOWN_ZERO_NAMED_TESTS")
    def test_one_failing_named_assertion(self):
        text='\n'.join(json.dumps(x) for x in [
            {"Action":"run","Test":"TestMathGraphProposedWitness"},
            {"Action":"fail","Test":"TestMathGraphProposedWitness"}])
        self.assertEqual(test_summary(text,1)["status"],"FAIL_NATIVE_ASSERTION")

if __name__=="__main__":unittest.main()
