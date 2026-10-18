# JPL refute-first audit V1 — qualified results

**Result: GREEN on original, immutable JPL source.** No NASA/JPL repository mutation,
publication claim, unsolicited message, or PR was made.

## Evidence

- [Qualified GitHub Actions #39170009402](https://github.com/metalogiclabs/mathgraph/actions/runs/39170009402)
- [Claim-scope audit job #117800906458](https://github.com/metalogiclabs/mathgraph/actions/runs/39170009402/job/117800906458) — SUCCESS, pinned SHA, five classification controls
- [Claim evidence receipt #12151693957](https://github.com/metalogiclabs/mathgraph/actions/runs/39170009402/artifacts/12151693957) — ZIP SHA256 `d2fc4005788a92061c9a0ff28be559ea42b3feacb85f4c2187670aee1dc34313`
- [Native Lean 4.35 job #117800906647](https://github.com/metalogiclabs/mathgraph/actions/runs/39170009402/job/117800906647) — SUCCESS, upstream parser target 20/20 build jobs, six compiled `#guard` controls (two valid, four known invalid)
- [Native execution artifact #12152356772](https://github.com/metalogiclabs/mathgraph/actions/runs/39170009402/artifacts/12152356772) — ZIP SHA256 `13d9b850e29d0cc68b0a5e5924e9290b92b2893125ed47cea88c37d366398925`
- JPL public source: `nasa-jpl/L4YAML@bca37392fdcb80481342a186a37ab37a5ede6e46`
- MathGraph research source: `metalogiclabs/mathgraph@1c999b03f62c8897e55abb53453d886e63e947cc`

## Main verdict — NOT_ESTABLISHED_BY_DOCUMENTED_PROOF

The JPL README opens by claiming YAML 1.2.2 conformance is established by
mathematical proof, but its own detailed verification section explicitly states
that the proposed grammar equivalence is false as written and the complete
independent input-to-event correspondence remains unproved. The narrower
`parse_iff_executable_language` lemma is not challenged.

**This is a claim-scope inconsistency, NOT a kernel bug or fresh mathematical
refutation.** It reproduces an already acknowledged limitation (see original
MathGraph [#134](https://github.com/metalogiclabs/mathgraph/issues/134) and
[#135](https://github.com/metalogiclabs/mathgraph/issues/135)).

## Native replay

- Expected ACCEPT: `---\\nfoo: bar\\n`, `---\\na: &a bar\\nb: *a\\n`.
- Expected REJECT: `*x`, `!h!x`, `&x [*x]`, malformed `%YAML .2\\n---\\n`.
- These controls check actual executable `parseYaml` from the pin under Lean
  v4.35.0; they do not constitute an independent proof of normative YAML
  conformance.

## Scientific limitation and next decisive test

The full refute-first scientific advantage remains **UNKNOWN** because these
source cases and the documented claim gap were already known. No new,
previously unread capstone was frozen before challenge, and no strong
equal-information maintainer baseline was run. A prospective test must freeze
Nicolas's next actual proposed theorem and its external specification *before*
opening the outcome, then return REFUTED with a reproducible witness,
CONDITIONALLY PROVED within exact authority, or UNKNOWN. Run against his
existing internal checks as a comparator.

The value of V1 is **executed, portable, outside-source verification with
positive/negative controls and honest scope**. It is not a novel scientific
breakthrough or proof of a 10× time improvement.
