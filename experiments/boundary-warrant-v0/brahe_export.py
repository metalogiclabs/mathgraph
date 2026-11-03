"""Independent read-only replay auditor for the pinned Brahe #608 Rust evidence.

This adapter recomputes log verdicts and source/transplant identities. It does
not claim customer-authorized requirements or live CI execution in this session.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import zipfile

from mathgraph_check.boundary_warrant import (
    BoundaryWarrant, Conclusion, Dependency, Obligation, Relation, Subject,
    Verification, required_dependencies, scope_identity,
)
from mathgraph_check.warrant_resolution import Receipt

ARTIFACT_SHA256 = "87c105ef5ab2c8880dbed6cbae78cfdb4c7bd680f23419cdb5776685b3cc914e"
ARTIFACT_ID = 13128365041
RUN_ID = 41415446440
SOURCE = {
    "repository": "duncaneddy/brahe",
    "baseSha": "323c4542ad915aa1b6a1dbf65f1f6a8040609294",
    "headSha": "f40f97da4094fddbd3745158f0123f9bcd0f3bd3",
    "baseBlobSha": "e161f52140cbcff04d0d7cbf0500b1c7cbd7dccf",
    "headBlobSha": "eb4172629778a63f874871629ddebc8fe0701858",
    "path": "src/events/detection.rs",
}
NEGATIVE = frozenset((
    "test_sscan_rejects_decreasing_detector_at_increasing_endpoint",
    "test_sscan_rejects_increasing_detector_at_decreasing_endpoint",
    "test_dscan_rejects_decreasing_detector_at_increasing_endpoint",
    "test_dscan_rejects_increasing_detector_at_decreasing_endpoint",
))
POSITIVE = frozenset((
    "test_sscan_accepts_direction_matching_endpoint",
    "test_sscan_accepts_any_direction_at_endpoint",
    "test_dscan_accepts_direction_matching_endpoint",
    "test_dscan_accepts_any_direction_at_endpoint",
    "test_bisection_search_time_event",
    "test_scan_for_event",
    "test_scan_for_event_backward",
    "test_step_reduction_factor_is_used",
    "test_bracket_termination",
    "test_event_near_bracket_boundary",
    "test_dscan_value_event_position_crossing",
    "test_dscan_value_event_no_crossing",
    "test_dscan_value_event_increasing_direction",
))
ASSERTIONS = (
    "assertion failed: !static_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)",
    "assertion failed: !static_endpoint_detected(2.0, 0.0, EventDirection::Increasing)",
    "assertion failed: !dynamic_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)",
    "assertion failed: !dynamic_endpoint_detected(2.0, 0.0, EventDirection::Increasing)",
)
MARKER = "#[cfg(test)]\nmod tests {"
BASE_GUARD = "if !crossed && current_crossing.abs() > detector.value_tolerance() {"
HEAD_GUARD = "let near_target_in_direction = current_crossing.abs() <= detector.value_tolerance()"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()


def verify_brahe_logs(stdout: str, stderr: str, exit_code: int, arm: str) -> dict:
    """Recompute the same exact 17-test verdict without accepting its receipt label."""
    combined = stdout + "\n" + stderr
    if (re.search(r"(?im)^error(?:\[[A-Z]\d+\])?:", combined.replace(
            "error: test failed, to rerun pass", "expected Cargo footer, to rerun pass"))
            or re.search(r"could not compile|failed to download|linking with .*failed",
                         combined, re.IGNORECASE)):
        raise ValueError("NATIVE_SETUP_FAILURE")
    if arm not in ("base", "head"):
        raise ValueError("INVALID_NATIVE_ARM")
    results = re.findall(
        r"(?m)^test events::detection::tests::([A-Za-z0-9_]+) \.\.\. (ok|FAILED)$",
        combined,
    )
    if (len(results) != 17 or len({name for name, _ in results}) != 17
            or {name for name, _ in results} != NEGATIVE | POSITIVE):
        raise ValueError("INCOMPLETE_NATIVE_REGRESSION")
    failures = {name for name, status in results if status == "FAILED"}
    if arm == "base":
        expected = (exit_code == 101 and failures == NEGATIVE
                    and "test result: FAILED. 13 passed; 4 failed;" in combined
                    and all(x in stderr for x in ASSERTIONS)
                    and all("thread 'events::detection::tests::" + x + "'" in stderr
                            for x in NEGATIVE))
    else:
        expected = (exit_code == 0 and not failures
                    and "test result: ok. 17 passed; 0 failed;" in combined)
    if not expected:
        raise ValueError("INCOMPLETE_NATIVE_REGRESSION")
    return {"tests": 17, "regressions": len(failures),
            "log_sha256": sha256(combined.encode())}


def export_brahe_boundary(
    artifact_zip: Path, base_source: Path, head_source: Path,
) -> tuple[BoundaryWarrant, Receipt, dict]:
    """Qualify only the exact historical Rust pair and its four negative controls."""
    if sha256(Path(artifact_zip).read_bytes()) != ARTIFACT_SHA256:
        raise ValueError("ARTIFACT_IDENTITY_MISMATCH")
    base, head = Path(base_source).read_bytes(), Path(head_source).read_bytes()
    if (git_blob_sha1(base) != SOURCE["baseBlobSha"]
            or git_blob_sha1(head) != SOURCE["headBlobSha"]):
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    b, h = base.decode("utf-8"), head.decode("utf-8")
    if (b.count(MARKER) != 1 or h.count(MARKER) != 1
            or b.split(MARKER)[0].count(BASE_GUARD) != 2
            or b.split(MARKER)[0].count(HEAD_GUARD) != 0
            or h.split(MARKER)[0].count(HEAD_GUARD) != 2
            or h.split(MARKER)[0].count(BASE_GUARD) != 0):
        raise ValueError("UNQUALIFIED_TRANSPLANT_BOUNDARY")
    transplant = (b.split(MARKER)[0] + MARKER + h.split(MARKER)[1]).encode("utf-8")
    with zipfile.ZipFile(artifact_zip) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("UNSAFE_ARTIFACT")
        def read(path):
            try:
                return archive.read(path)
            except KeyError as exc:
                raise ValueError("INCOMPLETE_ARTIFACT:" + path) from exc

        manifest_raw = read("brahe-transplant-manifest.json")
        manifest = json.loads(manifest_raw)
        if (manifest.get("source") != SOURCE
                or manifest.get("patchedSourceSha256") != sha256(transplant)
                or git_blob_sha1(transplant) != "b28c28e1c68b65b42da4bf25cfd9bbb6b3e6cb72"):
            raise ValueError("TRANSPLANT_IDENTITY_MISMATCH")
        native = json.loads(read("brahe-retrospective-receipt.json"))
        receipt = native.get("receipt", {})
        if (receipt.get("source") != {**SOURCE, "basePatchedBlobSha":git_blob_sha1(transplant)}
                or receipt.get("runner", {}).get("workflowRunUrl") !=
                    "https://github.com/metalogiclabs/mathgraph/actions/runs/" + str(RUN_ID)
                or native.get("verdict", {}).get("status") != "CANDIDATE_BOUNDED"
                or native.get("verdict", {}).get("authority") != "ADVISORY_ONLY"):
            raise ValueError("UNQUALIFIED_NATIVE_RECEIPT")
        if sha256(read("brahe-head/Cargo.lock")) != receipt["toolchain"]["cargoLockSha256"]:
            raise ValueError("RUST_DEPENDENCY_LOCK_CHANGED")
        outcomes = {}
        for arm, exit_code in (("base", 101), ("head", 0)):
            stdout, stderr = read("brahe-" + arm + ".stdout").decode(), read(
                "brahe-" + arm + ".stderr").decode()
            parsed = verify_brahe_logs(stdout, stderr, exit_code, arm)
            original = json.loads(read("brahe-" + arm + ".json"))
            if (original != receipt[arm] or original["sourceSha"] != SOURCE[arm + "Sha"]
                    or original["exitCode"] != exit_code
                    or original["testCount"] != parsed["tests"]
                    or original["regressionCount"] != parsed["regressions"]
                    or original["logSha256"] != parsed["log_sha256"]):
                raise ValueError("NATIVE_LOG_RECEIPT_MISMATCH")
            outcomes[arm] = parsed

    subject = Subject(SOURCE["repository"], SOURCE["headSha"], sha256(head))
    # Exact test module is the declared requirement. It is not an
    # independently signed customer/engineering specification.
    obligation = Obligation(
        "brahe.endpoint-direction",
        "Direction must agree with static/dynamic event crossing at tolerance endpoints",
        "PR_TEST_DECLARED; NOT_CUSTOMER_APPROVED",
        sha256((MARKER + h.split(MARKER)[1]).encode()),
    )
    relation = Relation(
        "event_consistency",
        "Both static and dynamic scan preserve increasing/decreasing/Any distinction",
        (("base_blob", SOURCE["baseBlobSha"]),
         ("head_blob", SOURCE["headBlobSha"]),
         ("negative_controls", "4"), ("total_tests", "17")),
    )
    verification = Verification(
        "native", receipt["toolchain"]["rustc"],
        sha256(manifest_raw), (),
        "brahe:run:" + str(RUN_ID) + ":artifact:" + str(ARTIFACT_ID),
    )
    warrant = BoundaryWarrant(
        subject, obligation, relation, verification,
        Conclusion("SUPPORTED", (
            "17 named Rust native event tests; 4 original wrong-direction failures",
            "source/receipt from public historical replay; no fresh Rust execution",
            "PR-authored obligation; no external owner approval or review superiority",
        )),
        required_dependencies(subject, obligation, relation, verification) + (
            Dependency("evidence", "brahe:retrospective-artifact", ARTIFACT_SHA256),
        ),
    )
    assessment = {
        "base_failures": outcomes["base"]["regressions"],
        "head_failures": outcomes["head"]["regressions"],
        "authority": "PR_TEST_DECLARED",
        "independent_owner_authority": "UNKNOWN",
        "replay": "RECHECKED_HISTORICAL_ARTIFACT",
    }
    return warrant, Receipt(verification.receipt_id, "native", scope_identity(warrant)), assessment
