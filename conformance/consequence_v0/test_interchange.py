"""Independent, fail-closed three-domain interchange boundary experiment.

Only JPL and finite capability records are locally materialized. The WebArena
negative control is source-pinned metadata, NOT an independently replayed verdict.
No envelope can grant its own qualification.
"""
import copy
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "website/src/data/record-index.json"
CAP = ROOT / "conformance/capability_v1/evaluation.json"
SCHEMA = ROOT / "protocol/schemas/consequence-envelope-v0.schema.json"

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def evidence_projection():
    idx = read(INDEX)
    records = {r["id"]: r for r in idx["records"]}
    jpl = records["mg-l4yaml-source-check-20261010"]
    cap = read(CAP)
    return {
        "jpl": {
            "source": jpl["scope"]["source_commit"],
            "suite": jpl["scope"]["external_suite_commit"],
            "goals": jpl["scope"]["supported_goals"],
            "historical": jpl["historic_status"],
            "unknowns": jpl["unknowns"],
            "record_digest": jpl["record_content_sha256"],
        },
        "capability": {
            "id": cap["contract"]["id"],
            "profile": cap["contract"]["profile"],
            "qualification": cap["qualification"],
            "applicability": cap["current_applicability"],
            "authorization": cap["action_authorization"],
            "policy_digest": cap["trust_policy"]["sha256"],
        },
        "negative": {
            "source_commit": "6502a30d6ff45814a01bba5f68d7d093b9d2cb1b",
            "ci_run": "38036286320",
            "matched_retained": 3,
            "matched_stateless": 3,
            "strong_baseline_advantage": "REJECTED_ON_THIS_CASE",
            "replay": "NOT_REPLAYED_BY_THIS_CONSUMER",
        }
    }

def resolve(projection, key, requested_scope, policy):
    """Consumer-owned, source-exact policy; never interpret producer statuses as authority."""
    if key == "jpl":
        p = projection["jpl"]
        if (requested_scope != "finite_parser_acceptance"
            or p["source"] != "62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
            or p["suite"] != "da267a5c4782e7361e82889e76c0dc7df0e1e870"
            or p["record_digest"] != "f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb"
            or p["goals"] != ["finite_parser_acceptance"]):
            return "UNKNOWN"
        return "SOURCE_PINNED_HISTORICAL_OBSERVATION" if policy == "historical" else "UNKNOWN"
    if key == "capability":
        p = projection["capability"]
        if (requested_scope != "mathgraph.finite-representation-refinement.v1"
            or p["id"] != "urn:mathgraph:capability:finite-developmental-growth"
            or p["policy_digest"] != "7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89"
            or p["qualification"] != "QUALIFIED_BOUNDED"):
            return "UNKNOWN"
        return "EXISTING_PROFILE_RECEIPT_REFERENCED" if policy == "historical" else "UNKNOWN"
    if key == "negative":
        p = projection["negative"]
        if (requested_scope == "matched_webarena_f" and policy == "historical"
            and p["source_commit"] == "6502a30d6ff45814a01bba5f68d7d093b9d2cb1b"
            and p["matched_retained"] == p["matched_stateless"] == 3):
            return "NEGATIVE_REPORTED_NOT_REPLAYED"
    return "UNKNOWN"

class InterchangeBoundary(unittest.TestCase):
    def setUp(self):
        self.p = evidence_projection()
    def test_existing_sources_pinned(self):
        self.assertEqual(self.p["jpl"]["historical"], "WARRANTED_BOUNDED")
        self.assertEqual(self.p["capability"]["qualification"], "QUALIFIED_BOUNDED")
    def test_exact_jpl(self):
        self.assertEqual(resolve(self.p,"jpl","finite_parser_acceptance","historical"),"SOURCE_PINNED_HISTORICAL_OBSERVATION")
    def test_jpl_universal_rejected(self):
        self.assertEqual(resolve(self.p,"jpl","universal_yaml","historical"),"UNKNOWN")
    def test_jpl_mutated_source_rejected(self):
        x=copy.deepcopy(self.p); x["jpl"]["source"]="0"*40
        self.assertEqual(resolve(x,"jpl","finite_parser_acceptance","historical"),"UNKNOWN")
    def test_jpl_mutated_receipt_rejected(self):
        x=copy.deepcopy(self.p); x["jpl"]["record_digest"]="0"*64
        self.assertEqual(resolve(x,"jpl","finite_parser_acceptance","historical"),"UNKNOWN")
    def test_capability_scope_rejected(self):
        self.assertEqual(resolve(self.p,"capability","universal","historical"),"UNKNOWN")
    def test_capability_policy_mutation_rejected(self):
        x=copy.deepcopy(self.p); x["capability"]["policy_digest"]="0"*64
        self.assertEqual(resolve(x,"capability","mathgraph.finite-representation-refinement.v1","historical"),"UNKNOWN")
    def test_current_applicability_not_promoted(self):
        self.assertEqual(resolve(self.p,"capability","mathgraph.finite-representation-refinement.v1","current"),"UNKNOWN")
    def test_negative_control_not_economic_win(self):
        self.assertEqual(resolve(self.p,"negative","matched_webarena_f","historical"),"NEGATIVE_REPORTED_NOT_REPLAYED")
        self.assertEqual(self.p["negative"]["strong_baseline_advantage"],"REJECTED_ON_THIS_CASE")
    def test_negative_unpinned_change_rejected(self):
        x=copy.deepcopy(self.p); x["negative"]["matched_stateless"]=9
        self.assertEqual(resolve(x,"negative","matched_webarena_f","historical"),"UNKNOWN")
    def test_unknown_critical_semantics(self):
        self.assertEqual(resolve(self.p,"unrecognized","anything","historical"),"UNKNOWN")
    def test_no_claim_of_cross_domain_replay(self):
        self.assertEqual(self.p["negative"]["replay"],"NOT_REPLAYED_BY_THIS_CONSUMER")

if __name__ == "__main__":
    unittest.main()
