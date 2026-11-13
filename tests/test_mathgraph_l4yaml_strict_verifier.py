"""Negative controls against a forged or incomplete native semantic audit."""

import importlib.util
import json
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parents[1] / "research/l4yaml_anchor_continuity_v1"
SPEC = importlib.util.spec_from_file_location("l4yaml_native_strict_audit", HERE / "analyze.py")
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.mark.parametrize("data", [
    "", "{}\n", "{}\n" * 13,
    '{"case":"x","case":"x"}\n' * 13,
    "\n" * 13,
])
def test_incomplete_or_duplicate_native_log_rejected(tmp_path, data):
    log = tmp_path / "native.jsonl"
    log.write_text(data)
    with pytest.raises(audit.VerificationError):
        audit.read_native(log)


def test_oracle_baseline_is_structurally_rechecked():
    source = HERE / "oracle_results.json"
    assert audit.check_oracle(source)["acyclic_cases"] == 16


@pytest.mark.parametrize("tamper", [
    lambda r: r.update(version="untracked"),
    lambda r: r.update(wheel_sha256="0" * 64),
    lambda r: r["acyclic_cases"][0].update(actual="wrong"),
    lambda r: r["acyclic_cases"].append(r["acyclic_cases"][0]),
])
def test_oracle_tampering_rejected(tmp_path, tamper):
    source = json.loads((HERE / "oracle_results.json").read_text())
    tamper(source)
    target = tmp_path / "oracle.json"
    target.write_text(json.dumps(source))
    with pytest.raises(audit.VerificationError):
        audit.check_oracle(target)


def test_duplicate_json_keys_rejected():
    with pytest.raises(audit.VerificationError, match="duplicate JSON"):
        audit.loads('{"status":"ok","status":"ok"}')


def test_nonstandard_json_constants_rejected():
    with pytest.raises(audit.VerificationError, match="non-JSON"):
        audit.loads('{"value":NaN}')
