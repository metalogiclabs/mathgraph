"""Fail-closed finite evidence gate; standard library only."""
from dataclasses import dataclass
import hashlib
from pathlib import Path

@dataclass(frozen=True)
class Evidence:
    expected_revision: str
    observed_revision: str | None
    expected_artifact_sha256: str
    artifact: bytes | None
    tests_passed: bool | None

def decide(e: Evidence) -> tuple[str, str]:
    if e.observed_revision is None or e.artifact is None or e.tests_passed is None:
        return "UNKNOWN", "required evidence missing"
    if e.observed_revision != e.expected_revision:
        return "REJECTED", "source revision mismatch"
    if hashlib.sha256(e.artifact).hexdigest() != e.expected_artifact_sha256:
        return "REJECTED", "artifact digest mismatch"
    if not e.tests_passed:
        return "REJECTED", "required tests failed"
    return "WARRANTED", "all declared finite checks passed"

def demo():
    blob = b"verified-build"
    sha = hashlib.sha256(blob).hexdigest()
    base = dict(expected_revision="abc123", expected_artifact_sha256=sha)
    cases = [
        Evidence(**base, observed_revision="abc123", artifact=blob, tests_passed=True),
        Evidence(**base, observed_revision="def456", artifact=blob, tests_passed=True),
        Evidence(**base, observed_revision="abc123", artifact=None, tests_passed=True),
        Evidence(**base, observed_revision="abc123", artifact=b"tampered", tests_passed=True),
    ]
    expected = ["WARRANTED", "REJECTED", "UNKNOWN", "REJECTED"]
    for e, want in zip(cases, expected):
        result, reason = decide(e)
        assert result == want, (result, want)
        print(f"{result}: {reason}")

if __name__ == "__main__":
    demo()
