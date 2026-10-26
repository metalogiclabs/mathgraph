"""Independent adverse source-native camera/gyro model tests (synthetic only)."""
import csv
import math
import tempfile
import unittest
from pathlib import Path
import numpy as np

from physical_source_native_joint import (
    Source, Truth, make_fixture, map_from_source, integrated,
    read_navigation_csv, past_only_gyro_phase,
    model_candidate_step, replay, grade, benchmark,
    BIAS, CLOCK, DRIFT, POPCOUNT, ANGULAR_BIN, TAU, SCENARIOS,
)

class Raw16BitJointTests(unittest.TestCase):
    def test_hidden_grader_never_enters_estimator(self):
        source,truth=make_fixture(0,"varying")
        baseline=replay(source)
        fake=Truth(truth.heading_rad+42.,999.,999.,999.)
        self.assertEqual(replay(source),baseline)
        self.assertNotEqual(grade(source,truth,baseline),grade(source,fake,baseline))

    def test_future_images_cannot_mutate_frozen_map(self):
        source,_=make_fixture(0,"varying")
        m=map_from_source(source)
        bits=source.camera_bits.copy()
        bits[m["frozen_at_camera_index"]+100]^=65535
        altered=Source(source.gyro_ns,source.gyro_rate,source.camera_ns,bits)
        n=map_from_source(altered)
        for key in ("signatures","present","quarantined"):
            self.assertTrue(np.array_equal(m[key],n[key]))

    def test_invalid_native_source_timestamps_and_bits_refuse(self):
        s,_=make_fixture(0,"varying")
        times=s.camera_ns.copy();times[3]=times[2]
        with self.assertRaisesRegex(ValueError,"nonmonotonic"):
            map_from_source(Source(s.gyro_ns,s.gyro_rate,times,s.camera_bits))
        bits=s.camera_bits.copy();bits[5]=65536
        with self.assertRaisesRegex(ValueError,"16-bit"):
            map_from_source(Source(s.gyro_ns,s.gyro_rate,s.camera_ns,bits))

    def test_causal_gyro_source_staleness_blocks_map(self):
        s,_=make_fixture(0,"varying")
        # Only 10% of the packets remain: many camera frames have no
        # gyro sample within the predeclared maximum causal age.
        thinned=Source(s.gyro_ns[::10],s.gyro_rate[::10],s.camera_ns,s.camera_bits)
        with self.assertRaisesRegex(ValueError,"stale gyro source"):
            map_from_source(thinned)

    def test_source_native_navigation_csv_roundtrip_without_encoder(self):
        source,_=make_fixture(0,"varying")
        with tempfile.TemporaryDirectory() as directory:
            camera_path=Path(directory)/"camera.csv"
            gyro_path=Path(directory)/"gyro.csv"
            with camera_path.open("w",newline="") as file:
                writer=csv.writer(file);writer.writerow(("timestamp_ns","bits16","usable"))
                writer.writerows((int(t),int(max(v,0)),int(v>=0))
                                 for t,v in zip(source.camera_ns,source.camera_bits))
            with gyro_path.open("w",newline="") as file:
                writer=csv.writer(file);writer.writerow(("timestamp_ns","gyro_z_rad_s"))
                writer.writerows((int(t),repr(float(w)))
                                 for t,w in zip(source.gyro_ns,source.gyro_rate))
            loaded=read_navigation_csv(camera_path,gyro_path)
            self.assertTrue(np.array_equal(loaded.camera_bits,source.camera_bits))
            self.assertTrue(np.array_equal(loaded.camera_ns,source.camera_ns))
            self.assertTrue(np.allclose(loaded.gyro_rate,source.gyro_rate))
            self.assertFalse(hasattr(loaded,"truth"))

    def test_minimum_clock_wait_refuses_instantaneous_decision(self):
        source,_=make_fixture(0,"varying")
        result=replay(source)
        for row in result["events"]:
            self.assertEqual(row["gyro_clock_decision_not_before_ns"]-row["timestamp_ns"],
                             40_000_000)
            self.assertFalse(row["navigation_correction_authorized"])
        self.assertTrue(result["retrospective_analysis_only"])

    def test_corrupted_columns_create_false_narrow_interval_without_sensitivity(self):
        source,truth=make_fixture(0,"outliers")
        weak=replay(source,robustness_budget=1)
        weak_grade=grade(source,truth,weak)
        self.assertGreater(weak_grade["model_narrow_frames"],0)
        self.assertGreater(weak_grade["false_model_narrow_frames_grader_only"],0)
        # Tightening apparent numerical certainty without testing outlier
        # sensitivity is a MODEL COUNTEREXAMPLE, not navigational authority.
        repaired=replay(source,robustness_budget=3)
        better=grade(source,truth,repaired)
        self.assertEqual(better["false_model_narrow_frames_grader_only"],0)
        self.assertEqual(better["model_narrow_frames"],0)
        self.assertTrue(any(e["model_state"]=="UNKNOWN_OUTLIER_SENSITIVITY"
                            for e in repaired["events"]))

    def test_same_source_zero_corrective_physical_authority(self):
        for name in SCENARIOS:
            s,_=make_fixture(0,name)
            r=replay(s)
            self.assertFalse(r["physical_navigation_authorized"])
            self.assertGreaterEqual(r["frozen_firstturn_bins"],16)
            self.assertTrue(all(e["navigation_correction_authorized"] is False
                                for e in r["events"]))
            self.assertGreater(len(r["camera_acquisition_indices"]),35)

    def test_steady_clock_offset_is_unidentifiable_from_relative_phase(self):
        s,_=make_fixture(0,"steady")
        m=map_from_source(s)
        v,_=model_candidate_step(s,m,m["frozen_at_camera_index"]+24)
        self.assertTrue(np.array_equal(v,np.broadcast_to(v[:1],v.shape)))

    def test_scalar_observation_oracle_independently_replays_grid_candidates(self):
        src,_=make_fixture(0,"varying")
        m=map_from_source(src)
        g=integrated(src)
        def scalar_causal_gyro(when_ns):
            k=int(np.searchsorted(src.gyro_ns,when_ns,side="right")-1)
            if k<0 or when_ns-src.gyro_ns[k]>20_000_000:
                raise ValueError("scalar stale gyro")
            return float(g[k]+src.gyro_rate[k]*(when_ns-src.gyro_ns[k])*1e-9)
        for idx in (96,132,204,312):
            valid,_=model_candidate_step(src,m,idx,jitter=1)
            t=(src.camera_ns[idx]-src.camera_ns[0])*1e-9
            observed=int(src.camera_bits[idx])
            for clock_i,bias_i,drift_i in ((0,0,0),(8,20,2),(16,40,4)):
                dt=float(CLOCK[clock_i])
                b=float(BIAS[bias_i]);d=float(DRIFT[drift_i])
                offset_ns=int(round(dt*1e9))
                theta=(scalar_causal_gyro(int(src.camera_ns[idx])+offset_ns)-
                       scalar_causal_gyro(int(src.camera_ns[0])+offset_ns)-
                       b*t-.5*d*t*t)
                center=int(math.floor((theta%TAU)/ANGULAR_BIN))%64
                cells=((center-1)%64,center,(center+1)%64)
                oracle=any(not m["present"][c] or
                           POPCOUNT[int(m["signatures"][c])^observed]<=2 for c in cells)
                self.assertEqual(bool(valid[clock_i,bias_i,drift_i]),oracle)

    def test_unqualified_finite_intervals_withhold_correction_despite_good_rmse(self):
        for case in ("steady","varying","clock_shift","drift","occlusion","alias"):
            source,truth=make_fixture(0,case)
            r=replay(source)
            metric=grade(source,truth,r)
            self.assertEqual(metric["model_narrow_fraction"],0.)
            self.assertLess(metric["mathgraph_diagnostic_rmse_deg"],
                            metric["gyro_rmse_deg"])
            self.assertFalse(metric["hardware_warrant"])

    def test_frozen_benchmark_retains_all_seven_model_conditions(self):
        report=benchmark(4)
        self.assertEqual(set(row["condition"] for row in report["scenarios"]),
                         set(SCENARIOS))
        self.assertFalse(report["real_sensors_tested"])
        self.assertFalse(report["physical_navigation_authorized"])
        for row in report["scenarios"]:
            self.assertEqual(row["trials"],4)
            self.assertEqual(row["mean"]["false_model_narrow_frames_grader_only"],0)
            self.assertEqual(row["mean"]["model_narrow_fraction"],0)

if __name__=="__main__":
    unittest.main()
