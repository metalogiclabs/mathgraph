"""Full two-domain transport experiment with actual archived JPL evidence.

Requires the two exact GitHub Actions evidence archives. No canned JPL verdict
is admissible. A receiver decodes MGSO, then invokes independent domain
verifiers. Semantic *equivalence between domains* is not claimed.
"""
import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from test_crystal_transport import encode,decode,Invalid
from test_stateful_campaign import invoke,finite_oracle,POLICY_SHA
from mathgraph_check.public_receipts import build_site,resolve,RECORD_ID,JPL_COMMIT,SUITE_COMMIT,TRUSTED_ZIPS

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"conformance/capability_v1/fixtures/capability-contract.json"
FIX=ROOT/"conformance/capability_v1/fixtures/finite-representation-refinement-v1.json"
POL=ROOT/"conformance/capability_v1/trust-policy.json"
JPL_ID="mathgraph.jpl.checked-source.v1"
CAP_ID="mathgraph.finite.checked-capability.v1"

def transfer_payload(type_id,payload):
    wire=encode(type_id,1,("mathgraph.evidence-bound.v1",),payload)
    typ,version,interfaces,out=decode(wire)
    assert typ==type_id and version==1 and out==payload
    return wire,out

def resolve_jpl(record,goal,source=JPL_COMMIT):
    return resolve(record,{"record_id":RECORD_ID,"source_commit":source,
                           "external_suite_commit":SUITE_COMMIT,"goal":goal})

def impact(active_sources,alternatives):
    """A derived conclusion survives if ANY independently checked support set survives."""
    return {name: any(set(path)<=set(active_sources) for path in support_sets)
            for name,support_sets in alternatives.items()}

class CrossDomainReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p1=os.environ["MATHGRAPH_V1_EVIDENCE_ZIP"]
        p2=os.environ["MATHGRAPH_V2_EVIDENCE_ZIP"]
        cls.zips=(Path(p1),Path(p2))
        assert hashlib.sha256(cls.zips[0].read_bytes()).hexdigest()==TRUSTED_ZIPS["v1"]
        assert hashlib.sha256(cls.zips[1].read_bytes()).hexdigest()==TRUSTED_ZIPS["v2"]
        cls.temp=tempfile.TemporaryDirectory()
        cls.record=build_site(*cls.zips,Path(cls.temp.name))
        code,cls.finite=invoke()
        assert code==0 and cls.finite["receipt"] is not None
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def test_actual_jpl_replay_then_transfer(self):
        wire,payload=transfer_payload(JPL_ID,json.dumps(self.record,sort_keys=True).encode())
        remote=json.loads(payload)
        r=resolve_jpl(remote,"finite_parser_acceptance")
        self.assertEqual(r["status"],"WARRANTED_BOUNDED")
        self.assertEqual(r["verified"],{"matched":48,"total":48,"extra_controls":4})
        self.assertEqual(r["whole_language_validity"],"UNKNOWN")
        self.assertFalse(r["truth_promotion"])
        self.assertEqual(encode(*decode(wire)),wire)
    def test_actual_finite_replay_then_transfer(self):
        receipt=self.finite["receipt"]
        wire,payload=transfer_payload(CAP_ID,json.dumps(receipt,sort_keys=True).encode())
        imported=json.loads(payload)
        self.assertEqual(imported,receipt)
        result=finite_oracle(imported["replay"])
        self.assertEqual(result["reuse_mask"],246)
        self.assertTrue(result["ablation_blocks_reuse"])
        self.assertEqual(encode(*decode(wire)),wire)
    def test_cross_domain_scope_not_equivalence(self):
        self.assertEqual(resolve_jpl(self.record,"universal_yaml_correctness")["status"],"UNKNOWN")
        self.assertEqual(self.finite["evaluation"]["current_applicability"],"UNKNOWN")
        self.assertEqual(self.finite["evaluation"]["action_authorization"],"NONE")
    def test_jpl_mutated_source_not_admitted(self):
        self.assertEqual(resolve_jpl(self.record,"finite_parser_acceptance",source="0"*40)["status"],"UNKNOWN")
    def test_wire_tamper_cannot_preserve_identity(self):
        a=encode(JPL_ID,1,(),b"a");b=encode(JPL_ID,1,(),b"b")
        self.assertNotEqual(hashlib.sha256(a).digest(),hashlib.sha256(b).digest())
    def test_selective_invalidation_and_alternative_support(self):
        supports={"jpl_only":[["jpl"]],"cap_only":[["cap"]],"both":[["jpl","cap"]],
                  "alternate":[["jpl"],["cap"]],"unsupported":[]}
        all_live=impact({"jpl","cap"},supports)
        self.assertTrue(all_live["both"])
        after=impact({"cap"},supports)
        self.assertFalse(after["jpl_only"])
        self.assertFalse(after["both"])
        self.assertTrue(after["cap_only"])
        self.assertTrue(after["alternate"])
        self.assertFalse(after["unsupported"])
    def test_no_authentication_or_economic_promotion(self):
        self.assertEqual(self.finite["evaluation"]["qualification"],"QUALIFIED_BOUNDED")
        self.assertEqual(self.finite["evaluation"]["freshness"],"NOT_CHECKED")
        self.assertEqual(self.finite["evaluation"]["revocation"],"NOT_CHECKED")

if __name__=="__main__":unittest.main()
