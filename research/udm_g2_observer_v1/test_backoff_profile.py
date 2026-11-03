"""Finite Go AST admission controls for a source-distinct ticker calibration.

No model call, untrusted PR code, or external source execution is needed.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VALIDATOR = ROOT / "validate.go"

def admitted(src, package="backoff"):
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"candidate.go"
        path.write_text(src, encoding="utf-8")
        p=subprocess.run(["go","run",str(VALIDATOR),"--","--package",package,str(path)],
            text=True,capture_output=True,timeout=30)
        if p.returncode: raise AssertionError("Go AST helper did not run: "+p.stderr)
        return json.loads(p.stdout)

GO_TEST='''package backoff
import ("testing"; "time"; "sync")
func TestMathGraphProposedWitness(t *testing.T) {
  _ = time.Second
  var m sync.Mutex
  m.Lock()
  m.Unlock()
  t.Error("bounded sentinel")
}
'''

class ProfileChecks(unittest.TestCase):
    def test_admits_explicit_backoff_with_stdlib_time_and_sync(self):
        self.assertEqual(admitted(GO_TEST)["status"], "ADMITTED_TEST_ONLY_CANDIDATE")
    def test_refuses_wrong_package(self):
        self.assertNotEqual(admitted(GO_TEST, "zerolog")["status"], "ADMITTED_TEST_ONLY_CANDIDATE")
    def test_refuses_untrusted_os_import(self):
        bad=GO_TEST.replace('"sync")','"sync";"os")')
        self.assertNotEqual(admitted(bad)["status"], "ADMITTED_TEST_ONLY_CANDIDATE")
    def test_refuses_out_of_scope_package_argument(self):
        self.assertNotEqual(admitted(GO_TEST, "another")["status"], "ADMITTED_TEST_ONLY_CANDIDATE")

if __name__=="__main__":unittest.main()
