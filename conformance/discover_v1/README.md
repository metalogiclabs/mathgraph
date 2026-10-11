# Local Discover v1 conformance

This directory freezes a real advisory request/result pair and tests the
dependency-free `mathgraph_protocol` implementation. It is not an independent
mathematical verifier or a hosted Discover service.

```bash
python -m pytest conformance/discover_v1/test_discover.py -q
python -I -S scripts/mathgraph_discover_v1.py --request conformance/discover_v1/fixtures/request.json
```

The result must match `fixtures/result.json` byte-for-byte. `OK`, `PARTIAL`, and
`UNKNOWN` exit zero; structural or operational `ERROR` exits one. All results
are advisory and report `NOT_CHECKED`, including error results.

The first fixture comes from the exact local
`examples/evidence_packs/recursive_residual_transfer_v1_20260523` pack. Its nine
small local artifacts are all present in Git, including seven source CSVs whose
original bytes are unchanged. The adapter pins manifest/metrics digests, checks
every present artifact's exact size/hash, and preserves all original locators.
The absent candidate-score CSV and required full-replay SQLite ledger remain
manifested references. The example is `PARTIAL`; historical metrics are reported
advisory inputs, not independently authenticated experiment results.

The isolation test copies only `mathgraph_protocol` into a temporary directory,
runs under `python -I -S`, blocks optional libraries and other MathGraph imports,
and denies network and subprocess operations through a Python audit hook. It
compares two runs and the committed result bytes. This is a dependency/isolation
test, not a security sandbox for arbitrary untrusted Python code.

The normative schemas are outside the website under `protocol/schemas/`.
Tests require exact byte parity with their public projections. Full semantics,
eligibility rules, wire-profile constraints, and source limitations are described
in `docs/discover_contract_v1.md`.
