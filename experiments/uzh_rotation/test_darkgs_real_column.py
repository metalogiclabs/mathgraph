import io,unittest
import numpy as np
from PIL import Image
from darkgs_camera_gyro_firstturn import (
    original_color_column_descriptor,causal_phase_at,
    running_causal_gyro_integral,inspect_observations,
)

def jpeg_column(signal):
    a=np.full((160,120),signal,dtype=np.uint8)
    image=Image.fromarray(a)
    out=io.BytesIO()
    image.save(out,format="PNG")
    return out.getvalue()

class RealColumnControls(unittest.TestCase):
    def test_original_gray_synthetic_bright_dark(self):
        a,d=original_color_column_descriptor(jpeg_column(255))
        b,_=original_color_column_descriptor(jpeg_column(0))
        self.assertEqual(d,(120,160,60))
        self.assertEqual(a,65535)
        self.assertEqual(b,0)
    def test_invalid_binary_image_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid source"):
            original_color_column_descriptor(b"not an image")
    def test_causal_phase_does_not_consult_future_gyro(self):
        t=np.arange(20,dtype=np.int64)*100000000
        w=np.ones(20)
        integ=running_causal_gyro_integral(t,w)
        before=causal_phase_at(400000000,t,w,integ)
        w[6:]=100
        future=running_causal_gyro_integral(t,w)
        after=causal_phase_at(400000000,t,w,future)
        self.assertAlmostEqual(before,after)
        self.assertAlmostEqual(before,.4)
    def test_duplicate_gyro_source_header_refused(self):
        t=np.arange(20,dtype=np.int64)
        t[10]=t[9]
        with self.assertRaisesRegex(ValueError,"strictly"):
            running_causal_gyro_integral(t,np.ones(20))
    def test_unshared_camera_gyro_clocks_cannot_make_map(self):
        t=np.arange(200,dtype=np.int64)*10_000_000
        f=[(int(1e12+i*10_000_000),0,(120,160,60)) for i in range(100)]
        out=inspect_observations(t,np.ones(200),f)
        self.assertEqual(out["state"],"UNKNOWN_DISJOINT_SOURCE_CLOCK_DOMAINS")
        self.assertFalse(out["navigation_correction_authorized"])
    def test_true_synthetic_first_full_turn_never_authorizes(self):
        n=2000
        t=np.arange(n,dtype=np.int64)*10_000_000
        w=np.ones(n)
        frames=[(int(t[i]),i%2,(120,160,60)) for i in range(1,n,15)]
        out=inspect_observations(t,w,frames)
        self.assertEqual(out["state"],"DIAGNOSTIC_SOURCE_GYRO_COMPLETE_TURN")
        self.assertGreater(out["diagnostic_nominal_64bin_coverage"],20)
        self.assertFalse(out["navigation_correction_authorized"])
        self.assertFalse(out["warranted_embedded_firstturn_reference"])
    def test_one_complete_turn_withheld_if_gyro_not_reaching_360(self):
        n=1000
        t=np.arange(n,dtype=np.int64)*10_000_000
        frames=[(int(t[i]),i%2,(120,160,60)) for i in range(1,n,11)]
        out=inspect_observations(t,np.ones(n)*.2,frames)
        self.assertEqual(out["state"],"DIAGNOSTIC_PARTIAL_SOURCE_GYRO_TURN")
        self.assertFalse(out["navigation_correction_authorized"])
if __name__=="__main__":
    unittest.main()
