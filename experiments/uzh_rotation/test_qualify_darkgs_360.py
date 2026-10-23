"""Blind-before-original-data controls for yaw and archive admission."""
import math
import unittest
from pathlib import Path
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation
from qualify_darkgs_360 import (PUBLISHED_MD5,EXPECTED_NAME,
                                datafile_entry,geometry,validate_zip)

def track(turns=3,axis="z",oscillate=False,samples=2001):
    t=np.arange(samples,dtype=np.int64)*10_000_000
    angle=np.linspace(0,turns*2*math.pi,samples)
    if oscillate:angle=.7*math.pi*np.sin(np.linspace(0,24*math.pi,samples))
    q=Rotation.from_euler(axis,angle).as_quat()
    return t,q,np.zeros((samples,3))

class DarkOriginalSourceAdmissionTests(unittest.TestCase):
    def test_original_published_metadata_checksum_and_fileid(self):
        d={"data":{"latestVersion":{"files":[{"dataFile":{
           "filename":"360.zip","id":50,"checksum":{"type":"MD5","value":PUBLISHED_MD5},
           "filesize":134000000}}]}}}
        self.assertEqual(datafile_entry(d)["datafile_id"],50)
    def test_publisher_checksum_mismatch_refused(self):
        d={"data":{"latestVersion":{"files":[{"dataFile":{
           "filename":"360.zip","id":50,"checksum":{"type":"MD5","value":"0"*32}}}]}}}
        with self.assertRaisesRegex(ValueError,"MD5"):
            datafile_entry(d)
    def test_actual_three_turn_worldz_candidate(self):
        x=geometry(*track())
        self.assertTrue(x["two_continuous_world_z_yaw_turns_qualified_in_source_model"])
        self.assertFalse(x["navigation_heading_correction_authorized"])
    def test_one_yaw_revolution_rejected(self):
        x=geometry(*track(turns=1))
        self.assertFalse(x["two_continuous_world_z_yaw_turns_qualified_in_source_model"])
    def test_back_forth_motion_path_not_two_turns(self):
        x=geometry(*track(oscillate=True))
        self.assertGreater(x["total_3d_rotation_travel_turns"],8)
        self.assertFalse(x["two_continuous_world_z_yaw_turns_qualified_in_source_model"])
    def test_wrong_rotation_axis_rejected(self):
        x=geometry(*track(axis="x"))
        self.assertFalse(x["two_continuous_world_z_yaw_turns_qualified_in_source_model"])
    def test_sampling_180_degree_alias_refused(self):
        x=geometry(*track(turns=12,samples=35))  # 127deg original step, genuinely > 90
        self.assertFalse(x["pose_sampling_admission"])
    def test_repeated_source_header_time_rejected(self):
        t,q,p=track()
        t[50]=t[49]
        with self.assertRaisesRegex(ValueError,"clock"):
            geometry(t,q,p)
    def test_quaternion_invalid_norm_rejected(self):
        t,q,p=track()
        q[30]*=2
        with self.assertRaisesRegex(ValueError,"nonunit"):
            geometry(t,q,p)
    def test_zip_member_parent_traversal_rejected(self):
        item=zipfile.ZipInfo("../evil.bag")
        item.file_size=100
        with self.assertRaisesRegex(ValueError,"unsafe"):
            validate_zip([item])
    def test_duplicate_archive_members_rejected(self):
        z1=zipfile.ZipInfo("bag/metadata.yaml")
        z2=zipfile.ZipInfo("bag/metadata.yaml")
        with self.assertRaisesRegex(ValueError,"duplicate"):
            validate_zip([z1,z2])
    def test_deposit_is_original_not_proof_of_external_gt(self):
        self.assertEqual(EXPECTED_NAME,"360.zip")
        self.assertEqual(PUBLISHED_MD5,"2b6eb3220c82ecab96dc8a4d918464ed")
if __name__=="__main__":
    unittest.main()
