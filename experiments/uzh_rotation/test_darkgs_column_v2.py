import io,unittest
import numpy as np
from PIL import Image
from darkgs_column_v2 import extract_column,pairs,firstturn

def observation(stripes):
    a=np.vstack([np.full((10,20),b,dtype=np.uint8) for b in stripes])
    f=io.BytesIO()
    Image.fromarray(a).save(f,format="PNG")
    return extract_column(f.getvalue())

class ColumnTest(unittest.TestCase):
    def test_uniform_brightness_cannot_authenticate_a_pattern(self):
        d=observation([200]*16)
        self.assertFalse(d["usable"])
        self.assertEqual(d["absolute"],65535)
    def test_relative_pattern_is_illumination_offset_invariant(self):
        base=[30 if i%2 else 180 for i in range(16)]
        a=observation(base)
        b=observation([x+12 for x in base])
        self.assertTrue(a["usable"])
        self.assertEqual(a["bits"],b["bits"])
    def test_identical_fingerprints_are_pairwise_uninformative(self):
        a=observation([30 if i%2 else 180 for i in range(16)])
        p=pairs({0:a,1:a,2:a})
        self.assertEqual(p["duplicate_binary_pairs"],3)
        self.assertEqual(p["pairwise_binary_witness_if_observation_error_le_2bits"],0)
    def test_zero_error_causal_firstturn_cannot_authorize(self):
        t=np.arange(1600,dtype=np.int64)*10000000
        d=observation([30 if i%2 else 180 for i in range(16)])
        frames=[(int(t[i]),d) for i in range(1,1500,20)]
        r=firstturn(t,np.ones(len(t)),frames)
        self.assertTrue(r["source_model_first_turn_complete"])
        self.assertFalse(r["navigation_correction_authorized"])
    def test_source_header_outlier_detected_without_silent_deletion(self):
        t=np.arange(1600,dtype=np.int64)*10000000
        d=observation([30 if i%2 else 180 for i in range(16)])
        frames=[(-500_000_000_000,d)]+[(int(t[i]),d) for i in range(1,1500,20)]
        r=firstturn(t,np.ones(len(t)),frames)
        self.assertEqual(r["camera_imu_clock_status"],"UNKNOWN_SOURCE_TIME_GAP_OR_DOMAIN")
        self.assertEqual(r["source_frames_outside_gyro_domain"],1)
    def test_invalid_header_timestamp_rejected(self):
        t=np.arange(1600,dtype=np.int64)*10000000
        d=observation([30 if i%2 else 180 for i in range(16)])
        frames=[(int(t[i]),d) for i in range(1,1500,20)]
        frames[15]=(frames[14][0],d)
        with self.assertRaisesRegex(ValueError,"chronological"):
            firstturn(t,np.ones(len(t)),frames)
if __name__=="__main__":
    unittest.main()
