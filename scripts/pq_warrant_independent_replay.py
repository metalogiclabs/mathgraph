#!/usr/bin/env python3
"""Independent bounded protocol/semantic replayer; NO MathGraph imports.

Shares pyca/cryptography's ML-DSA primitive; this is independent protocol and
finite-semantics code, not an independently validated cryptography backend.
Input: wire.b64, bundle.json, trust_keys.json, optional revoked.json.
"""
from __future__ import annotations

import base64
import hashlib
import itertools
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey
from cryptography.exceptions import InvalidSignature

CONTEXT = b"MathGraph.pq-warrant.v1"
DOMAIN = b"MathGraph.pq-warrant.v1.signed-statement\x00"


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def decode_json(data):
    def distinct(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("duplicate key")
            result[k] = v
        return result
    result = json.loads(data, object_pairs_hook=distinct)
    if canonical(result) != data:
        raise ValueError("noncanonical")
    return result


def mgso(wire):
    if len(wire) > 1048576 or wire[:6] != b"MGSO\x00\x01":
        raise ValueError("bad header")
    i = 6

    def take(n):
        nonlocal i
        if n < 0 or i + n > len(wire):
            raise ValueError("truncated")
        chunk = wire[i:i+n]
        i += n
        return chunk

    def uint(n):
        return int.from_bytes(take(n), "big")

    def txt():
        return take(uint(4)).decode("utf-8")

    name = txt()
    version = uint(4)
    n = uint(4)
    if n > 1000:
        raise ValueError("too many interfaces")
    interfaces = [txt() for _ in range(n)]
    payload = take(uint(8))
    if i != len(wire) or not name or interfaces != sorted(set(interfaces)):
        raise ValueError("noncanonical MGSO")
    return name, version, interfaces, payload


def eval_expr(e, values, depth=0):
    if depth > 32:
        raise ValueError("depth")
    if type(e) is bool:
        return e
    if not isinstance(e, list) or len(e) not in (2, 3):
        raise ValueError("shape")
    if e[0] == "var" and len(e) == 2 and e[1] in values:
        return values[e[1]]
    if e[0] == "not" and len(e) == 2:
        return not eval_expr(e[1], values, depth + 1)
    if e[0] in ("and", "or", "xor") and len(e) == 3:
        a = eval_expr(e[1], values, depth + 1)
        b = eval_expr(e[2], values, depth + 1)
        if e[0] == "and":
            return a and b
        if e[0] == "or":
            return a or b
        return a != b
    raise ValueError("unknown opcode")


def replay(path):
    try:
        wire = base64.b64decode((path / "wire.b64").read_text().strip(), validate=True)
        name, version, interfaces, payload = mgso(wire)
        raw = (path / "bundle.json").read_bytes()
        if len(raw) > 65536:
            return {"state": "UNAUTHENTICATED", "reason": "oversize"}
        env = decode_json(raw)
        if set(env) != {"statement", "signatures"}:
            raise ValueError("bundle")
        s = env["statement"]
        if set(s) != {"format", "subject", "claim_interface", "assumptions"}:
            raise ValueError("statement")
        if (s["format"] != "mathgraph.pq-warrant.v1" or
            s["claim_interface"] != "mathgraph.finite-bool3-eq@1"):
            return {"state": "UNKNOWN", "reason": "unsupported_statement_contract"}
        expected = {"sha256": hashlib.sha256(wire).hexdigest(),
                    "sha3-512": hashlib.sha3_512(wire).hexdigest()}
        subject = s["subject"]
        if (set(subject) != {"legacy_id", "digests"} or
            subject["legacy_id"] != "semantic:" + expected["sha256"] or
            subject["digests"] != expected):
            return {"state": "UNAUTHENTICATED", "reason": "digest_or_identity_mismatch"}
        assumptions = s["assumptions"]
        if not isinstance(assumptions, list) or assumptions != sorted(set(assumptions)):
            raise ValueError("assumptions")
        keys = decode_json((path / "trust_keys.json").read_bytes())
        msg = DOMAIN + len(canonical(s)).to_bytes(8, "big") + canonical(s)
        valid = False
        for sig in env["signatures"]:
            if set(sig) != {"algorithm", "key_id", "signature_b64"}:
                raise ValueError("signature record")
            if sig["algorithm"] != "ML-DSA-65" or sig["key_id"] not in keys:
                continue
            pair = keys[sig["key_id"]]
            if pair["algorithm"] != "ML-DSA-65":
                continue
            pub = base64.b64decode(pair["public_b64"], validate=True)
            kid = "sha3-256:" + hashlib.sha3_256(
                b"MathGraph.key.v1\x00ML-DSA-65\x00" + pub).hexdigest()
            if kid != sig["key_id"]:
                continue
            try:
                MLDSA65PublicKey.from_public_bytes(pub).verify(
                    base64.b64decode(sig["signature_b64"], validate=True), msg, CONTEXT)
                valid = True
            except (InvalidSignature, ValueError):
                continue
        if not valid:
            return {"state": "UNAUTHENTICATED", "reason": "required_mldsa65_not_verified"}
        revoked_file = path / "revoked.json"
        revoked = json.loads(revoked_file.read_text()) if revoked_file.exists() else []
        if any(a in revoked for a in assumptions):
            return {"state": "STALE", "reason": "revoked_assumption"}
        if (name != "mathgraph.claim.bool3-eq" or version != 1 or
            "mathgraph.finite-bool3-eq@1" not in interfaces):
            return {"state": "UNKNOWN", "reason": "unsupported_claim_type"}
        try:
            c = decode_json(payload)
            if set(c) != {"left", "right"}:
                raise ValueError("claim")
            for tup in itertools.product((False, True), repeat=3):
                values = dict(zip("xyz", tup))
                if eval_expr(c["left"], values) != eval_expr(c["right"], values):
                    return {"state": "REFUTED", "reason": "finite_counterexample",
                            "counterexample": values}
        except (ValueError, TypeError, KeyError):
            return {"state": "UNKNOWN", "reason": "unsupported_claim_grammar"}
        return {"state": "WARRANTED_BOUNDED", "reason": "exhaustive_bool3_equality"}
    except (ValueError, KeyError, TypeError, UnicodeError, OSError, AttributeError):
        return {"state": "UNAUTHENTICATED", "reason": "noncanonical_or_unverifiable_envelope"}


if __name__ == "__main__":
    print(json.dumps(replay(Path(sys.argv[1])), sort_keys=True))
