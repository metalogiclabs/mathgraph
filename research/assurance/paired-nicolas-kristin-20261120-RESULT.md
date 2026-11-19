# Paired Nicolas–Kristin source-native assurance — exact evidence report, 20 November 2026

**WARRANTED_BOUNDED retrospective mechanics, NOT a demonstrated external human baseline improvement or operational approval.**

## Scope and frozen protocol

- Prior to these paired runs, protocol frozen at [bb158fb956ccd442354ded76581aa5867d3ec189](https://github.com/metalogiclabs/mathgraph/commit/bb158fb956ccd442354ded76581aa5867d3ec189).
- [Final tested exact-head CI run #44636745428](https://github.com/metalogiclabs/mathgraph/actions/runs/44636745428), source head **54c97df7665ec4f552ab40974a86fc31b94f82d0**: 4/4 jobs SUCCESS (original L4YAML, repaired L4YAML, authentic FRET/C2PO/R2U2, paired assessor).
- First attempt [#44636527483](https://github.com/metalogiclabs/mathgraph/actions/runs/44636527483) was RED in BOTH new Lean extraction harnesses because import had to precede the module-doc comment. Both original schema libraries compiled (original 7/7 Lean jobs, repaired 8/8) before new test harness failed. Reordered only the imported harness file; no source revisions, protected requirements or case lists changed. FRET job passed on first run.

## Nicolas — L4YAML Core Schema

Authoritative *conditional* interpretation: YAML 1.2.2 Core Schema §10.3.2, untagged plain scalars only.
- Original L4YAML source **4f31fef1f18e48b2204322b9a257b905340768c6**, `L4YAML/Schema/Schema.lean` Git blob **5fb5bccfd3b6cccd164f68a678ef2ea812803fe0**.
- Repaired source **d8f9865f222f75a15ffbd766837d340ba627d12a**, same path blob **bda62ed5cad86edcf2a1a40abe297053e80af226**.
- Actual Lean 4.35.0 `lake env lean --run` execution extracted 12 source-native `resolveImplicit` constructor tags from each exact source. Original 9/12 matched P and failed 3: `1_000` got int (required str), `0x` got int (required str), `1.` got str (required float). Repaired **12/12 matched**.
- Tag-only observation q_old led to eight consequential collision pairs under P. This is a meaningful distinction loss **only relative to the declared tag-only q**; full source text or a richer typed value could retain some distinctions. In particular, a `.str "1."` stores the text even if the tag output is wrong. Do not conclude all downstream decoders or interfaces lose the same information.
- Corrected q displayed zero pairwise collisions on the selected 12-case input set; neither version is thereby certified correct for all YAML values or every schema.

## Kristin — FRETish / C2PO / native R2U2

- Source FRET **NASA-SW-VnV/fret@cf0f913cc15c41705e803593297e89cd6056b839**; R2U2 **R2U2/r2u2@2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a**; original tested runner **metalogiclabs/mathgraph@2b0e21e94e64ca54ff35c1d4572c60b3b6049720**.
- Fresh exact-source native run produced 64/64 expected monitor verdicts (4 eight-tick Boolean traces × original source [0,7] and constructed challenger [1,7]).
- Relative to published original FRETish [0,7] P: native original variant **32/32 matches**; deliberately constructed [1,7] **31/32 matches**, with sole mismatch `simultaneous:0`.
- q = full frozen trace plus time point, deliberately sufficient to compute P on this finite domain, so the wrong challenger is diagnosed as *decoder/temporal-interpretation fidelity*, not lost trace information. [1,7] is NOT independently authorized policy, a bug in published FRET output or an accepted repair for an operational system.

## Shared rule, baseline and warrant

Identical formula used in both domains, on exact finite input X:
1. Distinction sufficiency `q(a)=q(b) ⇒ P(a)=P(b)`.
2. Actual fidelity `d(q(x))=P(x)`.

Observed diagnoses:
- L4YAML original: representation insufficient **at tag-only q** (3 pointwise errors; eight consequential tag-only collision pairs).
- L4YAML corrected: both checks pass on 12-case X.
- FRET source: both checks pass on 32 original finite verdicts.
- Constructed shifted FRET monitor: decoder-fidelity failure at 1 of 32 positions.
- Strong **equally-informed conventional script**, independently implemented pairwise/pointwise loops, matched all four classifications and all witness sets: **TIE 4/4**; NOT an external human reviewer.
- Original `mathgraph_check.boundary_warrant` from PR #261 (exact commit **1b06e7fb4a11a352a9c10916d68a6218dd508b38**) was invoked for two bounded receipts. Four scoped dependency mutations (YAML source and obligation; FRET evidence and verifier policy) withdrew the affected conclusion to UNKNOWN while the unrelated conclusion remained supported. No independent issuer or human-owner authentication was thereby created; receipt admission is the study's trusted adapter boundary.

Wall seconds logged by respective hosted native jobs: L4 original 35, repaired 26, FRET 23. These are build/replay measurements on CI, **not** matched investigator cost or evidence of a competitive speedup.

Artifact ZIPs downloaded and rehashed independently in model container; each matched GitHub's published digest:
- YAML original #14584222026 SHA256 **224b81b8fc1d935be9c2b83d42cce84769e62170b2574ac019144bb0d77e1364**
- YAML repaired #14584072333 SHA256 **b8e34acb14d16fbdfa9d5faca59cb2bfc5507711b86f0c45fb9d6684debfd258**
- FRET native #14584597463 SHA256 **2cbd6d8365a095109db0a653681e4c9b6f185bd438f5e31d9328becda14bf82c**
- Paired qualification #14583898374 SHA256 **e8d98b94d8ce6481cc74a0b3055c2baa9b2c4948b247e07d0bf65ace82e0b424**.

## Promotion boundary and cheapest actual next experiment

**WARRANTED_BOUNDED**: identical diagnostic predicate can be executed on two genuine source-pinned toolchains and their frozen finite X; explicit negative controls show different repair-class mechanisms; source-byte/evidence identity can be selectively withdrawn in the original typed carrier.

**REJECTED as demonstrated advantage**: that MathGraph uniquely discovers or classifies these already known cases. Conventional comparator tied on every observation and witness.

**UNKNOWN / NOT_RUN**: real upstream FGM/DVB/QVTS head-to-head against Nicolas, operational FRET mission-owner intent, two independent external requirement interpreters, genuinely blinded competent human conventional reviewer, native runtime coverage outside the 12/32 finite points, acquisition-cost advantage, permission to patch/merge/deploy, generalized independent discovery.

**Best next gate:** a held-out case with independently fixed source/requirement and actual consenting technical adjudicators, comparing equal-access adaptive MathGraph and conventional investigators with true full cost. No contacting Nicolas/Kristin, changing their repositories, merging PRs or deploying product was authorized or performed.
