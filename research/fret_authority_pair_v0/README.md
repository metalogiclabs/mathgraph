# MathGraph — paired source-to-monitor authorization experiment (18 Nov 2026)

**Status: WARRANTED_BOUNDED native observations; CANDIDATE reusable authority protocol; UNKNOWN owner intent and generalized benefit.**

## Result

This is a narrow experiment in deciding **what warrants formalization or repair**. The same native verification ecosystem produces two very different assurance outcomes:

**Prior art inside this research programme:** An earlier Claim Assurance pilot already tested three-way packet-relative authorization in 30/30 **synthetic** checks. An independent source-intent pilot already exhibited a bounded native proof/countermodel and strong-baseline tie. This experiment does not claim invention of REFUSE/ABSTAIN. Its new bounded evidence is a *native C2PO/R2U2 decision pair plus mechanically selected question*, grounded in the source-to-monitor handoff. A separate pinned FRET parser/exporter alias replay provides additional lineage but is not part of this paired test. Internal Research OS records hold the earlier evidence.

| Source-evidence case | Independent consequence | Appropriate decision |
| --- | --- | --- |
| A. Explicit experimental strict name-binding policy fixes compile order `BOOST,COAST`; runtime header claims `COAST,BOOST` | Legacy C monitor silently changes `COAST` verdict `T,F` to `F,F` on the same named values | `REFUSE` execution under that *declared* policy; existing native SIG1 fork correctly rejects the mismatched header |
| B. Two **constructed** temporal candidates, `BOOST -> F[0,7] COAST` versus `BOOST -> F[2,7] COAST`; `BOOST` and `COAST` both true only at t0 | Bounded search discovered the one-pulse separating witness in its **second** candidate; native R2U2 C produces `IMMEDIATE=T`, `DELAYED=F` at t0, matching a separate Boolean oracle | `ABSTAIN` from selecting an intended requirement; ask whether a simultaneous COAST response counts |

The 8-tick trace is the sparsest witness (one response pulse) **within the declared two-window, fixed-t0-trigger, length-8 Boolean search grammar**. An independent set-theoretic oracle checks all **1,296 ordered pairs** of 36 possible 8-tick future windows. This is not global minimality over unrestricted MLTL. The generated question is: **“Does COAST at offset 0 after BOOST count as satisfying the requirement?”** The delayed formula is **not** asserted to be an alternative FRET translation. `F[2,7]` means ticks, not automatically elapsed seconds.

Case A's strict mapping policy is explicitly chosen by the experimenter. Original R2U2's documented compile-time mapping leaves deployment responsibilities to callers; the legacy runtime observation is not, by itself, an upstream bug finding. The optional SIG1 fork is an existing repair experiment, **not code introduced by this branch**. An equally informed simple string/header comparator can make the same A decision; this pilot does not claim comparative superiority.

## Exact source and preserved independent evidence

- [FRET original source](https://github.com/NASA-SW-VnV/fret/commit/cf0f913cc15c41705e803593297e89cd6056b839): `cf0f913cc15c41705e803593297e89cd6056b839`.
- [R2U2 original native source](https://github.com/R2U2/r2u2/commit/2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a): `2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a`.
- [Existing MathGraph SIG1 fork](https://github.com/metalogiclabs/r2u2/tree/mathgraph/sig1-input-contract-v5): `9d58a88f30216d8ebbbfc70828974f11ecd1ebeb`. Its compiler embeds a typed named-input contract in an opt-in binary footer; its C CLI checks it before reading telemetry.
- Separate FRET identifier-alias evidence (retained privately with its own source replay): two individually compiled accepted FRETish source requirements with distinct trigger names produce identical C2PO/native binaries, even though an independent source oracle distinguishes them. The single-sentence duplicate-name export is **rejected** by C2PO; do not claim that particular export deploys silently. The maintainer's intended `_DOT_`/`_PRC_` identifier policy is **UNKNOWN**.

## Reproduce

Check out the source commits above into separate directories. Build the original C monitor with `make -C monitors/c`; build the SIG1 fork with `make -C monitors/c debug`. From the root of this MathGraph checkout, run:

```bash
python3 -m unittest -v research.fret_authority_pair_v0.test_authority
python3 -m unittest -v research.fret_authority_pair_v0.test_witness
R2U2_SOURCE=/absolute/path/to/original/r2u2 \
R2U2_SIG1_SOURCE=/absolute/path/to/sig1/r2u2 \
  python3 -m unittest -v research.fret_authority_pair_v0.test_native_pair
```

The dedicated [source-pinned GitHub Actions workflow](../../.github/workflows/fret-authority-pair-v0.yml) runs all three modules with the two exact native source commits and records a separate CI pass/fail boundary.

The source path variables are required for **native qualification**. Without them, native test classes intentionally skip and their skip must not count as a qualified native pass. Tests verify exact Git HEADs before compiling. All generated binaries live in temporary directories, never in this research branch.

The standalone experiment consists of `authority.py`, `witness.py`, three `test_*.py` modules, and five input fixtures. The only ALLOW resulting from a *simulated verified owner answer* permits **candidate selection for additional checking**, not deployment. No actual owner answered this constructed trace. Changing source digests, withdrawing the strict policy, revoking the simulated answer, supplying contradictory answers, or disagreeing with the independent oracle causes ABSTAIN. These are pure gate tests, not a claim of full Metatron/RealityGraph/Flash runtime integration. The source-authorization flag is a controlled experimental input, **not a deployed authentication or signature verification mechanism**.

### Fresh local qualification boundary

- **25/25** tests in this experiment: 15 authority/status, 5 bounded witness discovery (including 1,296 ordered window-pair oracle checks), 5 authentic C2PO/native monitor cases, zero skips with both `R2U2_SOURCE` variables set.
- **48/48** native SIG1 fork input-boundary tests at the exact fork pin; separately **7/7** original FRET identifier-alias reproducibility tests using the authentic parser/exporters and native C2PO/R2U2.
- Locally generated binaries (not committed): original A SHA-256 `82c32f19651a7cfe8d472434376046639e15e9520a36b72336a8d53f9cfe15b4`; original B `76c12b313628f0525ddbded2b890ad99f05ccd609e2f1cd3e17025101fdf4a66`; opt-in SIG1 A `1cba63d431b4f6fb8b8b42975281f557e662e0444b1e85ea1d9474b86dc38462`.
- **Preserved baseline failure:** original R2U2 pin's separate `make -C monitors/c test` fails to compile this environment's `test/test_lib.c` (`r2u2_init` undeclared; munit signature mismatch). Its release C monitor compiles and runs. Do not imply the whole upstream C unit suite passed locally.
- **Broader repository is not green in this environment:** separately running all default MathGraph tests produced **2,160 passed, 8 skipped, 33 failed, 19 errors**. Some tests require external exact-source environment variables or archives not supplied to this standalone replay. That sweep is not evidence of global qualification for this branch; the new 25 native-scoped tests are run and reported independently.

## Warrant boundary and residual

**WARRANTED_BOUNDED**: exact original native C2PO/C monitor outputs; matching independent finite oracle for B; exact SIG1 fork native fail-closed reaction for A; three-valued policy gate unit tests. The earlier FRET identifier-collision source replay remains a separate qualified finding and must not be conflated with these constructed formulas.

**REJECTED in tested scope**: a generic claim that all short online temporal verdicts are incorrect (the preceding extensive R2U2 finite-prefix audit found zero wrong emitted verdicts); the claim that the single-requirement duplicate-name FRET export silently compiles; any claim that the demonstration alone determines engineering intent or gives a verified performance advantage over an equally informed baseline.

**UNKNOWN**: owner-authorized choice between immediate and delayed response; maintainer approval of strict name binding in every R2U2 deployment; FRET full Electron/project validation of alias spellings; complete source-author warrant chain; runtime telemetry provenance in real systems; actual integrated UDM/Metatron/Flash revocation; economic benefit beyond a well-informed conventional checker.

**Cheapest next decisive experiment**: obtain an authoritative answer on whether a simultaneous response is permitted for one real mission requirement; bind that answer to the exact source, test a revised and unchanged monitor on independently selected additional traces, and show downstream withdrawal/restoration when the authorized source changes. Treat a missing answer as UNKNOWN, not permission to guess.
