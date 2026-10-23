import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from capture import classify, unique_orders
class CaptureTests(unittest.TestCase):
    def test_http_error_not_empty(self):
        self.assertEqual(classify({'status':503,'body':'{}'})['kind'],'HTTP_ERROR')
    def test_transport_error_not_empty(self):
        self.assertEqual(classify({'error':'dns'})['kind'],'TRANSPORT_ERROR')
    def test_throttle_stops(self):
        self.assertEqual(classify({'status':429,'body':'{}'})['kind'],'THROTTLED')
    def test_malformed_json_not_empty(self):
        self.assertEqual(classify({'status':200,'body':'not json'})['kind'],'INVALID_JSON')
    def test_unknown_schema_not_empty(self):
        self.assertEqual(classify({'status':200,'body':'{}'})['kind'],'UNKNOWN_SCHEMA')
    def test_successful_empty(self):
        self.assertEqual(classify({'status':200,'body':'{"orders":[]}'})['kind'],'SUCCESS')
    def test_nonlist_orders(self):
        self.assertEqual(classify({'status':200,'body':'{"orders":{}}'})['kind'],'UNKNOWN_SCHEMA')
    def test_dedup_preserves_order(self):
        r={'status':200,'body':'{"orders":[{"orderHash":"0xabc","orderStatus":"open"}]}','finished_utc':'t1'}
        self.assertEqual(len(unique_orders([r,r])),1)
        self.assertEqual(unique_orders([r,r])[0]['observations'],2)
    def test_missing_hash_not_counted(self):
        self.assertEqual(unique_orders([{'status':200,'body':'{"orders":[{"x":1}]}'}]),[])
    def test_schema_list_nonobjects(self):
        self.assertEqual(classify({'status':200,'body':'{"orders":[1]}'})['kind'],'UNKNOWN_SCHEMA')
if __name__=='__main__':unittest.main()
