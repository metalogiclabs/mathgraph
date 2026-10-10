# MathGraph post-quantum warrant V1: bounded falsifiable experiment

**Status:** CANDIDATE until exact-head CI succeeds. NOT general theorem soundness,
security certification, independent crypto validation, or a released protocol.

## Permanent semantic carrier

Reuse [Crystal Semantic Object Envelope v1](semantic_object_envelope_v1.md)
UNCHANGED. The canonical header is MGSO 00 01 and the historical object ID
remains semantic:SHA256(original canonical MGSO bytes). The original bytes and
identity never change during crypto migration. Unknown future types remain
opaque and are safely retransmitted; their meaning remains UNKNOWN.

## Cryptographic migration outside that carrier

The experimental signed statement commits to the SHA-256 original identity
and the named sha3-512 digest of exactly the SAME original bytes. It includes
a typed claim interface and sorted explicit assumptions. The signature is
over deterministic UTF-8 JSON (sorted keys, no excess spaces, no duplicate
keys), with the following domain-separated message:

    "MathGraph.pq-warrant.v1.signed-statement\0" ||
      uint64_be(statement_byte_length) || canonical_statement_json

ML-DSA-65 is mandatory (NIST FIPS 204). The signature context is
MathGraph.pq-warrant.v1. Transitional Ed25519 signatures can accompany it,
but never substitute for an accepted ML-DSA-65. The prototype uses pinned pqcrypto 1.0.0 backed by published Rust implementations
for ML-DSA-65, and pyca/cryptography 47.0.0 for transitional Ed25519, not
custom-made post-quantum cryptography. The pqcrypto vendor explicitly reports
that its backend has not undergone a full third-party security audit; this is
research code and must not authorize real deployments. Signer key trust is supplied OUTSIDE
the untrusted statement. This is an experimental JSON format, not a claim
to implement the standardized COSE/SCITT envelopes.

## Meaning and warrant are separate

The sole admissible claim type for warrant V1 is
mathgraph.claim.bool3-eq@1, interpreted under interface
mathgraph.finite-bool3-eq@1. An independent finite checker enumerates all
eight valuations of x,y,z and compares the two well-typed Boolean terms.
Results are WARRANTED_BOUNDED (exact finite model), REFUTED (counterexample),
UNKNOWN (unsupported semantics), STALE (revoked assumption), or
UNAUTHENTICATED (bad signature, trust root, digest or transport).

A signature authenticates its message, not the truth of its claim.
This finite checker does not establish Lean general soundness or correctness
of deployed binaries. Source-to-binary semantic correspondence is UNKNOWN.

## Replay and protected negatives

The primary implementation is mathgraph/pq_warrant.py.
The independent-process replayer scripts/pq_warrant_independent_replay.py
parses MGSO bytes and executes the finite predicate WITHOUT importing
the primary MathGraph implementation. Both use the SAME pinned pqcrypto backend,
so this is protocol/semantic implementation independence, not cryptographic
implementation diversity.

tests/test_pq_warrant.py runs ephemeral real ML-DSA-65 signing and checks both
replayers, including an authenticated false claim, unknown future semantic
type, a revoked assumption, classical-only downgrade, mutated hash, changed
subject bytes, bogus signer, signature context mismatch, noncanonical JSON
and unsupported grammar. No private keys are committed or archived.

Qualification runs on mathgraph-pq-warrant-v1 via
.github/workflows/pq-warrant-v1.yml with source receipts and JUnit artifact.

## Explicit open obligations

1. COSE/SCITT interoperable encoding and independent roundtrip witnesses.
2. Independent crypto backends, key migration, revocation and security review.
3. Signed policy suite/freshness/identity lifecycle, no silent PQ downgrade.
4. A nontrivial source/verification/executable correspondence theorem.
5. Formal proof of the warrant and local invalidation calculus.

References:
- [NIST FIPS 204](https://csrc.nist.gov/pubs/fips/204/final)
- [NIST FIPS 205](https://csrc.nist.gov/pubs/fips/205/final)
- [RFC 9943 SCITT](https://www.rfc-editor.org/rfc/rfc9943.html)
- [RFC 9964 COSE/JWS ML-DSA](https://www.rfc-editor.org/rfc/rfc9964.html)
- [RFC 4998 archive evidence](https://www.rfc-editor.org/rfc/rfc4998.html)
