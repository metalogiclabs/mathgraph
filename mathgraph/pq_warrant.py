"""Bounded post-quantum evidence binding for Crystal semantic objects.

A signature authenticates a statement, not mathematical truth. Only the
separately checked finite Boolean claim language can earn WARRANTED_BOUNDED.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import itertools
import json
from typing import Mapping

from mathgraph.crystal import SemanticObject

FORMAT = "mathgraph.pq-warrant.v1"
CLAIM_TYPE = "mathgraph.claim.bool3-eq"
CLAIM_INTERFACE = "mathgraph.finite-bool3-eq@1"
SIGNATURE_CONTEXT = b"MathGraph.pq-warrant.v1"
MESSAGE_DOMAIN = b"MathGraph.pq-warrant.v1.signed-statement\x00"
MAX_OBJECT_BYTES = 1048576
MAX_BUNDLE_BYTES = 65536


def _json_bytes(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _canonical_json(raw: bytes) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict:
        d: dict = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("duplicate JSON key")
            d[k] = v
        return d
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                     parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if _json_bytes(obj) != raw:
        raise ValueError("noncanonical JSON")
    return obj


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(value: str) -> bytes:
    data = base64.b64decode(value, validate=True)
    if _b64(data) != value:
        raise ValueError("noncanonical base64")
    return data


def _bytes_digest(wire: bytes) -> dict[str, str]:
    return {"sha256": hashlib.sha256(wire).hexdigest(),
            "sha3-512": hashlib.sha3_512(wire).hexdigest()}


def key_id(algorithm: str, public_key: bytes) -> str:
    """Key identifier is informational; caller must separately trust the key."""
    return "sha3-256:" + hashlib.sha3_256(
        b"MathGraph.key.v1\x00" + algorithm.encode("ascii") + b"\x00" + public_key
    ).hexdigest()


def claim_object(left: object, right: object) -> SemanticObject:
    """A narrowly scoped, deterministic finite claim; NOT a general logic."""
    payload = _json_bytes({"left": left, "right": right})
    return SemanticObject(CLAIM_TYPE, 1, payload, (CLAIM_INTERFACE,))


def make_statement(obj: SemanticObject, assumptions: tuple[str, ...] = ()) -> dict:
    if not isinstance(obj, SemanticObject) or len(obj.to_bytes()) > MAX_OBJECT_BYTES:
        raise ValueError("object over bounded size or wrong type")
    if len(set(assumptions)) != len(assumptions) or tuple(sorted(assumptions)) != assumptions:
        raise ValueError("assumptions must be unique and sorted")
    if any(not isinstance(a, str) or not a for a in assumptions):
        raise ValueError("empty assumption")
    wire = obj.to_bytes()
    return {"format": FORMAT,
            "subject": {"legacy_id": obj.id, "digests": _bytes_digest(wire)},
            "claim_interface": CLAIM_INTERFACE,
            "assumptions": list(assumptions)}


def signed_message(statement: dict) -> bytes:
    raw = _json_bytes(statement)
    return MESSAGE_DOMAIN + len(raw).to_bytes(8, "big") + raw


def sign_mldsa65(statement: dict, private_key: object) -> dict:
    """Sign using standard ML-DSA-65, never a custom crypto implementation."""
    from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey
    if not isinstance(private_key, MLDSA65PrivateKey):
        raise TypeError("requires a real ML-DSA-65 private key")
    public = private_key.public_key().public_bytes_raw()
    signature = private_key.sign(signed_message(statement), SIGNATURE_CONTEXT)
    return {"algorithm": "ML-DSA-65", "key_id": key_id("ML-DSA-65", public),
            "signature_b64": _b64(signature)}


def sign_ed25519(statement: dict, private_key: object) -> dict:
    """Optional transition signature, NEVER an accepted substitute for ML-DSA-65."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("requires Ed25519 private key")
    public = private_key.public_key().public_bytes_raw()
    return {"algorithm": "Ed25519", "key_id": key_id("Ed25519", public),
            "signature_b64": _b64(private_key.sign(signed_message(statement)))}


def bundle_bytes(statement: dict, signatures: list[dict]) -> bytes:
    """Untrusted transport. Canonicality does NOT confer proof authority."""
    return _json_bytes({"statement": statement, "signatures": signatures})


@dataclass(frozen=True)
class Resolution:
    state: str  # WARRANTED_BOUNDED, REFUTED, UNKNOWN, STALE, UNAUTHENTICATED
    reason: str
    counterexample: dict[str, bool] | None = None


def _boolean(expr: object, env: Mapping[str, bool], depth: int = 0) -> bool:
    if depth > 32:
        raise ValueError("expression depth unsupported")
    if type(expr) is bool:
        return expr
    if not isinstance(expr, list) or len(expr) not in (2, 3):
        raise ValueError("unsupported expression")
    op = expr[0]
    if op == "var" and len(expr) == 2 and expr[1] in env:
        return env[expr[1]]
    if op == "not" and len(expr) == 2:
        return not _boolean(expr[1], env, depth + 1)
    if op in ("and", "or", "xor") and len(expr) == 3:
        a = _boolean(expr[1], env, depth + 1)
        b = _boolean(expr[2], env, depth + 1)
        return (a and b) if op == "and" else (a or b) if op == "or" else (a != b)
    raise ValueError("unknown finite-logic operation")


def _finite_truth(obj: SemanticObject) -> Resolution:
    if (obj.type_id != CLAIM_TYPE or obj.contract_version != 1 or
            CLAIM_INTERFACE not in obj.interfaces):
        return Resolution("UNKNOWN", "unsupported_claim_type")
    try:
        claim = _canonical_json(obj.payload)
        if not isinstance(claim, dict) or set(claim) != {"left", "right"}:
            raise ValueError("unsupported claim schema")
        for vals in itertools.product((False, True), repeat=3):
            world = dict(zip("xyz", vals))
            if _boolean(claim["left"], world) != _boolean(claim["right"], world):
                return Resolution("REFUTED", "finite_counterexample", world)
        return Resolution("WARRANTED_BOUNDED", "exhaustive_bool3_equality")
    except (ValueError, TypeError, KeyError, RecursionError):
        return Resolution("UNKNOWN", "unsupported_claim_grammar")


def resolve(wire: bytes, bundle: bytes, *, trusted_keys: Mapping[str, tuple[str, bytes]],
            revoked_assumptions: frozenset[str] = frozenset()) -> Resolution:
    """Fail closed: PQ signature + SHA3-512 + native finite checker required.

    Trust roots are supplied OUTSIDE the signed document. A self-issued key
    inside a document can never authorize itself. Ed25519 does not satisfy PQ.
    """
    if not isinstance(wire, bytes) or len(wire) > MAX_OBJECT_BYTES:
        return Resolution("UNKNOWN", "unsupported_object_size")
    if not isinstance(bundle, bytes) or len(bundle) > MAX_BUNDLE_BYTES:
        return Resolution("UNAUTHENTICATED", "unsupported_bundle_size")
    try:
        obj = SemanticObject.from_bytes(wire)
        data = _canonical_json(bundle)
        if not isinstance(data, dict) or set(data) != {"statement", "signatures"}:
            raise ValueError("unsupported bundle")
        stmt, signatures = data["statement"], data["signatures"]
        if not isinstance(stmt, dict) or set(stmt) != {
                "format", "subject", "claim_interface", "assumptions"}:
            raise ValueError("unsupported statement")
        if stmt["format"] != FORMAT or stmt["claim_interface"] != CLAIM_INTERFACE:
            return Resolution("UNKNOWN", "unsupported_statement_contract")
        subject = stmt["subject"]
        if not isinstance(subject, dict) or set(subject) != {"legacy_id", "digests"}:
            raise ValueError("bad subject")
        digests = subject["digests"]
        expected = _bytes_digest(wire)
        if not isinstance(digests, dict) or set(digests) != set(expected):
            return Resolution("UNKNOWN", "unsupported_digest_profile")
        if subject["legacy_id"] != obj.id:
            return Resolution("UNAUTHENTICATED", "legacy_identity_mismatch")
        for alg, expected_hash in expected.items():
            if not isinstance(digests[alg], str) or not hmac.compare_digest(
                    expected_hash, digests[alg]):
                return Resolution("UNAUTHENTICATED", "digest_mismatch")
        assumptions = stmt["assumptions"]
        if (not isinstance(assumptions, list) or
            any(not isinstance(a, str) or not a for a in assumptions) or
                assumptions != sorted(set(assumptions))):
            raise ValueError("noncanonical assumptions")
        if not isinstance(signatures, list) or len(signatures) > 8:
            raise ValueError("unsupported signature collection")
        msg = signed_message(stmt)
        pq_valid = False
        for sig in signatures:
            if not isinstance(sig, dict) or set(sig) != {"algorithm", "key_id", "signature_b64"}:
                raise ValueError("invalid signature record")
            algorithm, signer = sig["algorithm"], sig["key_id"]
            if not isinstance(algorithm, str) or not isinstance(signer, str):
                raise ValueError("invalid signature identifiers")
            pair = trusted_keys.get(signer)
            if pair is None or pair[0] != algorithm:
                continue
            pub = pair[1]
            if key_id(algorithm, pub) != signer:
                continue
            signature = _unb64(sig["signature_b64"])
            if algorithm == "ML-DSA-65":
                from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey
                from cryptography.exceptions import InvalidSignature
                try:
                    MLDSA65PublicKey.from_public_bytes(pub).verify(
                        signature, msg, SIGNATURE_CONTEXT)
                    pq_valid = True
                except (InvalidSignature, ValueError):
                    pass
            # No classical-only fallback. Unknown future algorithm remains unsupported.
        if not pq_valid:
            return Resolution("UNAUTHENTICATED", "required_mldsa65_not_verified")
        if any(a in revoked_assumptions for a in assumptions):
            return Resolution("STALE", "revoked_assumption")
        return _finite_truth(obj)
    except (ValueError, KeyError, TypeError, UnicodeError, OverflowError, ImportError, AttributeError):
        return Resolution("UNAUTHENTICATED", "noncanonical_or_unverifiable_envelope")
