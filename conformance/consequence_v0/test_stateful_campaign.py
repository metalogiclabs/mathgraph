"""One-shot stateful qualification campaign for the candidate interchange foundation.

Real finite-profile replay is delegated to the existing independently implemented
consumer; the downstream oracle and ablation are recomputed here. The JPL and
WebArena evidence are NOT independently re-executed by this campaign.
"""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "conformance/capability_v1"
POLICY_SHA = "7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89"
SOURCE = BASE / "consumer.py"
FIXTURE = BASE / "fixtures/finite-representation-refinement-v1.json"
CONTRACT = BASE / "fixtures/capability-contract.json"
POLICY = BASE / "trust-policy.json"
RECEIPT = BASE / "receipt.json"
INDEX = ROOT / "website/src/data/record-index.json"


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(fixture=FIXTURE, contract=CONTRACT, policy=POLICY):
    proc = subprocess.run(
        [sys.executable, "-I", "-S", str(SOURCE), "--fixture", str(fixture),
         "--contract", str(contract), "--policy", str(policy),
         "--policy-sha256", POLICY_SHA],
        cwd=str(ROOT), capture_output=True, text=True, timeout=45, check=False)
    if not proc.stdout.strip():
        raise AssertionError("CONSUMER_NO_JSON: " + proc.stderr[-400:])
    return proc.returncode, json.loads(proc.stdout)


def finite_oracle(replay):
    """Independent receiver: execute imported lookup on every carrier state."""
    rows = replay["reuse_witness"]
    assert len(rows) == 4
    lookup = {}
    for row in rows:
        key = tuple(row["observations"])
        assert len(key) == 2 and key not in lookup
        assert row["output"] in (0, 1)
        lookup[key] = row["output"]
    observed = []
    for n in range(8):
        bit0 = (n >> 2) & 1
        parity = n.bit_count() % 2
        observed.append(lookup[(parity, bit0)])
    actual = sum(v << i for i, v in enumerate(observed))
    target = sum((((n >> 2) & 1) | (n.bit_count() % 2)) << n for n in range(8))
    assert actual == target == replay["reuse_mask"] == 246
    # No policy on the old parity quotient can realize this target.
    parity_cells = {}
    for n in range(8):
        p = n.bit_count() % 2
        parity_cells.setdefault(p, set()).add((target >> n) & 1)
    assert any(len(outputs) > 1 for outputs in parity_cells.values())
    return {"states": 8, "target_mask": target,
            "reuse_mask": actual, "ablation_blocks_reuse": True,
            "qualified_external_organization": False}


def run_campaign():
    assert digest(POLICY) == POLICY_SHA
    code, result = invoke()
    assert code == 0, result
    assert result["evaluation"]["qualification"] == "QUALIFIED_BOUNDED"
    assert result["evaluation"]["current_applicability"] == "UNKNOWN"
    assert result["evaluation"]["action_authorization"] == "NONE"
    replay = result["receipt"]["replay"]
    assert replay["boolean_refinements_tested"] == 256
    assert replay["successful_refinements"] == 32
    assert replay["refined_closure_size"] == 16
    assert len(replay["old_closure_masks"]) == 4
    # The receiver never executes the producer experiment or trusts its verdict.
    reuse = finite_oracle(replay)
    assert result["receipt"] == read(RECEIPT)
    # The original JPL source is a distinct, bounded authority.
    index = read(INDEX)
    jpl = next(x for x in index["records"] if x["id"] == "mg-l4yaml-source-check-20261010")
    assert jpl["scope"]["supported_goals"] == ["finite_parser_acceptance"]
    assert "whole_language_correctness" in jpl["unknowns"]
    # Do not invent an independent WebArena replay.
    return {
        "schema": "mathgraph.consequence-campaign.v0",
        "source": {"consumer_sha256": digest(SOURCE),
                   "fixture_sha256": digest(FIXTURE),
                   "contract_sha256": digest(CONTRACT),
                   "policy_sha256": digest(POLICY)},
        "finite": {"qualification": "QUALIFIED_BOUNDED",
                   "basis": "same-owner implementation-independent qualification",
                   "reuse": reuse},
        "jpl": {"historical": jpl["historic_status"],
                "supported_goals": jpl["scope"]["supported_goals"],
                "current_requalification": "NOT_CHECKED"},
        "webarena": {"status": "NOT_INDEPENDENTLY_REPLAYED_IN_THIS_CAMPAIGN",
                     "strong_baseline_advantage": "NOT_PROMOTED"},
        "transport": "FINITE_CONSUMER_TO_DISTINCT_RECEIVER_ORACLE",
        "cross_domain_semantic_transport": "UNKNOWN",
        "new_capability_acquisition": "NOT_DEMONSTRATED",
        "economic_compounding": "UNKNOWN",
        "current_applicability": "UNKNOWN",
        "authorization": "NONE",
    }


class StatefulCampaign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_campaign()

    def test_replay_and_reuse(self):
        self.assertTrue(self.result["finite"]["reuse"]["ablation_blocks_reuse"])

    def test_repeat_exact(self):
        self.assertEqual(self.result, run_campaign())

    def test_mutated_fixture_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = read(FIXTURE)
            obj["scope"] = "universal"
            file = Path(tmp) / "fixture.json"
            file.write_text(json.dumps(obj))
            code, outcome = invoke(fixture=file)
            self.assertNotEqual(code, 0)
            self.assertIsNone(outcome["receipt"])
            self.assertEqual(outcome["evaluation"]["qualification"], "UNKNOWN")

    def test_mutated_contract_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = read(CONTRACT)
            obj["claim"]["scope"] = "universal"
            file = Path(tmp) / "contract.json"
            file.write_text(json.dumps(obj))
            code, outcome = invoke(contract=file)
            self.assertNotEqual(code, 0)
            self.assertIsNone(outcome["receipt"])

    def test_no_cross_domain_promotion(self):
        self.assertEqual(self.result["cross_domain_semantic_transport"], "UNKNOWN")
        self.assertEqual(self.result["webarena"]["status"], "NOT_INDEPENDENTLY_REPLAYED_IN_THIS_CAMPAIGN")
        self.assertEqual(self.result["authorization"], "NONE")


if __name__ == "__main__":
    if "--report" in sys.argv:
        print(json.dumps(run_campaign(), sort_keys=True, indent=2))
    else:
        unittest.main()
