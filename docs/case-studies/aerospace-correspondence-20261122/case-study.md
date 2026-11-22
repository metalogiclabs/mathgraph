# Preserving meaning across aerospace software boundaries

## Trajectory frames, runtime requirements, and downstream meaning

**Heath Sanchez · Metalogic Labs · 22 November 2026**  
Technical working draft. Reproduction and review materials accompany this note.

## Abstract

A successful software operation establishes only the property it actually checks. An aerospace engineering conclusion also depends on correspondence between the requirement, its representation, and the downstream interpretation. This case study examines that obligation through an accepted trajectory-export correction and a controlled runtime-monitor experiment. In Nyx, table-level reference-frame metadata could misdescribe the states selected for export; the accepted repair enforces the existing one-frame-per-table contract. In a freshly replayed FRET-to-C2PO-to-R2U2 pipeline, a same-sample COAST observation satisfies the exported response interval `[0,7]`, while a deliberately constructed `[1,7]` comparison requires a later observation. Both monitors agree with their respective formulas on the tested traces. The experiment therefore isolates a requirement interpretation that execution cannot choose for its owner. An accepted L4YAML interface correction supplies a further concrete example of a source distinction lost in transport. Together, these cases support a practical discipline: state the correspondence obligation, exercise the actual consumer, retain controls, and restrict the conclusion to the evidence obtained.

## 1. The engineering question

Suppose a trajectory exporter completes successfully, or a runtime monitor reports that a temporal formula holds. What engineering conclusion follows?

That answer depends on several facts that can sit outside the local operation: which reference frame gives the numbers their meaning; which samples a temporal interval includes; which physical signals correspond to the propositions; and whether the formal statement expresses the requirement that the responsible engineer intended. These facts are testable or reviewable obligations. A passing component check does not establish them automatically.

This note makes the question concrete using two different kinds of evidence. The Nyx case is a historical defect with an accepted upstream correction. The runtime-monitor case is a fresh reproduction of an existing controlled experiment that distinguishes two explicitly different temporal requirements. The latter is not a claim of an upstream FRET or R2U2 defect. Keeping these evidence classes distinct is central to the result.

The common object of investigation is the relation between a source meaning and the meaning used by the actual downstream consumer. For a transformation `T`, the relevant obligation is that interpreting `T(x)` preserves the required observation of `x` on a stated domain. Defining that observation is part of the engineering problem; an experiment cannot silently supply missing mission intent.

## 2. Accepted aerospace correction: trajectory reference frames

Nyx stores a single reference frame in the metadata of a trajectory Parquet table. Before the correction in upstream pull request #615, the exporter derived that metadata from the first state in the source trajectory. Export filtering could exclude that state. A selection could also contain states with different frames. On import, the table frame was assigned to the rows, so the round trip could change the physical interpretation of selected states. [1]

The failure was in the relationship between the selected rows and their shared frame label. Successful serialization and plausible numerical values did not establish that relationship. A representation with one frame label also cannot faithfully describe an arbitrary selection containing several frames under that same contract.

The accepted correction derives metadata from the selected rows, rejects mixed-frame selections, and reports an empty materialized selection explicitly. That last guard does not establish safe handling of an originally empty trajectory through every earlier access. The upstream regression tests cover homogeneous round trips, mixed-frame refusal, and filtered selections. The accepted PR head is `7d3253506471a7b9ff58e87fbee50e4a025e0b3f`; the upstream merge is `71e31c137bfe2fea641a21455febb84c936fc409`. [1,2]

| Selection | Required relationship | Corrected behaviour |
| --- | --- | --- |
| Nonempty, homogeneous frames | Table frame equals the selected rows' frame | Export and preserve that frame |
| Mixed frames | One shared label would misdescribe at least one row | Reject the selection |
| Filter removes the original first row | Metadata follows the retained rows | Derive metadata from the retained selection |
| Empty materialized selection | No selected row supplies a frame | Return an explicit error at the added guard |

This session rechecked the pinned source and historical hosted test receipts. It did not compile Nyx locally: a Rust toolchain was unavailable. The historical native research run records the original failing mixed/filtered cases and five passing corrected cases. That experiment used a disclosed compatibility shim in an unrelated nonpremium module; the audited export/import sources were checked before applying the targeted repair. The shim was not part of the accepted production PR. [3]

In the upstream workflow associated with the accepted PR head, Coverage, Check and Tests succeeded; the overall workflow failed because its Lints job failed. The coverage job executed synthetic merge `78ab554425ee06caa844260f27076f4da8a66d73`. Its Git tree, `6d8f077d27a158c52171ce7a6f8c10aae75a8c60`, is identical to the accepted upstream merge's tree. This binds the recorded coverage tests to the accepted merged source while preserving the distinct commit and workflow identities. [2,8]

The source and tests warrant the scoped export correction. They do not establish complete trajectory correctness, all import-side validation, or flight qualification. This note also makes no fresh claim about the magnitude of a propagated orbital error: that calculation was not rerun here.

## 3. Fresh native experiment: does the current sample count?

The runtime experiment reuses the existing MathGraph source-pinned native replay, rather than introducing a new monitor implementation. It executes the original FRET parser/exporter, original C2PO compiler and a freshly compiled original R2U2 C monitor. The selected sources are FRET `cf0f913cc15c41705e803593297e89cd6056b839` and R2U2/C2PO `2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a`. [4-6]

The selected FRETish requirement is:

> whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST

The actual FRET export is:

```text
(BOOST -> (F[0,7] COAST))
```

A separate, researcher-constructed comparison changes the lower interval bound:

```text
(BOOST -> (F[1,7] COAST))
```

The second formula is not FRET's output for the selected sentence. It is not an owner-approved repair. Its purpose is to distinguish whether a COAST observation at the trigger sample can satisfy the response, or whether satisfaction must include a later observation.

The interval is interpreted in sample indices in this experiment. Calling those indices physical seconds requires an additional sampling-period and signal-binding contract. This replay does not establish a spacecraft or rocket telemetry configuration.

### The separating trace

Use eight Boolean samples. BOOST and COAST are both true at sample 0. Both are false at samples 1 through 7. At evaluation index 0, the source formula is true: the interval `[0,7]` includes the current sample. The constructed `[1,7]` formula is false: there is no later COAST observation in that interval.

| Input scenario | Source `[0,7]`, at index 0 | Constructed `[1,7]`, at index 0 |
| --- | --- | --- |
| COAST only at the BOOST sample | True | False |
| COAST at the following sample | True | True |
| BOOST occurs; COAST never occurs | False | False |
| BOOST never occurs | True because BOOST is false | True because BOOST is false |

The fresh main campaign checked four eight-sample scenarios, two formulas and eight decoded verdict positions per formula: **64/64 output positions agreed with a separately implemented Boolean oracle**. These are finite output observations, not 64 independent requirements or 64 discovered failures. Eleven existing contract controls passed. A clean monitor rebuild and separate assessor repeated those same 64 values and refused five mutations of actual generated artifacts. This was a separate process on the same machine, not an external institutional validation. The package records the compressed native monitor output and the decoded values, because output representation is itself part of the comparison boundary. Verdicts are attributed to evaluation indices; the table does not assert wall-clock emission at time zero. [4,8]

### What the comparison does and does not decide

Changing `[0,7]` to `[1,7]` requires a later COAST observation; it does **not** prohibit BOOST and COAST from overlapping. An additional native control sets BOOST at sample 0 and COAST at both samples 0 and 1. Both formulas hold. All 16 verdict positions of this fifth scenario agreed with the oracle; these are separate from the original 64-position campaign. A non-overlap requirement needs its own explicit formula and domain assumptions. [8]

The result isolates a question for the requirement owner:

**Does a COAST observation at the same sample as BOOST count toward the required response, or must satisfaction include a later observation?**

Native execution demonstrates the consequence of that decision. It does not establish which policy the mission should adopt. The retained result therefore reports the selected finite semantic comparison as supported and operational intent as unresolved. This is an example of productive abstention: the next missing evidence is a requirement decision, rather than another run of either monitor.

## 4. Supporting interface correction: distinct keys, wrong value

L4YAML provides a small corroborating example. Its Lean parser preserved the distinct YAML keys `"a"` and `"a\0b"`. The original C/Python interface could use a NUL-terminated lookup, collapsing the second lookup to the first and returning the wrong value. The accepted correction introduced length-aware byte interfaces and routed Python access through them. [7]

Here the source representation retained the distinction, but the handoff to the downstream lookup did not. This is the same kind of correspondence question in a different setting: which distinction is needed to preserve the required result, and does the actual transport and consumer preserve it?

The repair was merged into the upstream grammar branch. This note uses that accepted public correction as historical supporting evidence. It does not claim a fresh Lean/FFI build, whole-language YAML conformance, or that a parser proof established all foreign-function-interface obligations. The PR's reported test counts are bound to its named intermediate source revisions; they are not silently reassigned to the merged head.

## 5. A reusable investigation pattern

The cases motivate a compact procedure that can fit into an existing engineering workflow.

1. **Name the consequential claim.** For example, an exported row retains its reference frame, or a response may be satisfied at the trigger sample.
2. **Fix the relevant interpretation.** Identify the applicable contract, domain, units, sample mapping and authority. Record unresolved choices explicitly.
3. **Trace the actual representation change.** Follow selected rows, strings, formulas, signal maps and verdicts through the code that consumes them.
4. **Construct a separating example and ordinary controls.** The example should make the interpretations or outcomes differ. Controls should preserve intended valid behaviour and expose vacuity or overcorrection.
5. **Bind the conclusion to its evidence.** Retain source identities, execution method, actual outputs, limitations and the changes that require requalification.

For an established defect, an original/repair comparison can test causal attribution. For an unresolved policy choice, two successful implementations may expose a decision without selecting its answer. These are different outcomes of the same investigation discipline.

This is a synthesis of established verification and validation concerns, illustrated with reproducible cases. It is not a claim of a new universal mathematical law, a replacement for the cited tools, or measured superiority over conventional review. The prior equal-information comparator for the monitor experiment tied; this reproduction supplies no new comparative-performance result. [4]

## 6. Evidence and limits

| Claim | Evidence available | Status in this note |
| --- | --- | --- |
| Selected Nyx exports could receive misleading frame metadata | Pinned original/fixed source, accepted PR, historical native logs | Confirmed historical defect and scoped accepted correction |
| Source and comparison temporal formulas differ on the selected trace | Fresh original-toolchain execution and independent finite oracle | Supported on the tested domain |
| `[1,7]` is the correct operational requirement | No independently established mission-owner decision | Unresolved |
| Distinct L4YAML keys could collide in the C/Python lookup | Public accepted interface correction and its declared native evidence | Confirmed historical supporting case |
| MathGraph improves discovery or review cost over an equally informed reviewer | No new fair comparative trial; earlier selected comparison tied | Not established |

The sources concern public software and research examples. They do not establish operational deployment, agency endorsement, a customer engagement, or a joint publication agreement. The reproducibility package separates original source material, fresh observations and historical receipts.

## 7. Next consequential experiment

The useful next collaboration is one real, shareable requirement with a fixed intended interpretation. For a temporal-monitor case, that means agreeing the trigger, whether the current sample counts, the sampling and signal contracts, and the treatment of unavailable observations. For an export case, it means fixing the physical observation and representation contract that downstream tools require.

The immediate deliverable should be one end-to-end correspondence check against that agreed requirement, with a separating scenario, valid controls and a clearly bounded result. A correct result, a discovered discrepancy and a justified unresolved outcome should all remain reportable. Evidence of deployment benefit or reduced investigation cost would require a separate evaluation.

## References

1. Nyx, accepted PR #615, *Preserve trajectory frame identity in Parquet exports*. https://github.com/nyx-space/nyx/pull/615
2. Nyx accepted-head workflow #42937928116. https://github.com/nyx-space/nyx/actions/runs/42937928116
3. MathGraph native Nyx research workflow #42925288557. https://github.com/metalogiclabs/mathgraph/actions/runs/42925288557
4. MathGraph native rocket replay, PR #282 and pinned method. https://github.com/metalogiclabs/mathgraph/pull/282
5. FRET, pinned source `cf0f913cc15c41705e803593297e89cd6056b839`. https://github.com/NASA-SW-VnV/fret/tree/cf0f913cc15c41705e803593297e89cd6056b839
6. R2U2, pinned source `2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a`; runtime-monitoring documentation. https://github.com/R2U2/r2u2/tree/2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a ; https://r2u2.github.io/r2u2/Preliminaries/runtime_monitoring.html
7. L4YAML, accepted PR #290, *Preserve embedded NUL in Python scalars and mapping keys*. https://github.com/nasa-jpl/L4YAML/pull/290
8. This case study's fresh results and source reconciliation: [monitor evidence](rocket/evidence.json), [native receipt, assessor and extra control](rocket/results.json), and [Nyx checkout identity](nyx/records/checkout_identity.json). The original method is frozen at `2b0e21e94e64ca54ff35c1d4572c60b3b6049720`; the accompanying repository commit identifies this working draft and its new reproduction wrapper.

## Reproduction

See the accompanying README for the exact commands, prerequisites, source pins and result boundaries. The source manifest and results distinguish a native monitor rerun from an audit of historical Nyx receipts. No result in this note depends on private correspondence or an unpublished manuscript.
