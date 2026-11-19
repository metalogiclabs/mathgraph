# Consequence foundation v0 — candidate, not admitted

## Purpose
Test whether existing MathGraph Check/Resolve records, finite capabilities, and negative research outcomes share a *lossless minimal envelope*. This document is a hypothesis and does not change existing authority.

A **consequence record** is an immutable description of one bounded assertion and pointers to the evidence and policies needed to judge it. It is **not** a proof, verdict, credential, permission, or new mathematical terminal form.

## Minimal envelope
- `schema_version`: exact parser contract.
- `id`, `version`: stable logical identity and immutable revision.
- `kind`: claim, observation, obstruction, capability, or experiment. Kinds classify payloads, not truth.
- `statement`: human-facing claim; never sufficient for admission.
- `scope`: exact bounded scope identifier; no subset or alias inference.
- `authority`: externally pinned verifier/policy artifact reference, or null.
- `evidence`: pinned artifact references, possibly empty.
- `payload`: domain-specific existing contract reference, or null.
- `relations`: typed links to other exact record versions, each with its own evidence reference or null.
- `assessment`: an optional *separate* reference to an evaluation; its contents cannot be trusted merely because referenced.

A reference contains `locator`, `sha256` and `size_bytes`. A hash establishes byte identity, not authenticity or truth. The record may be structurally valid even with no evidence; it then has no warranted semantics.

## Three protected exemplars
1. Source-pinned JPL L4YAML finite observation: preserve 48-case boundary and distinguish test observation from universal parser correctness.
2. Finite representation refinement: preserve existing capability descriptor/evaluation/receipt/policy and exact eight-state boundary. Do not turn the envelope into a second qualification.
3. Matched WebArena E→F result: preserve both bounded transfer and the *negative* finding of no advantage against the strong schema-aware stateless comparator (3 vs 3 evaluations). Do not convert null economic advantage into a capability win.

## Decisive acceptance experiment
An independent consumer must parse the same envelope and recover each exemplar's *existing* authority and exact status solely through its domain-specific verified payload and pinned evidence, including negative and UNKNOWN distinctions. Compare against original domain consumers. Any information loss or accidental promotion rejects the common-unit hypothesis. A successful three-case test warrants only bounded representational adequacy, not a universal ontology.

## Compatibility and authority
Existing schemas and registries remain normative. No migration, status promotion, production publication, graph explorer, or new authentication system is authorized by this v0. Typed graph edges are claims requiring their own evidence. Temporal applicability, revocation, freshness, and action authority remain independent axes.

## Minimal next work
Create source-exact exemplars and independent consumer; prove lossless round-trip plus adversarial status injection, digest mismatch, absent evidence, and false-lineage controls. Compare actual terminal consequences and cost, not only local checks. Record failed distinctions in ROS.
