#!/usr/bin/env python3
"""Source-native JPL Open Source Rover kinematics qualification, bounded scope.

Runs unchanged upstream pytest tests and independent finite geometry observations,
then induces a single precisely specified local fault and demands that the SAME
original upstream test cases fail. Never edits or pushes the upstream checkout.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = "nasa-jpl/osr-rover-code"
PIN = "7aaf18512c9e8a997931f0caae28b63c8c6e9a78"
CODE = "ROS/osr_control/osr_control/kinematics.py"
TEST = "ROS/osr_control/test/test_kinematics.py"
CODE_BLOB = "38e35e5823111808177d78427a1595d27d0ebe00"
TEST_BLOB = "5860abcdd690f4c62f912e79ebfdd84d0817b4ae"
PROTECTED = "return math.copysign(limited, commanded_linear_x)"
MUTATION = "return commanded_linear_x"
TEST_PRIMARY = "test_body_speed_keeps_every_wheel_within_max_vel"
TEST_REVERSE = "test_body_speed_for_radius_clamps_reverse"
TEST_UNRELATED = "test_twist_to_radius_infinite_when_no_yaw"
SELECTOR = f"{TEST_PRIMARY} or {TEST_REVERSE}"

def run(cmd: list[str], name: str, folder: Path, *, env=None, timeout=240) -> dict:
    try:
        p = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace",
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=env, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"APPARATUS_TIMEOUT:{name}") from e
    (folder / (name + ".log")).write_text(p.stdout, encoding="utf-8")
    return {"exit": p.returncode,
            "log": name + ".log",
            "log_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(),
            "passed": p.returncode == 0}

def path_hash(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   text=True).strip()

def source_test_alignment(source: str, test: str) -> dict:
    mod = ast.parse(source)
    suite = ast.parse(test)
    klass = next((n for n in mod.body if isinstance(n, ast.ClassDef)
                 and n.name == "RoverKinematics"), None)
    if klass is None:
        raise RuntimeError("ROVER_KINEMATICS_CLASS_MISSING")
    fn = {n.name:n for n in klass.body if isinstance(n, ast.FunctionDef)}
    if not {"body_speed_for_radius", "calculate_drive_velocities"}.issubset(fn):
        raise RuntimeError("PRODUCTION_KINEMATICS_METHOD_MISSING")
    proof_source = ast.get_source_segment(source, fn["body_speed_for_radius"])
    if not proof_source or proof_source.count(PROTECTED) != 1:
        raise RuntimeError("SOURCE_GUARD_NOT_UNIQUE")
    tests = {n.name:n for n in suite.body if isinstance(n, ast.FunctionDef)}
    for n in [TEST_PRIMARY, TEST_REVERSE, TEST_UNRELATED]:
        if n not in tests:
            raise RuntimeError("AUTHOR_TEST_MISSING:" + n)
    required = ["body_speed_for_radius", "calculate_drive_velocities", "max_vel"]
    witness = ast.get_source_segment(test, tests[TEST_PRIMARY])
    if not witness or any(name not in witness for name in required):
        raise RuntimeError("PROTECTED_TEST_WITNESS_CHANGED")
    if "pytest.approx(kin.max_vel)" not in witness:
        raise RuntimeError("MAX_WHEEL_SPEED_ASSERTION_CHANGED")
    return {"production_method": "RoverKinematics.body_speed_for_radius",
            "consumer_method": "RoverKinematics.calculate_drive_velocities",
            "test_id": TEST_PRIMARY, "reverse_test_id":TEST_REVERSE,
            "unrelated_test_id":TEST_UNRELATED,
            "test_anchor_sha256": hashlib.sha256(witness.encode()).hexdigest(),
            "implementation_anchor_sha256": hashlib.sha256(proof_source.encode()).hexdigest()}

def finite_independent_oracle(root: Path) -> dict:
    """Finite *independent* geometry reading; not a formal universal proof.

    Imports source-native functions and calculates a separate scalar bound based
    on geometry and the same documented wheel model. Bounded valid turning
    radii and finite commanded speeds only; no physical motor tests.
    """
    sys.path.insert(0, str((root / "ROS/osr_control").resolve()))
    from osr_control.kinematics import RoverDimensions, RoverKinematics
    dims = RoverDimensions(0.177, 0.310, 0.274, 0.253, 0.075)
    rover = RoverKinematics(dims, drive_no_load_rpm=223.0)
    radii = (-6.39, -3.0, -1.0, -0.6, -0.45, 0.45, 0.6, 1.0, 3.0, 6.39)
    speeds = (-10.0, -1.0, -0.4, 0.0, 0.4, 1.0, 10.0)
    checks = []
    for radius in radii:
        r = abs(radius)
        outer_radius = max(math.hypot(r + dims.d1, dims.d3), r + dims.d4)
        independent_limit = r / outer_radius * rover.max_vel
        for speed in speeds:
            actual = rover.body_speed_for_radius(speed, radius)
            ideal = math.copysign(min(abs(speed), independent_limit), speed)
            if speed == 0.0:
                ideal = 0.0
            if not math.isclose(actual, ideal, abs_tol=1e-10, rel_tol=1e-10):
                raise RuntimeError(f"BOUNDED_BODY_CLAMP_DISAGREEMENT:{radius}:{speed}")
            wheel = rover.calculate_drive_velocities(actual, radius)
            outer_speed = max(abs(v) for v in vars(wheel).values()) * dims.wheel_radius
            if not math.isfinite(outer_speed) or outer_speed > rover.max_vel + 1e-10:
                raise RuntimeError(f"BOUNDED_WHEEL_SPEED_EXCEEDED:{radius}:{speed}:{outer_speed}")
            checks.append({"radius":radius,"commanded":speed,
                           "limited":actual,"max_wheel":outer_speed})
    digest = hashlib.sha256(json.dumps(checks, sort_keys=True,
                                        separators=(",",":")).encode()).hexdigest()
    return {"status":"PASS_BOUNDED", "cases":len(checks),
            "radii":list(radii), "commanded_speeds":list(speeds),
            "grid_sha256":digest,
            "measurements":checks,
            "max_vel_mps":rover.max_vel,
            "claimed_universal_proof":False,
            "scope":"valid finite nonzero turning radii, exact authored rover dimensions and rpm"}

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: execute.py PINNED_OSR_CHECKOUT EVIDENCE_DIRECTORY")
    root, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if git(root,"rev-parse","HEAD") != PIN:
        raise SystemExit("FAIL_CLOSED_SOURCE_REVISION")
    if git(root,"rev-parse","HEAD:"+CODE) != CODE_BLOB or \
       git(root,"rev-parse","HEAD:"+TEST) != TEST_BLOB:
        raise SystemExit("FAIL_CLOSED_SOURCE_OR_TEST_BLOB")
    if git(root,"status","--porcelain"):
        raise SystemExit("UPSTREAM_CHECKOUT_NOT_CLEAN")

    implementation = (root/CODE).read_text()
    authored_tests = (root/TEST).read_text()
    alignment = source_test_alignment(implementation,authored_tests)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "ROS/osr_control")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    testfile = str(root/TEST)
    baseline = run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider",
                    testfile], "upstream-authored-tests", output, env=env)
    if baseline["exit"] != 0:
        raise RuntimeError("NATIVE_AUTHOR_TESTS_NOT_GREEN")
    selected = run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider",
                    testfile,"-k",SELECTOR], "original-protected-test", output, env=env)
    if selected["exit"] != 0:
        raise RuntimeError("AUTHORED_PROTECTED_TEST_NOT_GREEN")
    oracle=finite_independent_oracle(root)

    mutant = output / "mutant"
    package = mutant / "osr_control"
    package.mkdir(parents=True, exist_ok=True)
    (package/"__init__.py").write_text("")
    if implementation.count(PROTECTED) != 1:
        raise RuntimeError("MUTANT_SITE_NOT_UNIQUE")
    modified = implementation.replace(PROTECTED, MUTATION, 1)
    (package/"kinematics.py").write_text(modified)
    (output/"mutation.diff.txt").write_text(
        f"- {PROTECTED}\n+ {MUTATION}\n")
    altered_env = os.environ.copy()
    altered_env["PYTHONPATH"] = str(mutant)
    altered_env["PYTHONDONTWRITEBYTECODE"] = "1"
    mutant_result = run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider",
                         testfile,"-k",SELECTOR], "mutation-protected-test",
                         output, env=altered_env)
    mutant_log = (output/"mutation-protected-test.log").read_text()
    if mutant_result["exit"] == 0 or TEST_PRIMARY not in mutant_log or \
       "FAILED" not in mutant_log:
        raise RuntimeError("INDUCED_FAULT_NOT_REJECTED_BY_AUTHORED_TEST")
    if git(root,"status","--porcelain"):
        raise RuntimeError("ORIGINAL_OSR_CHECKOUT_MUTATED")
    report={
      "protocol":"MATHGRAPH_AUTONOMOUS_CLAIM_TRANSFER_V1",
      "external_repository":REPO, "source_sha":PIN,
      "source_blob_git":CODE_BLOB, "test_blob_git":TEST_BLOB,
      "source_sha256":path_hash(root,CODE),
      "test_sha256":path_hash(root,TEST),
      "author_encoded_requirement":
        "body speed limited so each commanded drive wheel stays within max_vel",
      "requirement_authority":"AUTHOR_SOURCE_DOCSTRING_AND_TEST_NOT_MISSION_CERTIFICATION",
      "source_test_alignment":alignment,
      "real_author_test_run":baseline,
      "protected_author_test_run":selected,
      "finite_independent_geometry_oracle":oracle,
      "induced_local_mutation":{
          **mutant_result,"mutation":"return math.copysign(limited, commanded_linear_x) => return commanded_linear_x",
          "original_protected_case_failed":True},
      "baseline_name":"full original unmodified pytest suite",
      "baseline_limitation":"test runner itself does not authorize unrelated claims or mission certification",
      "runtime_motor_evidence":False,
      "flight_qualified":False, "NASA_ENDORSEMENT":False
    }
    (output/"native-observation.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("OSR_SOURCE_NATIVE_TESTS_AND_INDUCED_FAULT_PASS",
          json.dumps({"tests":"AUTHOR_NATIVE_GREEN","bounded_grid":oracle["cases"],
                      "mutant":"AUTHOR_TEST_REJECTED","pin":PIN},sort_keys=True))
if __name__ == "__main__":
    main()
