# Supported import V1

This independent standard-library consumer imports only the immutable public
L4YAML record `mg-l4yaml-source-check-20261010`. It derives a read-only historical
`WARRANTED_BOUNDED` result for the 48 pinned YAML-suite cases under the existing
`pinned-jpl-qualified-receipt-v1` admission. It neither imports the website or
producer implementation nor executes Lean or fetches any URL.

The explicit local trust policy narrows the existing Resolve JPL admission to
this one record. It pins the same source commit, suite commit, receipt, verifier,
empty assumption list, exact finite scope, content hash, and transport bytes.
The member filename is `record.json` here (the same bytes are named
`jpl-record.json` in the Resolve bundle). Supply the policy separately from
incoming evidence and review its digest outside that evidence:

```bash
python scripts/mathgraph_import_v1.py \
  --record conformance/import_v1/fixtures/record.json \
  --policy conformance/import_v1/fixtures/trust-policy.json \
  --policy-sha256 944231afaf9d89e6f7dc77d9efbe80dcbd3fc76f8e8f260b32637a0f261faf65
```

The same arguments work with `python conformance/import_v1/consumer.py`.
That single file also works when copied outside the repository, using only
Python's standard library. The CLI accepts local regular files only; each read
is bounded to 65,536 bytes. It does not accept URLs or standard input. Successful
stdout is canonical UTF-8 JSON followed by one newline, exactly matching
`fixtures/result.json`. Failures exit 1 and emit a JSON `reason_code` on stderr.

The Python entry point is
`import_record(record_raw, policy_raw, policy_sha256, *, goal="finite_parser_acceptance")`.
Both inputs must be bytes. Rejections raise the module's typed `ImportError`
(a `ValueError` subclass) with a `reason_code` attribute. Unsupported goals,
including current applicability/lifecycle questions, raise `UNSUPPORTED_GOAL`.

Parsing rejects invalid UTF-8, BOMs, escaped lone surrogates, duplicate keys,
non-finite numbers, invalid roots, excessive nesting, and oversize input.
Validation checks exact schemas, identity, source/test pins, verifier receipts,
normalization context, assumptions, status axes, and digests. Rehashing a broader
policy or modified record does not expand the admitted profile. Canonical policy
bytes are required so the successful result remains deterministic.

`fixtures/record.json` is byte-identical to the existing public record:

- Transport SHA-256: `7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703`
- Content SHA-256: `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`

The result schema is `mathgraph.import-result.v1`. Its exact-profile JSON Schema
is published at `https://mathgraph.org/schemas/import-result-v1.schema.json` and
mirrored byte-for-byte from `protocol/schemas/import-result-v1.schema.json`.
Schema validation alone does not authenticate evidence.

## Meaning and limits

The result separates historical epistemic status from current lifecycle,
freshness, applicability, and authorization. Lifecycle and current applicability
are `UNKNOWN`; freshness is `NOT_CHECKED`; authorization is
`READ_ONLY_NO_AUTOMATIC_AUTHORIZATION`. No record index is supplied or fetched,
so the importer cannot establish current catalogue lifecycle. The result keeps
generalization, statement fidelity, human digestion, universal YAML correctness,
and a whole-input extraction theorem explicitly `UNKNOWN`.

The empty receipt assumption list does not mean unconditional YAML correctness:
the exact source/suite pins, specified input decoder, finite cases, controls,
Lean version, and receipt verifier remain explicit in the result. The imported
receipt is checked for consistency with 31 accepts + 17 rejects = 48 matched
cases, plus 4 controls = 52 guards. This is receipt-level historical derivation;
the import does not rerun source tests, replay original Lean proofs, establish
source fidelity, issue a theorem badge, or admit a claim to the kernel. Its
`READ_ONLY_IMPORT_RESULT` is not a mathematical terminal form or an executable
authorization. Digests protect integrity; the separately reviewed local policy
provides the bounded trust decision.

## Conformance

```bash
python -m pytest conformance/import_v1 conformance/protocol_v1 conformance/resolve_v1 -q
cd website && npm run build && npm run test:contracts
```

Tests mutate source bytes and commits, test commits/digests, content digests,
finite scope, verifier, assumptions, generalization, status and authorization.
They also cover strict parsing, policy substitution, unsupported goals,
standalone execution, deterministic output, and schema/public-record byte parity.
