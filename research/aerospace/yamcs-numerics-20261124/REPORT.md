# Commercial aerospace assurance — Yamcs iteration, 24 November 2026

## Warrant and boundary

**WARRANTED / FINITE_COUNTERMODEL:** native Yamcs Java APIs at `4af5abd2b5d8535f77e902de717c77d657f0093e` violate numerical value-preservation or representability contracts on selected synthetic inputs. These are ordinary software correctness discrepancies. No Yamcs server or operational telemetry, spacecraft or command link was accessed or started. No operational safety outcome is inferred.

Initial source-pinned run: https://github.com/metalogiclabs/mathgraph/actions/runs/45336875641

Harness commit: https://github.com/metalogiclabs/mathgraph/commit/0fb91a3a59bb735b13a6cc9517429f837bbdf4b9

Extension with software-parameter consumer and dependency hashes: https://github.com/metalogiclabs/mathgraph/commit/88c85b3d21ede2414096b8d78626c4e105595076

**Completed consumer qualification:** https://github.com/metalogiclabs/mathgraph/actions/runs/45337311923

## Objective → residual → experiment → evidence

Objective: establish whether unsigned numerical representations retain their mathematical meaning across existing public conversion APIs. Residual: source inspection alone could not establish executed behavior or distinguish value conversion from intentional bit reinterpretation.

The cheapest decisive experiment calls the original implementation using exact Java Value objects, independent BigInteger range and floating-conversion oracles, decimal parsing controls, and positive/negative boundary inputs. It checks acceptance, rejection and returned mathematical value separately. It does not substitute a rewritten implementation for Yamcs.

The unmodified native Maven build ran nine original tests: IntegerDataTypeTest (4), DataEncodingUtilsTest (3), DataTypeProcessorTest (2). All passed. A separate strict regression suite then failed on precisely the predicted contract assertions, with zero test errors or skipped cases. A five-line candidate production repair made all selected cases pass. Withdrawing the patch restored byte-identical observation tables and the same assertion failures. The nine original tests passed again with the repair.

| Contract family | Selected checks | Original discrepancies | After repair | After withdrawal |
|---|---:|---:|---:|---:|
| Typed integer conversion | 1,512 | 74 | 0 | 74 |
| Integer to floating type | 168 | 6 | 0 | 6 |
| UINT64.toLong documented contract | 21 | 21 | 0 | 21 |
| SoftwareParameterManager.transformValue consumer | 50 | 13 | 0 | 13 |

These are selected boundary checks, not population failure rates. The first three rows are contract families, not independent catalogue discoveries. The consumer row replays the same integer/floating mechanisms through an existing caller; it is not an additional discovery. Unsigned carrier interpretation and range computation contribute to the integer family.

The second run repeats all three original matrices with byte-identical baseline tables and adds 50 ordinary whole-parameter transformations. Thirteen consumer checks disagree with the mathematical oracle, including rejection of valid UINT32 values, acceptance outside narrow target ranges, negative signed64 results and wrong floating values. No manager instance, server or link is started. All 50 pass with the same repair; withdrawal restores all original rows. The nine original tests pass again. Broader regression compatibility is not established.

Concrete witnesses:

- UINT32 `4294967295` → signed 64-bit engineering type returns `-1`; the destination can represent the positive input exactly.
- UINT64 `4294967295` → signed 32-bit type is accepted as `-1`, whereas decimal parsing correctly rejects it as unrepresentable.
- UINT32 `2147483648` → double returns approximately `9.2233720347072922e18`, instead of exact `2147483648.0`.
- UINT64 zero → `toLong()` throws; UINT64 maximum → `toLong()` returns `-1`. The documented contract requires the opposite admission decision in these two cases.

Of the 74 integer discrepancies, 21 concern representable inputs and 53 concern invalid inputs incorrectly accepted. All 1,512 decimal-route controls agree with the independent range oracle. All 168 Value.toDouble controls agree with the exact-number floating oracle. Ordinary documented floating rounding is allowed by the oracle; it is not counted as a defect.

Contract authority: DataTypeProcessor.convertEngValueForType documents conversion to the target engineering type and rejection when it cannot convert. DataType.convertType documents canonical representation and rejection when a value cannot be represented. IntegerDataType and its original boundary tests explicitly enforce bit size and signedness. Value.toLong explicitly promises a signed long and an exception for unsigned values above Long.MAX_VALUE. These are separate requirements from raw bit-level encoding APIs that intentionally truncate.

## Independent evidence verification

The first native artifact contains 40 files. Downloaded ZIP SHA-256 equals GitHub's digest: `d531eb6d0c57bf173c34003ef7926329249e0f84b1b26385ccd879c0bb0f5883`. ZIP integrity and all 39 manifest hashes independently passed. Inspected original Maven logs, JUnit XML, raw TSV, exact patch and before/after/withdrawal records. Baseline source hashes match a separately cloned current upstream checkout. A green workflow alone was not used as a warrant.

The final consumer artifact contains 44 files. Independently downloaded SHA-256: `8f61a67b8aab53df34572790c30f29a0edd6b353e5eb7e7912daaa6789ff597d`, matching GitHub. ZIP integrity and 43/43 manifest entries pass. It includes SHA-256 identities for 52 resolved dependency jars. Artifact: https://github.com/metalogiclabs/mathgraph/actions/runs/45337311923/artifacts/14895180056 . The upstream master was rechecked after execution and remains the tested commit.

A separate Python verifier independently recomputes integer ranges, admissibility, floating expectations and every match/mismatch classification from the downloaded native observations, rather than trusting the Java probe's match flags. All four matrices agree before, after and upon withdrawal; the original nine-test baseline and four strict failure/pass/failure JUnit outcomes are independently checked. The verifier and its receipt are retained with the evidence package.

Local attempts are retained as environmental/harness lineage: unavailable Maven network configuration; compatibility data (`ct.sym`) missing from the local Java installation; a local build using a disclosed build-only compatibility adjustment was terminated with signal 9 before test execution. Cause of that termination is unestablished. None of those attempts is evidence of a Yamcs defect. The hosted warrant uses full Temurin JDK 17 and the original POM without that adjustment.

## Campaign reconciliation

Research OS and Campaign Registry were fetched. Their current readable contents did not contain these named commercial campaign investigations. The separate Canonical Research State page repeatedly failed retrieval with transport closure; browser fallback required sign-in. Its contents were not presumed known and the page was not altered. This checkpoint is reconciled to current GitHub source, actual test receipts and issue history.

| Project | Current source rechecked | Evidence and publication state |
|---|---|---|
| Sedaro Model Exchange | `7c03c2044d24ab091ee6e510dba4b84a7f055506` | Bounded index propagation/repair evidence verified; issue #5 exists, open, zero replies at check; contract clarification pending. |
| Antaris Python XTCE | `807ef4e16f2fdf6fa5d742e36242751ed3809499` | 20 original tests; 5 root and 10 child-local controls; 10 root/child mismatches; issue #6 already exists, zero replies at check. |
| OpenC3 COSMOS | `208e960798cabf18a4a6a703805c173ffdc4f4e4` | 25 original tests; 8/21 JSON and packet discrepancies; binary and Ruby controls 21/21. Issue #4432 was submitted by Heath. Its sole reply is crawlchat[bot], not human maintainer acceptance. |
| Dawn public forks | No new native execution this iteration | Earlier rounding-documentation observation retained as user-supplied lineage; no new functional defect or operational-relevance warrant. |
| Yamcs | `4af5abd2b5d8535f77e902de717c77d657f0093e` | Candidate promoted to bounded native numerical contract counterexamples; upstream publication not authorized or performed. |

Sedaro, Antaris and COSMOS archives were downloaded independently, their SHA-256 digests matched GitHub upload records, and every archive passed ZIP integrity. Actual tests, controls and raw observations were inspected; Cosmos/Antaris raw assertions were independently recomputed. Exact archives and hashes are retained with this checkpoint.

Publication links:

- https://github.com/sedaro/model-exchange/issues/5
- https://github.com/antaris-inc/python-xtce/issues/6
- https://github.com/OpenC3/cosmos/issues/4432

## Catalogue coverage

Actual catalogue retrieved from commit `58ddb19e00e6097d2196d7a1a4760ccb653924d5`, path `integrations/mathgraph-check-github/catalogue-check-v1/catalogue.json`; revision `2026-11-22-r2`. It has exactly 104 candidate search prompts. The attached assessment records every original ID/title/prompt: 41 have an explicitly scoped methodological, source or experiment assessment; 63 remain UNASSESSED. This is not a 41-detector pass count, a full repository audit, or evidence that unassessed modes are absent. Primary numerical mechanisms span several catalogue facets; facets are not additional discoveries.

## Novelty, norms and collaboration

Read README, AGPL license notice and the PR template; no separate CONTRIBUTING or issue template was present in the inspected tree. Yamcs asks for discussion before non-trivial contributions and a CLA for such patches. No CLA was signed. Existing JUnit 5 style and precise regression reports are the appropriate presentation.

Related history was inspected: #776 fixes signed bit counting; #1102 concerns comparison evaluation; merged #1191 changes MatchCriteriaEvaluatorFactory and its comparator regression; merged #1198 changes raw integer encoding/decoding. They do not modify the current conversion or UInt64Value.toLong paths tested here. Focused issue searches for unsigned, DataTypeProcessor, integer conversion, UInt64Value and toLong did not identify a matching report. This is a bounded novelty check, not an exhaustive guarantee.

External contribution review in #1201 shows maintainers asking for exact CCSDS semantics, precise leap-second admission and explicit configuration contracts. This supports a concise issue with minimal examples and a discussion of intended conversion semantics. It is evidence of constructive technical review, not interest in hiring MathGraph.

OpenC3 LICENSE.md and CONTRIBUTING.md were also read. Builder's License V2 has commercial-use restrictions and broad contribution terms. No proprietary MathGraph kernel code or new OpenC3 patch was submitted in this iteration.

## Synthesis: test the structure rather than repeat the analogy

Elementary mathematical criterion: if a downstream question q is recoverable solely from representation f(x), then f(x)=f(y) implies q(x)=q(y). Necessity follows by substituting equal representations into the downstream function. Conversely, if q is constant on every fiber of f, a well-defined answer function exists on the image of f. This is a reusable correspondence criterion, not a new discovery or a proof of commercial advantage.

COSMOS supplies native collision witnesses: `2^53` and `2^53+1` become the same integer after the float intermediate. Sedaro's empty-diff result similarly omits a distinction its model query observes. Antaris shows why a matched encode/decode round trip can remain positive when both use the wrong namespace.

Yamcs sharpens the hypothesis. The tested UINT32→signed64 subset has 15 distinct mathematical inputs and 15 distinct returned values, yet three returned values are wrong. Thus information erasure is not necessary for every observed conversion error; injectivity alone does not establish correctness. Required semantic correspondence must also commute: interpreting the transformed representation must give the required interpretation of the source. This extends the useful search strategy from collision finding to cross-representation correspondence and admissibility checks.

Predictive usefulness is only a bounded observation: the earlier campaign structure directed this numerical investigation and produced new native counterexamples. No preregistered blinded comparator was run. Comparative advantage over competent ordinary unit testing, overall detector performance, customer demand and commercial value remain UNKNOWN.

## Expected value and continuation

**Recommendation (inference): prioritize the Yamcs engineering team at Space Applications Services for the next bounded investigation and collaboration attempt.** It has current development, explicit conversion contracts, useful original tests, public examples of constructive external review, and a commercial support/custom-development business. Those facts establish a plausible route to a conversation, not demand for independent assurance.

Within this campaign: Yamcs ranks first for new correctness work; OpenC3 second for completing the existing focused contribution after human review/authorization; Antaris third pending namespace-contract clarification; Sedaro fourth because its public repository last changed in February 2025; Dawn remains lower until current public-code relevance is established. This ordering is qualitative, not a statistically estimated revenue score. No company or maintainer was contacted.

Highest-leverage residual: broader regression compatibility and maintainer acceptance of the small conversion repair. The next useful experiment after the consumer extension is a broader native Yamcs regression run with the patch, preserving the existing unsigned-comparison and encoding regressions, before proposing an upstream patch. Human interest and willingness to pay require their own evidence.

Commercial sources: https://yamcs.org/about and https://yamcs.org/enterprise/ (fetched 24 November 2026). The latter offers support and new features on time-and-material or fixed-price terms. That describes their business model; it does not show they buy outside assurance.
