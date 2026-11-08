# MathGraph Check: source-qualified projection gap in authenticated cycle

## Intent

When two independently qualified source states share a downstream observation
but disagree on a protected requirement, MathGraph Check should report a
**named obstruction**: no consumer of only that observation can decide the
protected verdict for both states. An incomplete or apparently collision-free
finite search remains UNKNOWN for the full claim.

The first source-bound demonstration is the frozen L4YAML parser-success / raw
SOH pair. The implementation must also work with future independently
qualified witnesses without inventing their authority.

## Approaches considered

1. **Chosen:** add an optional, host-qualified projection-claim adapter to
   the existing authenticated GitHub readback (`githubSnapshot`). Reuse
   `checkFiniteWarrantQuotient`, `resolve`, and `monitor`. Exact PR-head binding
   and separate trust policy are mandatory; default behavior is unchanged.
2. Immediately publish historical L4YAML findings in all live PR reports.
   Rejected: a frozen source witness must not attach to changed heads.
3. Accept projected witness tables directly in public webhook payloads.
   Rejected: a PR author could self-certify a synthetic counterexample.

## Contract

- `checkProjectionClaim(subject, claim, authority)` is pure. The claim names a
  target ID, protected requirement, and finite universe. The authority comes
  from a trusted caller, independently of the claim. Every finite row's source
  SHA must equal the authenticated GitHub PR head, and the universe SHA must
  match independently supplied authority. Missing evidence gives UNKNOWN.
- A qualified same-observation/different-verdict pair becomes a `BLOCKED`
  claim in the normal Check results, with `terminal_form=NAMED_OBSTRUCTION`,
  the witness IDs, source binding, and restricted proof scope. Provenance-only
  collisions and collision-free finite sets stay `UNKNOWN` for target logic.
- Existing `resolve` produces proposals only from explicit
  `allowed && source_authoritative` plans. No automatic execution or merge.
- Existing `monitor` withdraws the claim on a new head when the prior witness
  does not requalify. Independent source, data and policy must be newly bound.
- Live GitHub Check readback continues to exclude MathGraph's own Check runs;
  it is not an oracle for its own semantic warrant.
- No Cloudflare event handler changes, deployment, new permissions, or
  publication in this slice. First-party readback can use the new optional
  adapter when the host has qualified evidence. General witness discovery is
  still a separate UNKNOWN capability.

## Anti-goals

Do not infer a semantic claim from a green CI job, a PR-authored witness, an
unqualified table hash, an `UNKNOWN` row, or an old historical proof. Do not
convert a finite non-collision into universal sufficiency. Do not attach the
frozen L4YAML case to a different PR head.
