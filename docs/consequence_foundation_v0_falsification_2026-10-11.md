# Consequence foundation v0 — paper-first falsification checkpoint (2026-10-11)

Status: **REJECTED as an authority-preserving common unit at schema-only boundary**; still **CANDIDATE as a descriptive transport envelope**.

## Paper and ROS constraints consulted
- Papers & Formal Ideas Registry: local warrant does not imply protected terminal warrant; contextual, policy-dependent authority; dependency invalidation preserves unaffected consequences.
- MDA v7: exact source/role binding; strong executable-ledger comparator can tie persistence, despite gains against episodic reconstruction.
- Matched WebArena E→F: verified transfer but 3 vs 3 evaluations against strong stateless comparator, so no strict advantage.

## Local diagnostic
A standalone Python jsonschema Draft 2020-12 diagnostic reconstructed the exact v0 field constraints from PR #157's schema as inspected through GitHub. It was **not** an exact-byte checkout test or the repository's CI suite. Of ten expected behaviors, nine matched and one failed:

- A valid shape was accepted.
- Unexpected top-level status/authorization/freshness fields were rejected.
- **Scope escalation** from `jpl:48-cases` to `universal` was **accepted** by the schema. This is the decisive negative.
- Null authority, unsupported lineage, forged assessment reference, and changed evidence hash were all structurally accepted; this is expected for a descriptive envelope, but none may be promoted semantically.
- Boolean `size_bytes` was rejected.

The diagnostic used synthetic references; it did not replay the three protected real cases or execute independent domain consumers. No general claim of semantic unsoundness follows from a structural parser admitting a structurally valid but semantically false claim. The failure is against the **stronger proposed acceptance criterion** that the envelope itself preserves bounded authority.

## Decision
Do not promote v0 as a universal verified unit or publish a qualification badge. Retain existing domain-specific contracts and consumers as authorities. Next cheapest decisive experiment: bind the envelope's `scope` and `statement` to an externally pinned domain claim/policy; independent consumers must reject an escalated scope or return UNKNOWN, then replay JPL, finite capability and the negative compounding result with matched semantic comparisons and protected terminal checks.

No production, historical evidence, registry, or protocol v1 changes.
