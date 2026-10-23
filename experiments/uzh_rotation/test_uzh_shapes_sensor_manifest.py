import io,tempfile,unittest,zipfile
from pathlib import Path
from uzh_shapes_sensor_manifest import safe_members,first_rows,SOURCE_SHA256

class SourceSchemaTests(unittest.TestCase):
    def test_hash_frozen_from_prior_source_admission(self):
        self.assertEqual(SOURCE_SHA256,
                         "56aade6bf53dcf73e8fe40905ccac8385cd7606bc9a85103bf2c9f9045117551")
    def test_preview_excludes_comments(self):
        rows,count,raw=first_rows(b"# Units of IMU\n1 2 3\n2 3 4\n",1)
        self.assertEqual((rows,count),(["1 2 3"],2))
    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("../imu.txt","1 2 3")
            with zipfile.ZipFile(p) as z:
                with self.assertRaisesRegex(ValueError,"unsafe"):
                    safe_members(z)
    def test_zip_member_shape(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"ok.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("seq/imu.txt","0 1 2 3 4 5 6")
            with zipfile.ZipFile(p) as z:
                self.assertEqual(safe_members(z)[0].filename,"seq/imu.txt")
if __name__=="__main__":unittest.main()
