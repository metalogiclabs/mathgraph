#!/usr/bin/env python3
"""Pre-source synthetic conformance controls for frozen candidate generator and baseline."""
import sys,types,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import propose,baseline_reference

def fixture(mode):
    toy=types.ModuleType("toy")
    class ToyEncoder:
        def encode(self,content,optional=True):
            if not isinstance(content,(str,bytes)):raise TypeError("non scalar")
            return content
    class ToyDecoder:
        def decode(self,content,optional=None):return content
    class BrokenDecoder:
        def decode(self,content,optional=None):return "not the input"
    class InapplicableEncoder:
        def encode(self,content,optional=None):raise TypeError("no inputs")
    for c in (ToyEncoder,ToyDecoder,BrokenDecoder,InapplicableEncoder):c.__module__="toy"
    toy.ToyEncoder=InapplicableEncoder if mode=="none" else ToyEncoder
    toy.ToyDecoder=BrokenDecoder if mode=="broken" else ToyDecoder
    return toy

class Conformance(unittest.TestCase):
    def check(self,mode,expected):
        t=fixture(mode)
        a=propose.run(t)
        b=baseline_reference.judge(t)
        self.assertEqual(a["candidate_count"],1)
        self.assertEqual(a["results"][0]["status"],expected)
        self.assertEqual(b[0]["status"],expected)
        self.assertEqual(a["results"][0]["accepted"],b[0]["accepted"])
        self.assertEqual(a["results"][0]["counterexamples"],b[0]["counterexamples"])
    def test_valid_and_ineligible_inputs(self):self.check("good","WARRANTED_BOUNDED_FINITE")
    def test_real_counterexample_not_promoted(self):self.check("broken","REJECTED_BOUNDED")
    def test_no_applicability_stays_unknown(self):self.check("none","UNKNOWN_NO_APPLICABILITY")
    def test_unsupported_relations(self):
        m=types.ModuleType("toy")
        self.assertEqual(propose.run(m)["overall"],"UNKNOWN_NO_RELATION_FAMILY")
        self.assertEqual(baseline_reference.judge(m),[])
    def test_identical_predeclared_seeds(self):
        self.assertEqual(propose.SEEDS,tuple(baseline_reference.VALUES))
        self.assertEqual(len(propose.SEEDS),13)

if __name__=="__main__":unittest.main()
