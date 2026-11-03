"""Exact-pinned Nyx native two-arm replay, not an external requirement oracle."""
from __future__ import annotations

import hashlib
import re

TEST_MARKER = "// Longitude changes when the observer axes rotate; unlike latitude, it\n"
LATITUDE_ANCHOR = "#[rstest]\nfn latitude(almanac: Arc<Almanac>)"
TEST_NAME = "longitude_event_in_rotating_frame"


def transplant_exact_regression(base_source: str, head_source: str) -> str:
    """Import only the head's verified frame test; leave base production intact."""
    if TEST_NAME in base_source:
        raise ValueError("TEST_ALREADY_PRESENT")
    if (base_source.count(LATITUDE_ANCHOR) != 1
            or head_source.count(LATITUDE_ANCHOR) != 1
            or head_source.count(TEST_MARKER) != 1
            or head_source.count("fn " + TEST_NAME) != 1):
        raise ValueError("BAD_TEST_ANCHOR")
    beginning = head_source.index(TEST_MARKER)
    end = head_source.index(LATITUDE_ANCHOR, beginning)
    block = head_source[beginning:end]
    if not all(token in block for token in (
        "IAU_EARTH_FRAME", "transform_to(",
        "residual_deg.abs() < 1e-3", "inertial_residual_deg.abs() > 1.0",
    )):
        raise ValueError("NEGATIVE_FRAME_CONTROL_MISSING")
    return base_source.replace(LATITUDE_ANCHOR, block + LATITUDE_ANCHOR, 1)


def classify_native_test(stdout: str, stderr: str, exit_code: int, arm: str,
                         expected_target: str | None = None) -> dict:
    """Recognize one actual native test, separating a regression from setup failure."""
    if arm not in ("base", "head"):
        raise ValueError("INVALID_ARM")
    combined = stdout + "\n" + stderr
    no_cargo_footer = combined.replace("error: test failed, to rerun pass", "expected test footer")
    if (exit_code in (124, 125, 126, 127, 137)
            or re.search(r"(?im)^error(?:\[[A-Z]\d+\])?:", no_cargo_footer)
            or re.search(r"could not compile|failed to download|linking with .*failed|timed out",
                         combined, re.IGNORECASE)
            or "file cannot be inspected or loaded directly in ANISE" in combined):
        raise ValueError("NATIVE_SETUP_FAILURE")
    if expected_target is not None:
        running = re.findall(r"(?m)^\s*Running tests/lib\.rs \(([^\n]*)\)$", stderr)
        if (len(running) != 1 or
                f"/{expected_target}/debug/deps/" not in running[0]):
            raise ValueError("BUILD_IDENTITY_MISMATCH")
    matches = re.findall(
        r"(?m)^test (\S*" + TEST_NAME + r"\S*) \.\.\. (ok|FAILED)$", combined,
    )
    if (len(matches) != 1 or combined.count("running 1 test") != 1
            or not matches[0][0].startswith("propagation::stopcond::")):
        raise ValueError("INCOMPLETE_NATIVE_TEST")
    name, status = matches[0]
    if arm == "base":
        if not (exit_code == 101 and status == "FAILED"
                and "test result: FAILED. 0 passed; 1 failed;" in combined
                and "Earth-fixed longitude zero must be found in the requested event frame" in combined
                and "EventNotFound" in combined):
            raise ValueError("WRONG_BASELINE_FAILURE")
    elif not (exit_code == 0 and status == "ok"
              and "test result: ok. 1 passed; 0 failed;" in combined):
        raise ValueError("WRONG_HEAD_RESULT")
    return {"tests": 1, "passed": int(status == "ok"),
            "failed": int(status == "FAILED"), "name": name,
            "log_sha256": hashlib.sha256(combined.encode()).hexdigest()}
