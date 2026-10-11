# Resolve protocol v1 conformance consumer

This directory contains an independently implemented, standard-library-only
validator for the published Resolve bundle and trust-policy contracts. It
checks strict JSON decoding, exact object shapes, base64 transport, decoded
member sizes and hashes, externally supplied policy integrity, and the exact
historical receipt-admission bindings.

It deliberately does **not** replay the Resolve graph. Run the existing
`conformance/resolve_v1/consumer.py` after this validator when semantic replay
is required.

## Run

Python 3.11 or later is sufficient:

```bash
python conformance/protocol_v1/consumer.py \
  --bundle conformance/resolve_v1/fixtures/bundle.json \
  --policy conformance/resolve_v1/trust-policy.json \
  --policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

Success prints a deterministic JSON report with `accepted: true` and
`semantic_replay: NOT_PERFORMED`. Failure exits nonzero and prints a JSON
object containing a stable `reason_code`.

The policy digest is a trust input and must arrive independently of the bundle
and policy files. A self-hash proves only integrity, not authenticity or
authority.

## Tests

```bash
python -m pytest conformance/protocol_v1/test_consumer.py -q
```

The negative corpus covers duplicate keys, unexpected and missing fields,
base64/size/hash substitutions, unsupported versions, unknown kinds, invalid
admission bindings, and a record whose changed bytes were consistently
rehashed but were not part of the authorized v1 member set.
