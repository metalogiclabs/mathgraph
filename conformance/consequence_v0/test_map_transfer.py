"""Map transfer and selective invalidation falsifiers.

This is a finite structural model, NOT a cross-domain semantic transport proof.
Edges are untrusted unless consumer-owned policy admits exact dependencies.
"""
import copy
import unittest
from test_interchange import evidence_projection, resolve

def source_map():
    p=evidence_projection()
    return {"nodes":{"jpl":p["jpl"],"capability":p["capability"],"negative":p["negative"]},
            "edges":[{"from":"jpl","to":"capability","type":"candidate_related","warrant":"UNKNOWN"}]}

def transfer(source, selected, requested_scopes):
    """Copy only exact selected nodes; reject unrecognized scopes, never promote edges."""
    output={"nodes":{},"edges":[],"outcomes":{}}
    for key in selected:
        if key not in source["nodes"]:
            output["outcomes"][key]="UNKNOWN"
            continue
        scope=requested_scopes.get(key,"")
        verdict=resolve(source["nodes"] if "negative" in source["nodes"] else {},key,scope,"historical")
        if verdict=="UNKNOWN":
            output["outcomes"][key]="UNKNOWN"
            continue
        output["nodes"][key]=copy.deepcopy(source["nodes"][key])
        output["outcomes"][key]=verdict
    return output

def invalidate(map_state, changed):
    """Only an explicit verified dependency may propagate invalidation."""
    invalid=set(changed)
    edges=map_state.get("edges",[])
    progress=True
    while progress:
        progress=False
        for edge in edges:
            if edge.get("warrant")=="WARRANTED" and edge.get("type")=="requires" and edge.get("to") in invalid and edge.get("from") not in invalid:
                invalid.add(edge["from"]);progress=True
    return invalid

class MapBoundary(unittest.TestCase):
    def test_transfer_keeps_scope_and_unknown_edges(self):
        source=source_map()
        out=transfer(source,["jpl","capability"],{"jpl":"finite_parser_acceptance","capability":"mathgraph.finite-representation-refinement.v1"})
        self.assertEqual(set(out["nodes"]),{"jpl","capability"})
        self.assertEqual(out["edges"],[])
        self.assertEqual(out["nodes"]["capability"]["applicability"],"UNKNOWN")
    def test_broadened_scope_cannot_import(self):
        out=transfer(source_map(),["jpl"],{"jpl":"universal_yaml"})
        self.assertEqual(out["nodes"],{})
        self.assertEqual(out["outcomes"]["jpl"],"UNKNOWN")
    def test_candidate_edge_cannot_invalidate_unrelated(self):
        source=source_map()
        self.assertEqual(invalidate(source,{"jpl"}),{"jpl"})
    def test_verified_dependency_propagates_but_only_as_assumed_model(self):
        source=source_map()
        source["edges"]=[{"from":"capability","to":"jpl","type":"requires","warrant":"WARRANTED"}]
        self.assertEqual(invalidate(source,{"jpl"}),{"jpl","capability"})
    def test_rejected_economic_gain_is_not_promoted(self):
        source=source_map()
        out=transfer(source,["negative"],{"negative":"matched_webarena_f"})
        self.assertEqual(out["outcomes"]["negative"],"NEGATIVE_REPORTED_NOT_REPLAYED")
        self.assertEqual(out["nodes"]["negative"]["strong_baseline_advantage"],"REJECTED_ON_THIS_CASE")
    def test_source_not_mutated_by_transfer(self):
        source=source_map(); old=copy.deepcopy(source)
        transfer(source,["jpl"],{"jpl":"finite_parser_acceptance"})
        self.assertEqual(source,old)

if __name__=="__main__":
    unittest.main()
