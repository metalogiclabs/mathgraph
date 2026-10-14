# Independent review of PKC’s provenance–tape correspondence

**Prepared for:** Nicolas Rouquette and Xiaolan Xu  
**Prepared by:** Heath, MathGraph / Metalogic Labs  
**Reviewed repository:** [`nasa-jpl/propertykindcalculus`](https://github.com/nasa-jpl/propertykindcalculus)  
**Pinned revision:** [`6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9`](https://github.com/nasa-jpl/propertykindcalculus/commit/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9)  
**Review date:** 2026-10-03

## Finding

At the reviewed revision, the central computer-science claim is no longer merely a conjecture. PKC contains Lean proofs that an accepted correspondence between a well-formed metrology provenance hypergraph and a computational tape graph has two complementary forms:

1. The provenance labelled transition system is **weakly bisimilar to the actual computational tape graph**. Numerical operations internal to one provenance occurrence are silent steps.
2. The provenance system is **strongly bisimilar to a formally contracted tape graph** in which each accepted realization subgraph is collapsed to one ordered hyperedge.

The weak theorem is explicitly factored as the strong theorem composed with the weak contraction relation. PKC also proves the semantic consequence that matters for the methodology: for an accepted match, every tape dependency in an output cone comes from a declared provenance influencer, and every observable tape edge is authorized by a declared occurrence with the stated kinds.

This validates the theoretical core of “write once, correctly; go fast, automatically,” subject to the hypotheses stated below. The main unfinished engineering step is automatic construction of the match certificate for a recorded tape. The current code decides whether a supplied match is valid; it does not yet infer that match for an arbitrary recorded computation.

## Claim-by-claim assessment

| Claim | Status at the pinned revision | Evidence and qualification |
| --- | --- | --- |
| Provenance hypergraph and computational tape are weakly bisimilar | **Proved** | [`Match.isWeakBisimulation_weak`](https://github.com/nasa-jpl/propertykindcalculus/blob/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9/graph/PropertyKindCalculus/Graph/Bisimulation.lean#L647-L655) proves weak bisimulation under graph well-formedness and accepted matching. |
| Compaction strengthens the relation to strong bisimulation | **Proved for the defined contraction** | [`Match.isBisimulation_contracted`](https://github.com/nasa-jpl/propertykindcalculus/blob/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9/graph/PropertyKindCalculus/Graph/Bisimulation.lean#L513-L537) proves strong bisimulation between the provenance LTS and `m.contracted g`. |
| The contraction preserves the behaviour of the actual tape | **Proved as weak bisimulation** | [`Match.isSWBisimulation_contraction`](https://github.com/nasa-jpl/propertykindcalculus/blob/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9/graph/PropertyKindCalculus/Graph/Bisimulation.lean#L543-L646) relates the contracted graph to the uncontracted tape. |
| The compacted tape is literally isomorphic to the provenance hypergraph | **Qualified, not the exact named Lean theorem** | The Lean theorem establishes strong bisimulation. The blueprint describes ordered-hypergraph isomorphism only after quotienting two node-identity mismatches: derivation equality and nominal branch selection. That stronger wording should retain those qualifications unless a separate isomorphism object and theorem are added. |
| No undeclared raw value can influence a result | **Proved conditionally on the seal hypotheses** | [`TapeSeal.semantic_seal`](https://github.com/nasa-jpl/propertykindcalculus/blob/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9/torch/PropertyKindCalculus/Torch/Paradigm/TapeSeal.lean#L135-L162) proves output-cone dependence, source coverage including baked constants, and authorization of observable kind transitions. |
| A recorded tape can be checked automatically | **Partly complete** | Acceptance is a Boolean decision procedure over an authored match. A matcher that derives the match from the tape is still listed as open in the [status ledger](https://github.com/nasa-jpl/propertykindcalculus/blob/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9/blueprint/PropertyKindCalculusBlueprint/Chapters/Capstones.lean#L663-L677). |

## What “accepted correspondence” means

The result is conditional, but the condition is concrete and executable. [`Match.accepts`](https://github.com/nasa-jpl/propertykindcalculus/blob/6d3da52c1db4a085ac7ea561dd8f125e7cdb0fc9/PropertyKindCalculus/Paradigm/TapeGraph.lean#L318-L323) checks all of the following:

- the tape is ordered;
- every declared provenance node has one or more in-range tape components;
- component-table keys are unique and name only declared nodes;
- no tape vertex is a component of two provenance nodes;
- tape leaves are exactly components of declared sources;
- every non-wire realization is closed, interior-private, progressing, frontier-using, and composed of operation vertices;
- realization interiors are mutually disjoint and disjoint from observable components;
- every tape operation is covered;
- every provenance occurrence is realized, and every realization names a real occurrence.

These clauses rule out precisely the ways an implementation could smuggle an undeclared dependency across the boundary. In particular, `leavesAreSources` covers both named inputs and constants: an unlisted baked constant causes acceptance to fail.

## Why the result is substantive

The repository includes a concrete model for

\[
y = a \cdot b + e
\]

where complex multiplication expands to four real products inside the tape. The four partial-product vertices are implementation detail and therefore silent in the weak relation. The corresponding match is accepted by kernel reduction, and all three bisimulation theorems are instantiated.

The test then mutates the tape by adding a constant leaf that the provenance graph does not list. The same match is rejected specifically by `leavesAreSources`. This gives the result a positive witness and a targeted negative witness; acceptance is not vacuous.

The pinned axiom profiles are:

- strong contracted bisimulation: `propext`, `Quot.sound`;
- weak contraction: `propext`, `Quot.sound`;
- composite weak bisimulation: `propext`, `Classical.choice`, `Quot.sound`;
- semantic seal: `propext`, `Classical.choice`, `Quot.sound`;
- accepted-instance / rejected-mutant witness: `propext`.

No `sorry` or `admit` placeholder carries these claims.

## Exact interpretation for the methodology

The formal result supports the following statement:

> If the PKC provenance graph is well formed, the recorded tape is well formed, and the Boolean acceptance checker accepts a match between them, then the tape’s observable behaviour implements the provenance graph up to silent internal numerical steps. Contracting those accepted internal realization subgraphs yields a strong bisimulation. Under the denotation bridge, the computation depends only on provenance-declared influencers and performs only provenance-authorized observable kind transitions.

This is enough to justify the architecture’s theoretical separation:

- Scientists author and verify the metrological structure in the provenance layer.
- The runtime may autoscale, checkpoint, resume, or fuse numerical work without changing that observable structure, provided its recorded tape still admits an accepted match and the execution/code-generation layers preserve the tape denotation.

The bisimulation theorem does not by itself verify the scheduler, checkpoint implementation, GPU compiler, or generated machine code. Those systems may change operational details freely, but the relevant tape and denotation obligations still have to be discharged.

## Remaining work

The highest-value next step is to implement the matcher that constructs `Match` from a harvested provenance graph and recorded tape, then run it on the dielectric worked model. The repository already identifies the required evidence:

1. ports matched by name;
2. constants matched by recording site;
3. each occurrence matched by a realization table for its family and carrier;
4. either recorder scope markers for each member call, or a documented widening of membership to the dependency closure visible in the tape.

Once that instrument exists, the current Boolean acceptance checker and the proved theorems turn its successful output into a certificate. Until then, the theoretical statement is proved, while end-to-end automatic certification of an arbitrary recorded model remains incomplete.

## Reproduction

The reviewed targets were rebuilt with Lean 4.34.0:

```text
lake build PropertyKindCalculus.Graph.Bisimulation \
  PropertyKindCalculus.Tests.Graph.Bisimulation \
  PropertyKindCalculus.Torch.Paradigm.TapeSeal
```

The proof entered the repository in commit [`6a249cf`](https://github.com/nasa-jpl/propertykindcalculus/commit/6a249cf), “Prove the three capstone theorems and their supporting lemmas,” and is present at the pinned reviewed revision.

## Related contribution trail

This review is part of the same MathGraph / JPL collaboration trail as the L4YAML grammar contribution:

- [L4YAML pull request #1](https://github.com/nasa-jpl/L4YAML/pull/1)
- [Published L4YAML commit `097b7a2`](https://github.com/metalogiclabs/L4YAML/commit/097b7a29428d1ba8e350e40628cd33a19d191a08)
- [L4YAML contribution branch](https://github.com/metalogiclabs/L4YAML/tree/heath-serialization-wellformed-v1)
- [JPL target branch `fix-a-grammar-completeness`](https://github.com/nasa-jpl/L4YAML/tree/fix-a-grammar-completeness)
- [ROS checkpoint](https://app.notion.com/p/3ee3e523d7ab81f0a3cec19bb3d35cee?pvs=204)
