# MathGraph Core V0

Core V0 is the small semantic graph kernel used by adapters. It stores
normalized objects, typed relations, verifier warrants, support lineage,
epistemic status, and the grammar that assigned meaning. Prover parsing,
proof replay, policy, and application-specific source names stay outside the
kernel.

## Data model

\[
G=(O,E,W,S,\Gamma)
\]

- `Object`: normalized meaning under one grammar. Its ID hashes the grammar
  ID, semantic type, and canonical normal form. Surface spelling and theorem
  names are excluded.
- `Relation`: typed directed hyperedge over object IDs. V0 defines
  `SAME_MEANING`, `IMPLIES`, and `REFUTES`. Same-meaning and refutation are
  binary. The implication representation supports multiple inputs and outputs;
  automatic closure currently composes unary implications only.
- `Warrant`: external verifier outcome or a kernel-derived result with parent
  warrant IDs and a fixed rule ID.
- `Support`: revocable source digest and assumptions/authority references.
- `Grammar`: immutable identifier, version, and definition digest. Grammar ID
  changes whenever any of those fields changes.
- `Unknown`: typed unsupported-normalization residual. It is not an Object,
  so missing grammar coverage cannot accidentally create semantic identity.

## Identity and serialization

`.mg` is UTF-8 canonical JSON with format tag `mathgraph-core-v0`. Map keys and
collections are serialized deterministically; floating point values are
rejected. Each record carries its content ID, and loading checks both
canonical encoding and recomputed IDs.

Object identity hashes exactly:

```json
{"grammar_id":"…","semantic_type":"…","normal_form":{}}
```

The grammar ID incorporates grammar name, version, and definition digest. A
proof name or verifier run therefore cannot perturb semantic identity, while a
changed normal form or grammar version necessarily changes the object ID.

## Admission, closure, and revocation

`normalize` delegates to an injected adapter normalizer. Unsupported or
non-canonical output becomes `UNKNOWN_UNSUPPORTED_GRAMMAR`. `verify` checks
that an external evidence receipt is bound to the candidate and its evidence
digest; the kernel does not replay or authenticate the external verifier.
`admit` accepts only warrants whose subject, support, and parent references are
present in the graph.

Closure composes warranted same-meaning paths and unary implication paths.
Same-meaning supports substitution at either implication endpoint. A warranted
object plus a warranted implication path warrants its consequence. Derived
warrants retain their parent lineage. Closure does not infer reflexive
implications and ignores multi-source/multi-target implications until a rule
for them is defined.

Revocation marks a support inactive, recomputes effective warrant status from
support and parent lineage, and reruns closure. Independent alternate warrants
remain live. If positive and negative external warrants are both active, the
subject is `CONFLICTED`; neither result silently overrides the other.

## Cross-prover adapter boundary

`core_v0_family_adapter.replay_family` imports the existing bounded discovery
rows. A caller must provide the pinned source digests and verifier authority
references. The adapter quotients recognized source occurrences by canonical
claim ID, keeps unsupported surfaces as `Unknown`, and requires explicit
source/target claim IDs plus verifier authority before adding an implication.
Recognition by itself never creates a warrant.


## Discovery loop integration

Core V0 remains the semantic/evidential kernel; objective choice and attention
policy stay outside it. `discovery_candidate_sources.candidates_from_core_v0_graph`
round-trips and closes a copy of the graph, binds the resulting frontier to the
SHA-256 digest of that exact closed `.mg` snapshot, and emits only unresolved
subjects as advisory `DiscoveryCandidate` records.

Resolved `WARRANTED`, `REJECTED`, and `SUPERSEDED` subjects do not re-enter
the attention queue. Unsupported grammar residuals descend to representation
repair, revoked evidence descends to replay, conflicts descend to trust audit,
and otherwise-unwarranted semantic objects or relations descend to an explicit
verifier-contact boundary.

The scheduler still cannot promote truth. A selected continuation must return
through a verifier adapter and be admitted as a Core V0 warrant before it can
change durable semantic state.

Scheduler ranking metadata is also outside the evidence boundary. Attention
probabilities, taste scores, costs, and other policy values may use floating
point, but Core V0 canonical evidence deliberately rejects floats. A verifier
adapter must therefore project a selected continuation into the smallest
authority-relevant envelope: semantic subject identity, exact source identity,
verifier result, qualification boundary, and support digests. The policy that
selected a target is routing provenance, not evidence that the target is true.

This gives the bounded loop:

```text
generate -> normalize -> verify -> admit -> close
   ^                                  |
   |                                  v
DiscoveryScheduler <- unresolved Core V0 frontier
```

The intended compounding invariant is: once closure can warrant a consequence,
that consequence disappears from future advisory attention until its support is
revoked or conflicted.
