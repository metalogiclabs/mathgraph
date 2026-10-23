"""Independent source and center-column preflight controls."""
import io
import json
import tarfile
import tempfile
from pathlib import Path
import unittest
from audit_topspin_column import metadata_shape,inspect_members,stream_events,hash_file, PUBLIC_MD5

class TopspinOriginalControls(unittest.TestCase):
    def test_center_column_chosen_from_original_metadata(self):
        values=b"time,x,y,polarity\n0,2,1,1\n50000,2,2,0\n100000,1,2,1\n"
        d=stream_events(io.BytesIO(values),4,5,"synthetic")
        self.assertEqual(d["fixed_column_x"],2)
        self.assertEqual(d["fixed_column_events"],2)
        self.assertEqual(d["fixed_column_polarities"],[1,1])
        self.assertFalse(d["prospective_signal_feasible"])
        self.assertFalse(d["navigation_correction_authorized"])
    def test_metadata_dimensions_never_from_future_events(self):
        self.assertEqual(metadata_shape({"width":640,"height":480}),(640,480))
        with self.assertRaisesRegex(ValueError,"unavailable"):
            metadata_shape({"event_max_x":639,"event_max_y":479})
    def test_negative_time_rejected(self):
        with self.assertRaisesRegex(ValueError,"range"):
            stream_events(io.BytesIO(b"-1,1,1,0\n"),10,10,"bad")
    def test_out_of_order_source_is_retained_but_not_promoted(self):
        d=stream_events(io.BytesIO(b"3,1,1,0\n2,1,1,1\n"),2,3,"bad")
        self.assertEqual(d["events_out_of_timestamp_order"],1)
        self.assertFalse(d["prospective_signal_feasible"])
    def test_path_traversal_in_tar_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"bad.tar.gz"
            with tarfile.open(p,"w:gz") as tf:
                blob=b"hello"
                item=tarfile.TarInfo("../evil.txt")
                item.size=len(blob)
                tf.addfile(item,io.BytesIO(blob))
            with tarfile.open(p,"r:gz") as tf:
                with self.assertRaisesRegex(ValueError,"unsafe"):
                    inspect_members(tf)
    def test_correct_member_shapes(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"archive.tar.gz"
            with tarfile.open(p,"w:gz") as tf:
                for name,body in (("scene/events.csv",b"0,1,1,0\n"),
                                  ("scene/meta.json",b'{"width":4,"height":4}')):
                    item=tarfile.TarInfo(name)
                    item.size=len(body)
                    tf.addfile(item,io.BytesIO(body))
            with tarfile.open(p,"r:gz") as tf:
                a,b=inspect_members(tf)
                self.assertTrue(a.name.endswith("events.csv"))
                self.assertEqual(metadata_shape(json.load(tf.extractfile(b))),(4,4))
    def test_published_digest_is_source_authority_not_result(self):
        self.assertEqual(PUBLIC_MD5["hubble-perpendicular-slow.tar.gz"],
                         "791716392f201526d814267155291147")
    def test_unknown_geometry_fails(self):
        with self.assertRaisesRegex(ValueError,"invalid"):
            metadata_shape({"width":0,"height":180})

if __name__=="__main__":
    unittest.main()
