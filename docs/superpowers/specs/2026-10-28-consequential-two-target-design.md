# Consequential two-target evidence-frame experiment — design

Date: 2026-10-28
Status: implemented V2 on protected-frame base `0aab2b4d`; research-only,
no release authority; independent review and CI qualification tracked separately

## Intent

Test the strongest currently actionable Metatron/MathGraph hypothesis: a source-bound
verification memory can preserve *required* obligations independently of what an
authenticated packet says, identify the missing native observation, and selectively
withdraw reliance when its support disappears. Exercise one unchanged generic
evaluator on two independently sourced Go cases without changing the trusted
Metatron Nucleus or the deployed GitHub App.

The immediate falsifier was retained on the exact GOETH V19 research head:
a signed owner packet may (a) relabel two untested FCU obligations as true or
(b) omit them entirely; the packet-relative evaluator admits both. The actual
native evidence supports only a narrower predicate and Engine controls.
**Canonical correction (2026-10-28):** newer research commit `0aab2b4d`
already introduced the protected-frame evaluator and mapped the pinned GOETH
historical predicate. This experiment does **not** claim to invent that repair.
Its incremental test is an independently byte-pinned wrapper of that same
kernel, a second target, and actual Metatron lineage/revocation replay.

## Goals and acceptance

1. Keep the existing protected-frame `assessWarrant` kernel and historical
   signed-packet negative controls unchanged. Add only an opt-in source/receipt
   wrapper that delegates the consequential decision to that kernel.
2. Freeze a byte-digested, independently supplied obligation frame for each
   exact source subject and policy-version label. A signed packet cannot choose
   the required set or observation ceiling. Malformed, wrong-source,
   wrong-digest and missing frames ABSTAIN, with a named residual.
3. Require an exact, independently rechecked native-receipt state **and** a
   matching, separately adapter-derived named observation. Native state alone
   cannot magically warrant every requirement in a frame. A historical Go
   receipt is *not* fresh source correctness or a normative owner grant.
4. Apply the same evaluator, with no per-target code changes, to GOETH V19 and
   goccy/go-yaml PR #958. The subject-specific frames are declarative, reviewed
   research fixtures; they are **not** independent owner policies.
5. Test a non-vacuous frame-relative positive, real residuals, direct false
   evidence, two misleading signed packets, expiry, revocation, wrong head,
   source withdrawal and cold replay. Preserve independent Metatron logging
   where the original pinned Nucleus is actually available.
6. Compare against a competent fixed-frame, fully informed conventional rule
   evaluator and the old packet-only evaluator. Report ties honestly; never
   imply a frontier-agent or commercial advantage from a weak heuristic.
7. All Check conclusions remain `neutral` / `ADVISORY_ONLY`. No owner-granted
   merge, production rollout, external side effect, upstream write or new trust
   kernel is authorized.

## Approaches considered

1. **Modify the existing signed-packet evaluator directly.** Smaller surface,
   but would erase the original failure and conflate provenance with meaning.
2. **Byte-pinned adapter to existing protected-frame evaluator (chosen V2).**
   It preserves previous negative lineage and reuses the already qualified V0
   semantics instead of maintaining two competing admission kernels. The cost
   remains an externally reviewed mapping from native receipt scope to named
   research obligations.
3. **Universal autonomous protocol invention now.** Not credible from these
   sources: the constructor/semantic language and owner permissions are not
   autonomously discovered. This remains a distinct L7 experiment.

## Trust boundaries

- `owner-auth.mjs` checks exact signed bytes under a separately configured key;
  it does not check human owner legitimacy or policy truth.
- `geth-v19-evidence.mjs` and `external-native-receipt.mjs` are the existing
  read-only, source-pinned historical adapters. The adapter's qualified state
  must be produced by trusted caller code, not a PR or signed packet field.
- A separately pinned frame enumerates exact protected obligations, frozen
  policy-version label, native receipt profile and **ceiling** for each
  historical observation. GOETH's positive `predicate` observation is returned
  by the existing native adapter; goccy's 69/0/20 typed observations are a
  research-only projection of separately pinned native report bytes after the
  existing adapter validates the source, report and GitHub metadata. Neither
  side alone confers truth. No frame proves real owner intent or completeness.
- Metatron Nucleus remains byte-identical. Append-only event and revocation
  records are derived memory, not permission to execute a consequential action.
- Frames and native observations are not interchangeable: a signed assertion,
  even under an authentic owner key, cannot rewrite a native test result.

## Data and interfaces

`assessConsequentialFrame({snapshot, verifiedOwner, frameBytes,
frameSha256, nativeReceipt, asOf})` returns `decision`, `residuals`,
`future`, `boundary`, `missing_observations`, `source`, `native_profile`.

`frameBytes` is exact UTF-8 JSON, schema
`mathgraph.consequential-research-frame.v1`, with subject/action/scope, an
exact native profile, policy-version label and nonempty unique required obligations.
Each obligation declares independently reviewed expected native ceiling (`WARRANTED_TRUE`,
`WARRANTED_FALSE` or `INSUFFICIENT`) *if and only if* the named exact native
receipt **and its separately sourced, identically named observation** qualify;
no observation means `INSUFFICIENT`. The digest must be supplied independently
of the bytes. The adapter constructs an explicit `mathgraph.protected-frame.v0`
and delegates to `assessWarrant(snapshot, contract, asOf, protectedFrame)`.

Research source cases:

- GOETH V19: `metalogiclabs/go-ethereum#19@a04aa77...`; historical native
  predicate is qualified; `remote_conflicting_fcu` and `concurrent_fcu` are not.
- goccy/go-yaml PR #958: historical 130-case, native source-authored evidence
  qualifies a bounded 69 repaired / zero introduced-regression observation;
  the 20 inherited cases are not silently declared repaired by the PR.

## Non-goals and promotion boundary

This is **WARRANTED_BOUNDED** only if exact tests and native receipt readbacks
pass. It is not a novel GOETH protected-frame repair, L7 autonomous constructor
invention, a fresh blind target, a
new Go execution, an independently authored policy oracle, a human pilot, a
general safety theorem or an authorized production release. Those stay
`UNKNOWN` until separate native execution, real owner approval and a strong
same-information external comparison. A correct baseline TIE is expected and
must not be turned into claimed superiority.
