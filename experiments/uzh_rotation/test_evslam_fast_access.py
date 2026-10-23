import unittest
from probe_evslam_fast_access import report_status, FAST_METADATA_BYTES,FAST_FILE_ID

class TestPublisherAccessClassification(unittest.TestCase):
    def test_quota_is_not_a_camera_result(self):
        self.assertEqual(report_status(1,"Too many users have viewed or downloaded this file recently.",False,None),
                         "UNKNOWN_PUBLISHER_DOWNLOAD_QUOTA")
    def test_generic_failure_remains_unknown(self):
        self.assertEqual(report_status(1,"404",False,None),"UNKNOWN_ORIGINAL_SOURCE_TRANSFER_FAILED")
    def test_wrong_file_size_rejected(self):
        self.assertEqual(report_status(0,"",True,42),"UNKNOWN_ORIGINAL_SIZE_MISMATCH")
    def test_absence_rejected(self):
        self.assertEqual(report_status(0,"",False,None),"UNKNOWN_NO_SOURCE_BYTES")
    def test_exact_publisher_size_positive(self):
        self.assertEqual(report_status(0,"",True,FAST_METADATA_BYTES),"SOURCE_ACQUIRED_FOR_RAW_BAG_PROBE")
    def test_id_source_scope(self):
        self.assertEqual(FAST_FILE_ID,"1t4viDrRV40_uOS3Tfh9-jMbGKgHorTI1")
if __name__=="__main__":
    unittest.main()
