"""Finite permission controls and exact pinned upstream qualification."""
import base64
import os
from pathlib import Path
import unittest

from upstream_encoding_transfer import domain, minimum_separator, oracle
from permitted_witness_audit import SCENARIOS, permission_audit


class PermissionWitnessTests(unittest.TestCase):
    def test_all_permitted_observations_have_minimum_cost_six(self):
        inputs=domain()
        original=[oracle(x) for x in inputs]
        obs={
            "reference":original,
            "standard_alphabet":[base64.b64encode(x).rstrip(b"=") for x in inputs],
            "unstripped_padding":[base64.urlsafe_b64encode(x) for x in inputs],
            "trailing_zero_loss":[oracle(x.rstrip(b"\x00") if len(x)%3==0 else x) for x in inputs],
        }
        r=minimum_separator(inputs,obs)
        self.assertEqual(r["tests_hex"],["00","f80000"])
        self.assertEqual(r["total_synthetic_cost"],6)

    def test_losing_sensor_changes_cost_or_obstructs(self):
        inputs=domain()
        obs={
            "reference":[oracle(x) for x in inputs],
            "standard_alphabet":[base64.b64encode(x).rstrip(b"=") for x in inputs],
            "unstripped_padding":[base64.urlsafe_b64encode(x) for x in inputs],
            "trailing_zero_loss":[oracle(x.rstrip(b"\x00") if len(x)%3==0 else x) for x in inputs],
        }
        expected={
            "all_permitted":("MINIMUM_BASIS",6,[]),
            "one_byte_forbidden":("MINIMUM_BASIS",7,[]),
            "only_three_byte":("OBSTRUCTION",None,["unstripped_padding"]),
            "only_one_byte":("OBSTRUCTION",None,["trailing_zero_loss"]),
            "no_probes":("OBSTRUCTION",None,["standard_alphabet","trailing_zero_loss","unstripped_padding"]),
        }
        for name,lengths in SCENARIOS.items():
            ix=[i for i,x in enumerate(inputs) if len(x) in lengths]
            solution=minimum_separator(tuple(inputs[i] for i in ix),
                {name2:[values[i] for i in ix] for name2,values in obs.items()})
            with self.subTest(name=name):
                self.assertEqual(solution["status"],expected[name][0])
                self.assertEqual(solution["total_synthetic_cost"],expected[name][1])
                self.assertEqual(solution["unsplittable"],expected[name][2])
                if name=="one_byte_forbidden":
                    self.assertEqual(solution["tests_hex"],["0000","f80000"])

    def test_native_source_replay_and_permission_obstruction(self):
        upstream=os.environ.get("MATHGRAPH_PINNED_UPSTREAM")
        if not upstream:
            self.skipTest("requires separately checked out source")
        r=permission_audit(Path(upstream))
        self.assertEqual(r["full_domain_size"],1026)
        self.assertEqual(r["observation_grammar"],"only input lengths 1,2,3 may be selected")
        self.assertEqual(len(r["excluded_controls_hex"]),3)
        self.assertEqual(r["source"]["commit"],"672971d66a2ef9f85151e53283113f33d642dabd")
        s=r["scenarios"]
        self.assertEqual(s["all_permitted"]["tests_hex"],["00","f80000"])
        self.assertEqual(s["one_byte_forbidden"]["total_synthetic_cost"],7)
        self.assertEqual(s["only_three_byte"]["unsplittable"],["unstripped_padding"])

if __name__=="__main__":
    unittest.main()
