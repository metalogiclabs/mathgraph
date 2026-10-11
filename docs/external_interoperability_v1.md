# Unsigned external interoperability v1

This local profile maps one exact `mathgraph.capability-contract.v1` artifact to
an [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md).
The committed example wraps the exact finite capability contract independently
qualified in [capability conformance](../conformance/capability_v1/README.md).
The wrapper does **not** import or reproduce that qualification. The portable
contract, finite-profile evaluation, consumer policy, and replay receipt remain
separate objects with separate verification requirements.

The normative shape is
[`external-binding-v1.schema.json`](../protocol/schemas/external-binding-v1.schema.json).
Its [public projection](../website/public/schemas/external-binding-v1.schema.json)
is byte-identical. The checked example is
[`statement.json`](../conformance/interoperability_v1/statement.json).
This is the first narrow profile; records, other schemas and media types require
an explicit future profile, rather than fallback interpretation.

## Exact mapping

| Statement field | Binding |
| --- | --- |
| `_type` | `https://in-toto.io/Statement/v1` |
| `predicateType` | `https://mathgraph.org/attestation/external-binding/v1` |
| `subject` | Exactly one opaque name and SHA-256 of the original artifact bytes |
| `predicate.schema_version` | `mathgraph.external-binding.v1` |
| `predicate.signature` | Always `UNSIGNED`; this describes the profile, not a signature verification result |
| `predicate.artifact` | Exact name, SHA-256, byte size, `application/json` media type, and `mathgraph.capability-contract.v1` object-schema identity |
| `predicate.claim` | Exact claim `id`, `kind`, and `scope` from the artifact |
| `predicate.assumptions` | Exact ordered assumptions from the artifact |
| `predicate.evidence` | Exact ordered references, including every id, locator, SHA-256, size and media type |
| `predicate.extensions` | Explicit noncritical opaque external data only |

The digest also binds every other descriptor member, including capability
identity, version, profile, input/output types, preconditions, guarantees,
implementation, boundary, limitations and contract extensions. Evidence hashes
are bound references: this adapter does not open, fetch, replay or verify the
referenced evidence. A matching evidence locator grants no access permission.

Both inputs are UTF-8 JSON **bytes**. Artifact bytes are hashed unchanged;
whitespace changes therefore change the digest. Export uses sorted keys,
two-space indentation, ASCII JSON escapes, and a single trailing LF. That is a
deterministic serialization convention for this profile, not a general JSON
canonicalization or signing scheme. Import accepts other valid JSON whitespace
and key order for the wrapper but always checks the exact supplied artifact.
The media type and object schema are fixed profile identifiers, not guessed
from a filename or fetched from a URI.

## Local API and consumer selection

```python
from pathlib import Path
from mathgraph_protocol.in_toto_v1 import export_statement, import_statement

name = "conformance/capability_v1/fixtures/capability-contract.json"
artifact = Path(name).read_bytes()  # Caller-controlled local read.
statement = export_statement(artifact, name=name)
expected = {
    "name": name,
    "sha256": "24e639b9181af313100504e0aa525536197d868810e6ffdb5093fd13501577a8",
    "size_bytes": 3533,
    "media_type": "application/json",
    "object_schema": "mathgraph.capability-contract.v1",
}
result = import_statement(statement, artifact, expected_artifact=expected)
assert result["correspondence"] == "MATCH"
assert result["qualification"] == "UNKNOWN"
```

The caller must select `expected_artifact` independently of the received wrapper.
Copying an attacker's pin from the wrapper defeats selection of the intended
artifact. A self-consistent new wrapper with a recomputed digest over a widened
scope, stripped assumptions or changed evidence cannot match the original pin.
Even if the caller selects new bytes, stale projected fields are rejected.
Names are opaque labels: neither the protocol package nor the thin
[`adapters/in_toto_v1.py`](../adapters/in_toto_v1.py) opens paths or fetches URLs.
Caller-supplied pins select content; they do not independently authenticate a
publisher or prove that the selected contract is qualified.

Invalid inputs raise `ExternalBindingError` with a structural or correspondence
reason code. This is not a mathematical refutation. Successful imports return:

- `correspondence: MATCH` and the exact artifact, claim, assumptions and evidence;
- `signature: UNSIGNED`;
- `authenticity`, `signer_policy`, `transparency`, and `freshness`: `NOT_CHECKED`;
- `qualification` and `current_applicability`: `UNKNOWN`;
- `action_authorization: NONE`.

No terminal form, accepted claim, qualification receipt, policy admission,
freshness, revocation check, supersession check or publisher identity is created.
Independent finite-profile qualification remains separate even when the exact
qualified contract is the subject.

## Fail-closed and extension rules

The standard-library implementation is the strict boundary. JSON Schema shape
validation alone cannot establish byte or field correspondence. It also cannot
reliably reject duplicate JSON keys or distinguish JSON integer syntax from
integral floating-point values. The implementation rejects duplicate keys at any
depth, nonfinite values including overflow, malformed UTF-8, unsupported statement
type/predicate type/object schema/media type, extra or missing known fields,
extra subjects, digest/size/name mismatches, and changed or stripped claim,
assumptions or evidence. It validates the underlying capability descriptor too.
Producer qualification/status/signature/terminal-form fields cannot be added to
known objects to grant authority.

Unknown data is accepted only inside `predicate.extensions`, with unique,
nonempty `id`, nonempty `version`, literal Boolean `critical: false`, and an
object-valued `payload`. Every critical extension is unsupported and rejected,
including critical extensions in the underlying capability contract. Unknown
top-level and predicate members are rejected, not guessed to be noncritical.
External extension payloads are returned as `external_extensions` without
interpretation; even a payload saying `qualification: QUALIFIED_BOUNDED` has no
effect on any outcome. Consumers must keep that opaque data separate from
authority fields. Export creates an empty external extension array. Artifact
extensions remain bound by the original artifact digest.

## Deferred external systems

These are documented extension boundaries, **not implementations**:

- [Sigstore bundle](https://docs.sigstore.dev/about/bundle/): a future integration
  needs real signed fixtures, cryptographic verification, independently selected
  signer identity/issuer/root policy, and transparency verification. Signature
  validity, signer policy, log inclusion, freshness, and semantic qualification
  must remain separate outcomes. This profile performs no signing, DSSE parsing,
  Sigstore bundle verification or transparency-log access.
- [SCITT RFC 9943](https://datatracker.ietf.org/doc/rfc9943/): a future COSE/receipt
  profile requires a trusted transparency-service policy and qualified verifier.
  A receipt can establish attributable inclusion under that policy; it does not
  establish mathematical truth. Attachments can currently appear only as opaque,
  explicitly noncritical data, without receipt verification or new authority.
- [RATS RFC 9334](https://datatracker.ietf.org/doc/rfc9334/): the separation of
  evidence, appraisal policy and results is an architectural comparison only.
  No RATS evidence/appraisal wire format is implemented. Device attestation
  evidence must not be relabelled as mathematical proof evidence.

There is no network, execution, signing, service, deployment or hosted endpoint
in this adapter. A future authenticated transport must not widen the authority
of the existing unsigned import result.

## Verification

```bash
python -m pytest conformance/interoperability_v1 conformance/capability_v1 conformance/protocol_v1 -q --tb=short
```

Tests cover exact qualified-contract bytes, deterministic output, schema parity,
field stripping and mutation, recomputed digests with changed scope, unsupported
types, strict decoding, producer authority injection, and opaque extension
handling. An isolated `python -I -S` check blocks optional/research imports and
runtime file/network/process side effects while exercising the thin adapter.
