# Source catalogue v1 independent replay

This directory contains an implementation-independent, Python-standard-library
consumer for the MathGraph source catalogue contract. It validates exact local
publication bytes under a separately pinned trust policy. It imports neither
`mathgraph` nor `mathgraph_protocol`.

The replay checks canonical bytes, content addresses, source and producer pins,
closed object/relation identities, admitted structural relation meanings,
counts, ordering, byte budgets, feasible source ranges, nonempty unique producer
and wrapper source identities, and the exact derived search index. Unknown
noncritical extensions remain opaque. Unknown critical extensions, unsupported
relations, forged statuses, terminal forms, proof/evidence edges, implication,
equivalence, or action authority fail closed.

The replay does **not** fetch Mathlib source, run Lean, replay proof checking,
authenticate the current state of GitHub, establish current applicability, or
authorize an action. Without the upstream source and qualification environment,
it validates the pinned historical catalogue, source identities, and publication
integrity only. Source-byte and environment correspondence are rechecked by the
separate regeneration workflow.

After the qualified public catalogue and trust policy are committed:

```sh
python -I -S -B conformance/source_catalogue_v1/consumer.py \
  --catalogue-root website/public/catalogues/mathlib/v4.34.1 \
  --policy conformance/source_catalogue_v1/trust-policy.json \
  --policy-sha256 <separately-reviewed-sha256> --audit-imports
```

For mechanically enforced network and repository isolation, acquire the exact
runtime image before replay and use `run_isolated.py --backend docker`. The
runner mounts only the consumer, trust policy, manifest, search index, and the
manifest-listed shards read-only. It also requires an independently supplied
checked-out wrapper commit, binds the actual consumer and runner SHA-256 values
to the trust policy, and records the isolated interpreter identity:

```sh
python -I -S -B conformance/source_catalogue_v1/run_isolated.py \
  --backend docker --image-id sha256:<exact-image-id> \
  --catalogue-root <catalogue> --policy <trust-policy.json> \
  --policy-sha256 <separately-reviewed-sha256> \
  --artifact-checksums-sha256 <separate-transfer-sha256> \
  --expected-wrapper-commit <exact-checked-out-commit>
```

The hosted adversarial suite needs no package installation:

```sh
python -I -S -B conformance/source_catalogue_v1/stdlib_conformance.py
```

It emits a deterministic authority-`NONE` report for 48 named conformance
cases. The hosted workflow retains that report, verifies the complete downloaded
artifact inventory from a sorted relative checksum manifest, and records action
artifact metadata only as provenance rather than as an enforced integrity gate.
