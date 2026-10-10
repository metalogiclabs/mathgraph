"""Actual ML-DSA verification, semantic falsification, and independent replay."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from pqcrypto.sign import ml_dsa_65
from mathgraph.pq_warrant import signed_message
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mathgraph.crystal import SemanticObject
from mathgraph.pq_warrant import (
    bundle_bytes, claim_object, key_id, make_statement, resolve,
    sign_ed25519, sign_mldsa65,
)


@pytest.fixture(scope="module")
def keys():
    pq = ml_dsa_65.keygen()
    ed = Ed25519PrivateKey.generate()
    pq_pub = pq[0]
    ed_pub = ed.public_key().public_bytes_raw()
    pq_id = key_id("ML-DSA-65", pq_pub)
    ed_id = key_id("Ed25519", ed_pub)
    trust = {pq_id: ("ML-DSA-65", pq_pub), ed_id: ("Ed25519", ed_pub)}
    return pq, ed, trust


def source():
    # Exhaustive source-law claim over the complete 2^3 Boolean space.
    return claim_object(["and", ["var", "x"], ["var", "y"]],
                        ["and", ["var", "y"], ["var", "x"]])


def signed(obj, keys, assumptions=()):
    pq, ed, _ = keys
    statement = make_statement(obj, assumptions)
    return bundle_bytes(statement, [sign_mldsa65(statement, pq),
                                    sign_ed25519(statement, ed)])


def standalone(tmp_path, obj, wire, bundle, keys, revoked=()):
    (_, _, trust) = keys
    (tmp_path / "wire.b64").write_text(base64.b64encode(wire).decode("ascii"))
    (tmp_path / "bundle.json").write_bytes(bundle)
    (tmp_path / "trust_keys.json").write_text(json.dumps({
        kid:{"algorithm":alg, "public_b64":base64.b64encode(pub).decode("ascii")}
        for kid,(alg,pub) in trust.items()}, sort_keys=True, separators=(",", ":")))
    (tmp_path / "revoked.json").write_text(json.dumps(list(revoked)))
    cmd = [sys.executable, str(Path(__file__).resolve().parents[1] /
           "scripts/pq_warrant_independent_replay.py"), str(tmp_path)]
    completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


def test_real_pq_and_independent_replayer_with_same_immutable_bytes(tmp_path, keys):
    obj = source()
    wire = obj.to_bytes()
    digest = hashlib.sha3_512(wire).hexdigest()
    assert wire[:6] == b"MGSO\x00\x01"
    assert obj.id == "semantic:" + hashlib.sha256(wire).hexdigest()
    assert len(digest) == 128
    assert SemanticObject.from_bytes(wire).to_bytes() == wire
    bundle = signed(obj, keys)
    result = resolve(wire, bundle, trusted_keys=keys[2])
    external = standalone(tmp_path, obj, wire, bundle, keys)
    assert result.state == external["state"] == "WARRANTED_BOUNDED"
    assert result.reason == external["reason"] == "exhaustive_bool3_equality"
    assert make_statement(obj)["subject"]["digests"]["sha3-512"] == digest


def test_authenticated_false_claim_has_real_counterexample(tmp_path, keys):
    obj = claim_object(["var", "x"], ["var", "y"])
    wire, bundle = obj.to_bytes(), signed(obj, keys)
    primary = resolve(wire, bundle, trusted_keys=keys[2])
    independent = standalone(tmp_path, obj, wire, bundle, keys)
    assert primary.state == independent["state"] == "REFUTED"
    assert primary.counterexample == independent["counterexample"]
    assert primary.counterexample["x"] != primary.counterexample["y"]


def test_unknown_future_semantics_are_preserved_not_warranted(tmp_path, keys):
    future = SemanticObject("future.quantum.machine", 99, b"\x00\xffproof-system-2099",
                            ("quantum.future@9",))
    raw, bundle = future.to_bytes(), signed(future, keys)
    before_id = future.id
    result = resolve(raw, bundle, trusted_keys=keys[2])
    external = standalone(tmp_path, future, raw, bundle, keys)
    assert result.state == external["state"] == "UNKNOWN"
    assert result.reason == "unsupported_claim_type"
    assert SemanticObject.from_bytes(raw).to_bytes() == raw
    assert SemanticObject.from_bytes(raw).id == before_id


def test_revoked_assumption_propagates_to_stale(tmp_path, keys):
    obj = source()
    bundle = signed(obj, keys, ("assumption:runtime@1",))
    wire = obj.to_bytes()
    primary = resolve(wire, bundle, trusted_keys=keys[2],
                      revoked_assumptions=frozenset({"assumption:runtime@1"}))
    independent = standalone(tmp_path, obj, wire, bundle, keys,
                             revoked=("assumption:runtime@1",))
    assert primary.state == independent["state"] == "STALE"
    assert resolve(wire, bundle, trusted_keys=keys[2]).state == "WARRANTED_BOUNDED"


def test_classical_only_cannot_downgrade_pq_requirement(keys):
    obj = source()
    statement = make_statement(obj)
    classical = bundle_bytes(statement, [sign_ed25519(statement, keys[1])])
    assert resolve(obj.to_bytes(), classical, trusted_keys=keys[2]).state == "UNAUTHENTICATED"


def test_tampering_object_and_signature_are_not_accepted(keys):
    obj = source()
    signed_wire = signed(obj, keys)
    wire = obj.to_bytes()
    tampered_wire = wire[:-1] + bytes([wire[-1] ^ 0x01])
    assert resolve(tampered_wire, signed_wire, trusted_keys=keys[2]).state != "WARRANTED_BOUNDED"
    parsed = json.loads(signed_wire)
    parsed["signatures"][0]["signature_b64"] = base64.b64encode(b"invalid").decode()
    assert resolve(wire, bundle_bytes(parsed["statement"], parsed["signatures"]),
                   trusted_keys=keys[2]).state == "UNAUTHENTICATED"
    parsed = json.loads(signed_wire)
    parsed["statement"]["assumptions"] = ["assumption:forged"]
    assert resolve(wire, bundle_bytes(parsed["statement"], parsed["signatures"]),
                   trusted_keys=keys[2]).state == "UNAUTHENTICATED"


def test_signature_identifier_and_incorrect_policy_key_fail(keys):
    obj = source()
    wire, bundle = obj.to_bytes(), signed(obj, keys)
    assert resolve(wire, bundle, trusted_keys={}).state == "UNAUTHENTICATED"
    changed = json.loads(bundle)
    changed["signatures"][0]["algorithm"] = "ML-DSA-2099"
    result = resolve(wire, bundle_bytes(changed["statement"], changed["signatures"]),
                     trusted_keys=keys[2])
    assert result.state == "UNAUTHENTICATED"
    changed["signatures"][0]["algorithm"] = "ML-DSA-65"
    changed["signatures"][0]["key_id"] = "sha3-256:" + "0"*64
    assert resolve(wire, bundle_bytes(changed["statement"], changed["signatures"]),
                   trusted_keys=keys[2]).state == "UNAUTHENTICATED"


def test_digest_substitution_rejected_even_when_resigned(keys):
    obj = source()
    statement = make_statement(obj)
    statement["subject"]["digests"]["sha3-512"] = "0"*128
    wire = obj.to_bytes()
    forged = bundle_bytes(statement, [sign_mldsa65(statement, keys[0])])
    assert resolve(wire, forged, trusted_keys=keys[2]).state == "UNAUTHENTICATED"


def test_noncanonical_json_and_opaque_unknown_grammar(keys):
    obj = source()
    wire = obj.to_bytes()
    valid = signed(obj, keys)
    assert resolve(wire, valid + b" ", trusted_keys=keys[2]).state == "UNAUTHENTICATED"
    repeated = valid.replace(b'"statement":', b'"statement":{},"statement":', 1)
    assert resolve(wire, repeated, trusted_keys=keys[2]).state == "UNAUTHENTICATED"
    unknown = claim_object(["magic", ["var", "x"]], True)
    assert resolve(unknown.to_bytes(), signed(unknown, keys),
                   trusted_keys=keys[2]).state == "UNKNOWN"


def test_wrong_signature_context_rejected(keys):
    obj = source()
    statement = make_statement(obj)
    pub = keys[0][0]
    wrong_sig = ml_dsa_65.sign(keys[0][1], signed_message(statement), b"wrong-pq-context")
    bad = bundle_bytes(statement, [{"algorithm":"ML-DSA-65",
                                    "key_id":key_id("ML-DSA-65",pub),
                                    "signature_b64":base64.b64encode(wrong_sig).decode()}])
    assert resolve(obj.to_bytes(), bad, trusted_keys=keys[2]).state == "UNAUTHENTICATED"
