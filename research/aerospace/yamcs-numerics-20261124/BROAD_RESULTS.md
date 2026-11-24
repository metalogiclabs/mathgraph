# Yamcs broader regression qualification — 24 November 2026

**QUALIFIED_BOUNDED_SELECTED_REACTOR.** The exact five-line repair from native parent run [45337311923](https://github.com/metalogiclabs/mathgraph/actions/runs/45337311923) preserves the default core reactor's tested behavior on all three upstream CI Java versions.

| Java | Original passed, before | Original passed, after | Original skipped, both | Added regressions passed | Numerical checks passed |
|---|---:|---:|---:|---:|---:|
| 17 | 1,151 | 1,151 | 14 | 4 | 1,751 |
| 21 | 1,151 | 1,151 | 14 | 4 | 1,751 |
| 25 | 1,151 | 1,151 | 14 | 4 | 1,751 |

The original case/status multisets match exactly. There were no failures or errors. Required original IntegerDataTypeTest, DataTypeProcessorTest, DataEncodingUtilsTest and UnsignedComparisonTest were all present and passed. The four added test methods cover 1,512 integer conversions, 168 floating conversions, 21 UINT64.toLong checks and 50 ordinary SoftwareParameterManager.transformValue checks; these are finite cases and overlapping contract facets, not 1,751 independent discoveries.

Execution authority: [run 45339330722](https://github.com/metalogiclabs/mathgraph/actions/runs/45339330722), exact harness commit `e58c466217f6a343566f3c7c597a72f6ff2b6df1`, upstream source `4af5abd2b5d8535f77e902de717c77d657f0093e`. The upstream head was rechecked after execution and is unchanged. The parent artifact's 43-entry manifest and exact regression source were verified before applying its candidate.patch. Original POMs and tests were retained.

The command is `mvn -B --no-transfer-progress -pl yamcs-core -am -Dmaven.test.failure.ignore=true -Dmathgraph.strict=true -Dmathgraph.out=... test`. Failure-ignore permits collection of all module outcomes; every raw JUnit failure/error prevents qualification. It does not weaken the acceptance condition. Original reports are cleared between stages to prevent stale results. The repair is withdrawn after testing, and tracked upstream source is restored.

**Separate replay passed.** A fresh job downloaded the three archives, recomputed and matched their upload SHA-256 digests, verified 976/976 manifest entries per Java version, reconstructed the original test inventories from raw JUnit XML, checked required regressions, and independently recomputed all arithmetic/admissibility classifications from raw TSV using Python. This is a separate implementation/process within the same authored investigation, not an external review.

Artifacts:

- [yamcs-broad-jdk-21](https://github.com/metalogiclabs/mathgraph/actions/runs/45339330722/artifacts/14895643197) — sha256:5ba6b5ea703721cdba3e45ab92212ada62b794a0e2085207ce8dabbc73b2e9a4
- [yamcs-broad-jdk-17](https://github.com/metalogiclabs/mathgraph/actions/runs/45339330722/artifacts/14895513343) — sha256:cf8bff5c67cd9e190ef3b4f087738dc586d9d38865c93db608fe962193ab2c9d
- [yamcs-broad-jdk-25](https://github.com/metalogiclabs/mathgraph/actions/runs/45339330722/artifacts/14895104828) — sha256:0c7c5b9a02a96a233c2631649996aba29496f10d0da00915d88706278858c13a
- [yamcs-broad-independent-replay](https://github.com/metalogiclabs/mathgraph/actions/runs/45339330722/artifacts/14894839363) — sha256:aa02496b257bd613e5573e3d09c90ca6992558c5ec48fdd69659abace2949276

Each native artifact contains 977 files, including full Maven logs, raw JUnit XML/text reports, per-case inventories, dependency hashes, original source hashes, the exact patch, and numerical tables. The replay artifact retains the independent receipt.

**Boundary:** `yamcs-core -am` includes the API/client/XTCE/core reactor dependencies and original default Maven test selection. Tests may use local synthetic sockets. No production system, live telemetry or spacecraft was accessed. The separate integration-test module, web tests, Javadoc and other operating systems are not qualified here. The 14 original skips remain untested. Full operational correctness and paid demand remain UNKNOWN.

**State change:** the prior broader-compatibility UNKNOWN is superseded within this named reactor/platform boundary. The native counterexamples and before/repair/withdrawal lineage remain the correctness authority. No additional causal discovery or catalogue coverage count is claimed.

**Current residual and next action:** maintainer confirmation and a focused contribution. A concise engineering-value conversion discussion is prepared below; the distinct UINT64.toLong issue should remain separately reviewable. No upstream issue, PR or message was submitted. No CLA was signed. Yamcs' discussion-first contribution norm remains applicable.

## Prepared issue draft — not submitted

Unsigned engineering-value conversions can change values or reject representable inputs

I reproduced this offline at 4af5abd2b5d8535f77e902de717c77d657f0093e through DataTypeProcessor.convertEngValueForType and the whole-value branch of SoftwareParameterManager.transformValue.

For a UINT32 value representing 4294967295:
- Converting to a signed 64-bit engineering type returns -1.
- Converting to an unsigned 32-bit engineering type throws IllegalArgumentException.
- Converting to a 64-bit floating type returns approximately 9.223372036854776e18.

I expected the mathematical value to be preserved in each of these representable targets, consistent with the existing decimal conversion and Value.toDouble paths. Separately, UINT32 256 is accepted for an unsigned 8-bit engineering type instead of being rejected.

This appears to be in the engineering-value conversion paths, separate from the comparator path repaired in #1191.

Native reproduction, candidate repair and withdrawal:
https://github.com/metalogiclabs/mathgraph/actions/runs/45337311923

I have a small candidate correction and regression tests. Would a contribution along these lines be useful?

The broader paired regression results above can accompany that draft. No evidence of commercial demand is inferred from technical qualification.
