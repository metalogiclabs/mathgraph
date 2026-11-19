"""Receiving-side advisory consumer of the qualified finite capability."""
import unittest
from test_stateful_campaign import invoke,finite_oracle

class AgentConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code,result=invoke()
        assert code==0
        cls.result=result
    def test_all_eight_states(self):
        receipt=self.result["receipt"]
        replay=receipt["replay"]
        finite_oracle(replay)
        lookup={tuple(row["observations"]):row["output"] for row in replay["reuse_witness"]}
        for n in range(8):
            got=lookup[(n.bit_count()%2,(n>>2)&1)]
            self.assertEqual(got,((n>>2)&1)|(n.bit_count()%2))
    def test_no_action_authority(self):
        evaluation=self.result["evaluation"]
        self.assertEqual(evaluation["action_authorization"],"NONE")
        self.assertEqual(evaluation["current_applicability"],"UNKNOWN")
        self.assertEqual(evaluation["freshness"],"NOT_CHECKED")
        self.assertEqual(evaluation["revocation"],"NOT_CHECKED")

if __name__=="__main__":unittest.main()
