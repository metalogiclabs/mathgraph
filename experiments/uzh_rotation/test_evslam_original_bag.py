import hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from probe_evslam_original_bag import inspect_original, safe_archive_names, source_digest

class OriginalSensorProbeTests(unittest.TestCase):
    def test_source_hash_binds_exact_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"mock.bag";p.write_bytes(b"fake-source-data")
            self.assertEqual(source_digest(p)[0],hashlib.sha256(b"fake-source-data").hexdigest())
    def test_disallow_zip_path_traversal(self):
        with self.assertRaisesRegex(ValueError,"dangerous"):
            safe_archive_names(["../source.bag"])
        with self.assertRaisesRegex(ValueError,"dangerous"):
            safe_archive_names(["a\\b.bag"])
    def test_zip_detected_without_unsafe_implicit_extraction(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"source.bag"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("record.bag","not real bag data")
            r=inspect_original(p)
            self.assertEqual(r["original_source_record_type"],"ZIP_ARCHIVE")
            self.assertEqual(r["source_status"],"UNKNOWN_ZIP_NEEDS_SEPARATE_SAFE_ORIGINAL_BAG_REPLAY")
            self.assertFalse(r["camera_event_values_opened"])
            self.assertFalse(r["heading_correction_authorized"])
    def test_unrecognized_source_is_unknown(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"source.bag";p.write_bytes(b"fake bag no header")
            r=inspect_original(p)
            self.assertEqual(r["source_status"],"UNKNOWN_ORIGINAL_CONTAINER_UNRECOGNIZED")
            self.assertFalse(r["reference_gt_quaternions_opened"])
    def test_invalid_zip_path_not_published_as_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"source.bag"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("../evil.bag","bad")
            with self.assertRaisesRegex(ValueError,"dangerous"):
                inspect_original(p)
if __name__=="__main__":unittest.main()
