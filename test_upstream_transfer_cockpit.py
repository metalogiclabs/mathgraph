import unittest
from upstream_transfer_cockpit import render

def fixture():
    return {
        "schema":"mathgraph.upstream-evidence-acquisition.v1",
        "mode":"PINNED_UPSTREAM_WITH_SCRIPTED_MUTATIONS_NOT_LIVE_NEBIUS",
        "origin":{"repository":"pallets/itsdangerous",
                  "commit":"672971d66a2ef9f85151e53283113f33d642dabd"},
        "experiment":{"testcase_domain":1026,"minimum_tests_hex":["00","f80000"],
                      "minimum_synthetic_cost":6,"independent_brute_force_cost":6},
        "comparison":{"baseline_original_tests":"WARRANTED",
                      "with_new_test":"REJECTED",
                      "after_scripted_repair":"WARRANTED"},
        "transitions":[{"step":name,"state":state}
            for name,state in [
                ("native_original_tests","WARRANTED"),
                ("test_source_changed","REJECTED"),
                ("missing_evidence","UNKNOWN"),
                ("new_test_fails","REJECTED"),
                ("candidate_changed","REJECTED"),
                ("fresh_expanded_tests","WARRANTED")]],
    }

class UpstreamCockpitTests(unittest.TestCase):
    def test_transparent_static_provenance(self):
        html=render(fixture())
        self.assertIn("REAL UPSTREAM SOURCE",html)
        self.assertIn("NOT A LIVE NEBIUS MODEL RUN",html)
        self.assertIn("f80000",html)
        self.assertIn("pallets/itsdangerous",html)
        self.assertIn("synthetic",html.lower())

    def test_schema_and_provenance_fail_closed(self):
        for key,change in [("schema","other"),("mode","nebius")]:
            obj=fixture()
            obj[key]=change
            with self.subTest(key=key), self.assertRaises(ValueError):
                render(obj)
        obj=fixture()
        obj["origin"]["commit"]="foreign"
        with self.assertRaises(ValueError):
            render(obj)

    def test_not_a_warrant_verifier(self):
        obj=fixture()
        obj["comparison"]["with_new_test"]="WARRANTED"
        with self.assertRaises(ValueError):
            render(obj)
        obj=fixture()
        obj["experiment"]["independent_brute_force_cost"]=5
        with self.assertRaises(ValueError):
            render(obj)

    def test_escaped_adversarial_string(self):
        obj=fixture()
        obj["transitions"][0]["step"]='</script><img src=x onerror=alert(1)>'
        html=render(obj)
        self.assertNotIn("</script><img",html)
        self.assertIn("\\u003c/script",html)
        obj["experiment"]["minimum_tests_hex"][0]="<img>"
        with self.assertRaises(ValueError):
            render(obj)

    def test_missing_timeline_rejected(self):
        obj=fixture()
        obj["transitions"]=[]
        with self.assertRaises(ValueError):
            render(obj)

if __name__=="__main__":
    unittest.main()
