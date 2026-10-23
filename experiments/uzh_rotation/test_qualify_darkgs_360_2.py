import unittest
from qualify_darkgs_360_2 import ORIGINAL_DEPOSIT_MD5,ORIGINAL_DEPOSIT_NAME,FROZEN_360_METHOD_BLOB
from qualify_darkgs_360 import datafile_entry,geometry
import numpy as np
from scipy.spatial.transform import Rotation

class FrozenSecondSourceTests(unittest.TestCase):
    def test_published_original_md5_frozen(self):
        self.assertEqual(ORIGINAL_DEPOSIT_MD5,"9a05e7d528241ad9a4f055170f3a710f")
    def test_first_classifier_git_blob_frozen(self):
        self.assertEqual(FROZEN_360_METHOD_BLOB,"4a8138ab153243aa656342e4cf704fb662fd7e46")
    def test_metadata_label_is_exact_second_original_source(self):
        doc={"data":{"latestVersion":{"files":[{"dataFile":{
            "filename":"360_2.zip","id":51,"checksum":{"type":"MD5","value":ORIGINAL_DEPOSIT_MD5}}}]}}}
        result=datafile_entry(doc,name=ORIGINAL_DEPOSIT_NAME)
        self.assertEqual(result["datafile_id"],51)
    def test_no_changes_to_consequential_classification(self):
        t=np.arange(400,dtype=np.int64)*10000000
        q=Rotation.from_euler("z",np.linspace(0,6*np.pi,len(t))).as_quat()
        r=geometry(t,q,np.zeros((len(t),3)))
        self.assertTrue(r["two_continuous_world_z_yaw_turns_qualified_in_source_model"])
        self.assertFalse(r["navigation_heading_correction_authorized"])
if __name__=="__main__":
    unittest.main()
