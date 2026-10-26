#!/usr/bin/env python3
"""Independent finite evidence verifier for an exposed native pytest execution.

It NEVER launches arbitrary source commands or assumes a passing suite is the
author's complete test contract. No protected sources are read by this module.
"""
from __future__ import annotations
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceObstruction(ValueError):
    pass


def exact_case_ids(xml: bytes) -> dict:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise EvidenceObstruction("UNKNOWN_INVALID_JUNIT") from None
    if root.tag not in ("testsuites", "testsuite"):
        raise EvidenceObstruction("UNKNOWN_INVALID_JUNIT_ROOT")
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    leaves = [s for s in suites if not list(s.iter("testsuite"))[1:]]
    if not leaves:
        raise EvidenceObstruction("UNKNOWN_NO_TESTSUITES")
    counters = {}
    for name in ("tests", "failures", "errors", "skipped"):
        try:
            counters[name] = sum(int(s.attrib.get(name, "0")) for s in leaves)
        except ValueError:
            raise EvidenceObstruction("UNKNOWN_INVALID_JUNIT_COUNT") from None
    records = []
    for c in root.iter("testcase"):
        ident = (c.attrib.get("file", ""), c.attrib.get("classname", ""), c.attrib.get("name", ""))
        if not ident[1] or not ident[2]:
            raise EvidenceObstruction("UNKNOWN_TEST_IDENTITY")
        records.append(ident)
    if not records or len(records) != counters["tests"] or len(records) != len(set(records)):
        raise EvidenceObstruction("UNKNOWN_TEST_IDENTITY_OR_COUNT")
    if counters["failures"] != sum(bool(list(c.iter("failure"))) for c in root.iter("testcase")):
        raise EvidenceObstruction("UNKNOWN_JUNIT_FAILURE_COUNT")
    if counters["errors"] != sum(bool(list(c.iter("error"))) for c in root.iter("testcase")):
        raise EvidenceObstruction("UNKNOWN_JUNIT_ERROR_COUNT")
    if counters["skipped"] != sum(bool(list(c.iter("skipped"))) for c in root.iter("testcase")):
        raise EvidenceObstruction("UNKNOWN_JUNIT_SKIP_COUNT")
    return {"counts": counters, "case_ids": sorted(records), "junit_sha256": sha(xml)}


def read_native_receipt(xml: bytes, *, original_sha: str, git_head: str,
                        argv: list[str], exit_code: int, original_case_scope: str) -> dict:
    """Runtime facts are externally attested by the exact CI runner, not by XML alone."""
    if original_sha != git_head or len(original_sha) != 40:
        raise EvidenceObstruction("UNKNOWN_SOURCE_COMMIT_MISMATCH")
    if argv[:3] != ["python", "-m", "pytest"] or any(";" in x or "\n" in x for x in argv):
        raise EvidenceObstruction("UNKNOWN_UNSUPPORTED_NATIVE_COMMAND")
    record = exact_case_ids(xml)
    cs = record["counts"]
    if exit_code != 0 or cs["failures"] or cs["errors"]:
        status = "UNKNOWN_NATIVE_FAILURE"
    elif cs["skipped"]:
        status = "UNKNOWN_PARTIAL_EXECUTED_SCOPE"
    else:
        status = "WARRANTED_BOUNDED_EXECUTED_CASE_IDS"
    return {
        "status": status,
        "original_source_commit": original_sha,
        "original_source_head": git_head,
        "argv": argv,
        "run_exit_code": exit_code,
        "source_scope": original_case_scope,
        "evidence": record,
        "not_established": [
            "author's complete intended test coverage",
            "causal authenticity without the external pinned runner",
            "hermetic environment or complete trusted import closure",
            "new test-constructor grammar or prospective source advantage"
        ],
    }


def minimal_supports(alternatives: list[list[str]], live: set[str]) -> list[list[str]]:
    """Return inclusion-minimal currently live AND-support sets (OR over alternatives)."""
    valid = [frozenset(x) for x in alternatives if set(x) <= live]
    return [sorted(s) for s in sorted(set(valid), key=lambda s: (len(s), sorted(s)))
            if not any(other < s for other in valid)]


def claims_at_snapshot(claims: dict[str, list[list[str]]], live: set[str]) -> dict:
    """Historical alternatives remain immutable; only active view changes."""
    return {name: {"supports": minimal_supports(choices, live),
                   "active": bool(minimal_supports(choices, live))}
            for name, choices in sorted(claims.items())}


def compare_equally_informed(candidate: dict | None, baseline: dict | None) -> str:
    """No independent human comparator is implied by this exact-case comparison."""
    if candidate is None or baseline is None:
        return "UNKNOWN_MISSING_COMPARATOR"
    if candidate["status"] != "WARRANTED_BOUNDED_EXECUTED_CASE_IDS":
        return "UNKNOWN_CANDIDATE_SCOPE"
    if baseline["status"] != "WARRANTED_BOUNDED_EXECUTED_CASE_IDS":
        return "UNKNOWN_BASELINE_SCOPE"
    a = candidate["evidence"]["case_ids"]
    b = baseline["evidence"]["case_ids"]
    return "TIE_EXACT_EXECUTED_CASE_IDENTITIES" if a == b else "DIFFERENT_SCOPE_NO_SUPERIORITY_PROOF"


def materialize_result(result: dict, file: Path):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
