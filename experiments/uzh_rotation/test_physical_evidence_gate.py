"""Adversarial five-revolution gate tests.

Fixture physics exist only to test auditor and referee implementation.
They are NEVER a measured flight demonstration or a source of performance
thresholds. Source roles are stored in disjoint temporary directories.
"""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from physical_evidence_gate import (
    VERSION,inspect,check_manifest,map_digest,fail,
)
from physical_encoder_score import score

T0=10_000_000_000
SEC=1_000_000_000
CPR=1024
OMEGA=2*math.pi


def dump(path,obj):
    Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")


def jl(path,rows):
    Path(path).write_text("".join(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n"
                               for row in rows))


def add_manifest(folder,role,mode,files,**extras):
    content={"schema":VERSION,"role":role,"mode":mode,
             "capture_id":"demo_capture_0001",
             "files":{name:{"sha256":hashlib.sha256((folder/name).read_bytes()).hexdigest(),
                             "bytes":(folder/name).stat().st_size}
                      for name in files}}
    content.update(extras)
    dump(folder/("nav_manifest.json" if role=="NAVIGATION" else "encoder_manifest.json"),
         content)


def make_fixture(root,mode="FIXTURE",with_encoder=True):
    nav=root/"navigation";enc=root/"encoder"
    nav.mkdir();enc.mkdir()
    sensor=[]
    def gy(ts):
        sensor.append({"kind":"GYRO","t_ns":ts,"omega_rad_s":OMEGA})
    def cam(ts,reading,status="OK"):
        sensor.append({"kind":"COLUMN","t_ns":ts,"status":status,
                       "column_u16":reading})
    gy(T0)
    seen={7:0xAAA8,8:0xAAAA,9:0xAAA9,15:0x5550,16:0x5555,17:0x5551}
    for index,word in seen.items():
        ts=T0+round((index+.5)/64*SEC)
        cam(ts,word)
    for turn in range(1,7):gy(T0+turn*SEC)
    cam(T0+SEC+150_000_000,0xAAAA)
    cam(T0+2*SEC+250_000_000,None,"OCCLUDED")
    sensor.sort(key=lambda r:r["t_ns"])
    for i,row in enumerate(sensor):row["seq"]=i
    jl(nav/"sensors.jsonl",sensor)
    by_t={x["t_ns"]:x for x in sensor}
    decisions=[]
    def push(t,kind,**kwargs):
        if kind=="ESTIMATE":
            # Fixture-only independent conventional vision+gyro comparator
            # recorded on the same source timeline; not a physical claim.
            kwargs["conventional_visual_heading_rad"]=OMEGA*((t-T0)/SEC)*.985
        decisions.append({"t_ns":t,"kind":kind,**kwargs})
    for idx,val in seen.items():
        t=T0+round((idx+.5)/64*SEC)
        push(t+1,"MAP_CAPTURE",camera_seq=by_t[t]["seq"],
             phase_u16=idx*1024+512,radius_u16=20,disposition="ACCEPTED")
    push(T0+500_000_000,"ESTIMATE",fused_heading_rad=OMEGA*.5,
         correction_delta_rad=0.,authority="UNKNOWN",support_camera_seq=None)
    push(T0+SEC+1,"FREEZE",map_sha256=map_digest(seen,set()))
    push(T0+SEC+50_000_000,"REQUEST",hypotheses=[8,16],step_bins=0,
         witness_predicted=True)
    # For this demonstration the active request explicitly links to a
    # later actual camera sample, not a predicted measurement.
    push(T0+SEC+150_000_001,"MATCH",
         camera_seq=by_t[T0+SEC+150_000_000]["seq"],
         before=[8,16],after=[8],step_bins=0,request_seq=8)
    push(T0+SEC+160_000_000,"ESTIMATE",
         fused_heading_rad=OMEGA*1.16*.95,
         correction_delta_rad=-.1,authority="WARRANTED",
         support_camera_seq=by_t[T0+SEC+150_000_000]["seq"])
    push(T0+2*SEC+250_000_001,"WITHDRAW",reason="OCCLUSION")
    for turn in [2,3,4,5]:
        t=T0+turn*SEC+260_000_000
        push(t,"ESTIMATE",fused_heading_rad=OMEGA*(turn+.26)*.95,
             correction_delta_rad=0.,authority="UNKNOWN",support_camera_seq=None)
    decisions.sort(key=lambda x:x["t_ns"])
    for i,row in enumerate(decisions):row["seq"]=i
    jl(nav/"decisions.jsonl",decisions)
    witnesses=[{"camera_ns":T0-2*SEC+i*100_000_000,
                "gyro_ns":T0-2*SEC+i*100_000_000} for i in range(6)]
    timing={
        "capture_id":"demo_capture_0001",
        "source":"independent_reference_pulses",
        "independent_reference":True,
        "nominal_skew_ns":0,
        "error_bound_ns":100_000,
        "witness_pairs":witnesses,
        "calibrated_before_ns":T0-100_000_000,
        "valid_through_ns":T0+8*SEC,
        "max_gyro_rad_s":7.,
        "integration_error_rad":0.,
    }
    dump(nav/"timing.json",timing)
    add_manifest(nav,"NAVIGATION",mode,
                 ("sensors.jsonl","decisions.jsonl","timing.json"),
                 conventional_visual_baseline={
                     "name":"identical_source_conventional_visual_gyro_fixture",
                     "source_sensor_sha256":hashlib.sha256((nav/"sensors.jsonl").read_bytes()).hexdigest(),
                     "source_code_sha256":"f"*64,
                     "no_encoder_input":True,
                     "frozen_before_capture":True})
    if with_encoder:
        rows=[]
        for i in range(61):
            t=T0+i*100_000_000
            ticks=round(i*.1*.95*CPR)
            rows.append({"seq":i,"t_ns":t,"ticks_unwrapped":ticks})
        jl(enc/"encoder.jsonl",rows)
        pulse={"offset_ns":0,"bound_ns":100_000,
               "independent_reference":True,"source":"independent_reference_pulses",
               "max_interpolation_gap_ns":150_000_000,
               "pulse_pairs":[{"encoder_ns":T0-2*SEC+i*100_000_000,
                               "navigation_ns":T0-2*SEC+i*100_000_000}
                              for i in range(6)]}
        add_manifest(enc,"ENCODER",mode,("encoder.jsonl",),
                     counts_per_revolution=CPR,
                     navigation_manifest_sha256=hashlib.sha256(
                         (nav/"nav_manifest.json").read_bytes()).hexdigest(),
                     encoder_to_navigation_clock=pulse)
    return nav,enc


def rewrite_nav(nav,filename,rows=None,edit=None):
    p=nav/filename
    if rows is not None:jl(p,rows)
    elif edit is not None:
        obj=json.loads(p.read_text());edit(obj);dump(p,obj)
    m=json.loads((nav/"nav_manifest.json").read_text())
    m["files"][filename]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                          "bytes":p.stat().st_size}
    if filename=="sensors.jsonl":
        # This test must keep the independent comparator's declared
        # identical-input digest synchronized, so timestamp corruption is
        # reached and rejected by the SOURCE CLOCK gate itself.
        m["conventional_visual_baseline"]["source_sensor_sha256"]=m["files"][filename]["sha256"]
    dump(nav/"nav_manifest.json",m)


class PhysicalEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="mg-physical-protocol-")
        self.nav,self.encoder=make_fixture(Path(self.tmp.name))
    def tearDown(self):self.tmp.cleanup()

    def test_complete_demo_remains_fixture_only_with_independent_score(self):
        audit=inspect(self.nav)
        self.assertTrue(audit["policy_consistent_with_declared_finite_model"])
        self.assertEqual(audit["role_isolation"],"NAVIGATION_ONLY_NO_ENCODER_BYTES")
        self.assertGreater(audit["firstturn_map_bins"],0)
        self.assertEqual(audit["statistics"]["warranted_estimates"],1)
        self.assertEqual(audit["statistics"]["requests_acquired"],1)
        self.assertGreater(audit["statistics"]["occluded_columns"],0)
        self.assertFalse(audit["physical_visual_heading_accuracy_verified"])
        path=Path(self.tmp.name)/"nav_audit.json"
        dump(path,audit)
        result=score(path,self.encoder)
        self.assertEqual(result["physical_acceptance"],"FIXTURE_ONLY_NOT_PHYSICAL_VALIDATION")
        self.assertGreater(result["recorded_total_optical_turns"],5)
        self.assertTrue(result["revolutions_indexed_from_encoder_capture_start"])
        self.assertAlmostEqual(result["encoder_turns_at_source_firstturn_freeze"],.95,delta=.002)
        self.assertFalse(result["acceptance_tests"]["first_turn_freeze_not_early_or_in_later_turns"])
        self.assertTrue(result["observed_improvement_over_gyro_only"])
        self.assertIsNotNone(result["conventional_visual_rmse_unwrapped_deg"])
        self.assertTrue(result["acceptance_tests"]["same_sensor_conventional_visual_baseline_scored"])
        self.assertFalse(result["acceptance_tests"]["baseline_binary_and_equal_data_execution_independently_attested"])
        self.assertGreater(result["per_revolution"]["2"]["samples"],0)
        self.assertGreater(result["per_revolution"]["5"]["samples"],0)
        self.assertFalse(result["acceptance_tests"]["timing_bound_independently_physically_certified"])
    def test_ambiguous_landmarks_remain_candidate_support(self):
        from physical_evidence_gate import allowed_after,separates_pair
        repeat={k:0xAAAA for k in (7,8,9,15,16,17)}
        self.assertEqual(allowed_after([8,16],0,0xAAAA,repeat),[8,16])
        self.assertFalse(separates_pair(8,16,0,repeat))

    def test_firstturn_phase_cannot_be_forged_from_oracle(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        event=next(x for x in rows if x["kind"]=="MAP_CAPTURE")
        event["phase_u16"]=(event["phase_u16"]+2048)%65536
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"disagrees with causal gyro"):
            inspect(self.nav)

    def test_conventional_baseline_cannot_claim_different_camera_gyro_source(self):
        meta=json.loads((self.nav/"nav_manifest.json").read_text())
        meta["conventional_visual_baseline"]["source_sensor_sha256"]="0"*64
        dump(self.nav/"nav_manifest.json",meta)
        with self.assertRaisesRegex(ValueError,"not pinned to identical sensor"):
            inspect(self.nav)

    def test_missing_conventional_visual_output_is_fail_closed(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        estimate=next(x for x in rows if x["kind"]=="ESTIMATE")
        del estimate["conventional_visual_heading_rad"]
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"invalid heading estimate"):
            inspect(self.nav)

    def test_navigation_bundle_rejects_encoder_present(self):
        (self.nav/"encoder.jsonl").write_text("truth\n")
        with self.assertRaisesRegex(ValueError,"leaked"):
            inspect(self.nav)
    def test_mutated_gyro_byte_breaks_immutable_manifest(self):
        with (self.nav/"sensors.jsonl").open("a") as stream:
            stream.write("{}\n")
        with self.assertRaisesRegex(ValueError,"digest or size"):
            inspect(self.nav)
    def test_unknown_correction_blocked(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        x=next(v for v in rows if v["kind"]=="ESTIMATE" and v["authority"]=="UNKNOWN")
        x["correction_delta_rad"]=0.4
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"UNKNOWN estimate"):
            inspect(self.nav)
    def test_occlusion_with_stale_support_does_not_authorize(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        early=next(x for x in rows if x["kind"]=="ESTIMATE" and x["authority"]=="WARRANTED")
        late=next(x for x in rows if x["kind"]=="ESTIMATE" and x["t_ns"]>T0+2*SEC)
        late["authority"]="WARRANTED"
        late["support_camera_seq"]=early["support_camera_seq"]
        late["correction_delta_rad"]=.1
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"unsupported"):
            inspect(self.nav)
    def test_decision_after_capture_future_camera_rejected(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        match=next(x for x in rows if x["kind"]=="MATCH")
        match["camera_seq"]=99999
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"causal camera"):
            inspect(self.nav)
    def test_candidate_elimination_must_match_independent_hamming_replay(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        match=next(x for x in rows if x["kind"]=="MATCH")
        match["after"]=[16]
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"cannot justify"):
            inspect(self.nav)
    def test_certified_clock_bound_cannot_conflict_with_pulses(self):
        def corrupt(x):x["witness_pairs"][2]["camera_ns"]+=1_000_000
        rewrite_nav(self.nav,"timing.json",edit=corrupt)
        with self.assertRaisesRegex(ValueError,"contradicted"):
            inspect(self.nav)
    def test_rewrite_firstturn_map_after_freeze_is_refused(self):
        rows=[json.loads(x) for x in (self.nav/"decisions.jsonl").read_text().splitlines()]
        next_freeze=next(i for i,v in enumerate(rows) if v["kind"]=="FREEZE")
        element=next(v.copy() for v in rows if v["kind"]=="MAP_CAPTURE")
        element["t_ns"]=rows[next_freeze]["t_ns"]+1
        rows.insert(next_freeze+1,element)
        rows.sort(key=lambda x:x["t_ns"])
        for i,v in enumerate(rows):v["seq"]=i
        rewrite_nav(self.nav,"decisions.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"after first-turn freeze"):
            inspect(self.nav)
    def test_sensor_clock_duplicate_rejected_even_if_manifest_rehashed(self):
        rows=[json.loads(x) for x in (self.nav/"sensors.jsonl").read_text().splitlines()]
        rows[2]["t_ns"]=rows[1]["t_ns"]
        rewrite_nav(self.nav,"sensors.jsonl",rows=rows)
        with self.assertRaisesRegex(ValueError,"non-strict"):
            inspect(self.nav)
    def test_encoder_is_not_interpolated_across_unbounded_gaps(self):
        audit=inspect(self.nav)
        path=Path(self.tmp.name)/"nav_audit.json";dump(path,audit)
        rows=[json.loads(x) for x in (self.encoder/"encoder.jsonl").read_text().splitlines()]
        # Remove the majority of the reference source, relabel and rehash
        # only in the test harness; no real data is created by this fixture.
        rows=rows[:15]+rows[55:]
        for i,r in enumerate(rows):r["seq"]=i
        jl(self.encoder/"encoder.jsonl",rows)
        meta=json.loads((self.encoder/"encoder_manifest.json").read_text())
        raw=(self.encoder/"encoder.jsonl").read_bytes()
        meta["files"]["encoder.jsonl"]={"sha256":hashlib.sha256(raw).hexdigest(),
                                         "bytes":len(raw)}
        dump(self.encoder/"encoder_manifest.json",meta)
        report=score(path,self.encoder)
        self.assertGreater(report["encoder_interpolation_missing_samples"],0)
        self.assertFalse(report["acceptance_tests"]["all_navigator_estimates_have_bracketed_encoder_truth"])
        self.assertEqual(report["physical_acceptance"],"FIXTURE_ONLY_NOT_PHYSICAL_VALIDATION")
    def test_empty_encoder_source_cannot_be_a_five_turn_success(self):
        audit=inspect(self.nav);path=Path(self.tmp.name)/"nav_audit.json";dump(path,audit)
        self.assertFalse(audit["physical_visual_heading_accuracy_verified"])
        with (self.encoder/"encoder.jsonl").open("a") as f:f.write("{}\n")
        with self.assertRaisesRegex(ValueError,"digest or size"):
            score(path,self.encoder)


if __name__=="__main__":
    unittest.main()
