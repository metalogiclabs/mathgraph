#!/usr/bin/env python3
"""Synthetic positive, negative, equality, no-reference controls BEFORE held-out source."""
import json,sys,types,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import propose,baseline_reference

def module(mode):
    toy=types.ModuleType("toy")
    def dumps(value):
        if mode=="constant":return "0"
        if mode=="no-reference":return b"\\x00"+repr(value).encode()
        return json.dumps(value)
    def loads(text):
        if mode=="no-reference":
            return repr(text)
        parsed=json.loads(text)
        if mode=="wrong-reference" and parsed=="hello":return "BAD"
        return parsed
    dumps.__module__="toy"
    loads.__module__="toy"
    toy.dumps=dumps;toy.loads=loads
    return toy

class ProofOfControls(unittest.TestCase):
    def compare(self,mod):
        p=propose.inspect_api(mod)["results"]
        b=baseline_reference.evaluate(mod)
        self.assertEqual(len(p),len(b))
        for left,right in zip(p,b):
            self.assertEqual(left["id"],right["id"])
            for name in ("accepted","strict_matches","strict_counterexamples",
                         "canonical_supported","canonical_counterexamples",
                         "reference_supported","reference_counterexamples",
                         "reference_distinct_outputs","reference_has_container",
                         "reference_perturbation_rejections","strict_verdict",
                         "normal_form_verdict","reference_verdict"):
                self.assertEqual(left[name],right[name],(name,left.get(name),right.get(name)))
            for a,z in zip(left["samples"],right["samples"]):
                for name in ("index","encoder","strict","normal_form","reference","negative_json"):
                    self.assertEqual(a[name],z[name],(name,a,z))
        return p
    def test_prospective_json_positive_and_normalization(self):
        r=self.compare(module("correct"))[0]
        self.assertEqual(r["reference_verdict"],"WARRANTED_BOUNDED_JSON_SUBSET")
        self.assertEqual(r["normal_form_verdict"],"WARRANTED_BOUNDED_FINITE")
        self.assertEqual(r["strict_verdict"],"REJECTED_BOUNDED")
        self.assertGreaterEqual(r["reference_perturbation_rejections"],2)
    def test_source_decoder_conflicts_with_independent_json(self):
        r=self.compare(module("wrong-reference"))[0]
        self.assertEqual(r["reference_verdict"],"REJECTED_BOUNDED")
    def test_constant_codec_does_not_earn_reference_warrant(self):
        r=self.compare(module("constant"))[0]
        self.assertEqual(r["reference_verdict"],"UNKNOWN_NO_INDEPENDENT_REFERENCE")
    def test_non_json_source_no_oracle(self):
        r=self.compare(module("no-reference"))[0]
        self.assertEqual(r["reference_verdict"],"UNKNOWN_NO_INDEPENDENT_REFERENCE")
    def test_no_relation_family_fail_closed(self):
        t=types.ModuleType("toy")
        self.assertEqual(propose.inspect_api(t)["pair_count"],0)
        self.assertEqual(baseline_reference.evaluate(t),[])
    def test_both_methods_same_frozen_seeds(self):
        self.assertEqual(propose.SEEDS,tuple(baseline_reference.FIXTURES))
        self.assertEqual(len(propose.SEEDS),17)

if __name__=="__main__":unittest.main()
