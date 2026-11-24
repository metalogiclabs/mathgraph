# EnduroSat csp-es: qualification of an existing upstream dedup backport

Date: 2026-11-24. Offline synthetic unit tests only. No external submission.

## Warrant and lineage

EnduroSat `develop` at `135807773e7fd9aea9f68f027e296e9f54d75830` still contains two duplicate-search problems already repaired by libcsp PR [#1036](https://github.com/libcsp/libcsp/pull/1036), merged as `134f2cb7bd44a0d23a98e9d9606c59a9ca000f23` on 2026-10-17. Credit for the diagnoses, fixes and original upstream regressions belongs to Stef Van den Haute and upstream libcsp. These are not new MathGraph discoveries.

WARRANTED within this Linux/GCC synthetic boundary: backporting the two search changes clears the selected cases and preserves EnduroSat's current author tests, including its four CRC-trailer regressions. EnduroSat's newer CRC-trailer exclusion is retained. The repair remains a contribution candidate until maintainer review. Deployment, operational consequence, all-platform correctness, maintainer interest and paid demand are UNKNOWN.

| Native evidence | Before | Two-line backport | Withdrawal |
|---|---:|---:|---:|
| EnduroSat author unit tests | 22 pass | 22 pass | 22 pass |
| Existing libcsp #1036 regressions | 1 pass, 2 fail | 3 pass | 1 pass, 2 fail |
| Independent selected matrix | 68/240 discrepant | 0/240 discrepant | 68/240 discrepant |

Before/withdrawal matrix output is byte-identical; original production source bytes were restored. The matrix's 68 failures (64 false negatives, four false positives) are manifestations of two already-known causal mechanisms, not 68 discoveries.

## Contract and decisive examples

The source declares a 100 ms duplicate window and a 16-entry ring. Ordinary current code and the upstream regression include age 100 ms and exclude 101 ms. The clock API returns uint32 milliseconds; the original POSIX implementation explicitly narrows CLOCK_MONOTONIC to that type. Selected intervals are at most 10,001 ms, well below one clock period. This research makes no claim about comparing timestamps separated by an entire 32-bit period.

- At timestamp 1000, insert one packet then 15 distinct packets at the same time. Repeating the first packet is not detected, although it remains the oldest stored entry.
- Insert at uint32 timestamp 4294967246 and repeat 30 ms later: the fresh duplicate is not detected before clock wrap.
- Insert at timestamp 4294957296 and repeat 10,001 ms later (now timestamp 1): the expired packet is incorrectly classified as a duplicate.

`probe.c` invokes the actual built library's header encoding, CRC32 and duplicate search. Only the clock is controlled with GNU linker's `--wrap=csp_get_ms`; no duplicate-search approximation is executed. Each matrix case starts a fresh process. Original author tests use the ordinary native clock. The independent Python oracle uses unbounded elapsed integers and the stated ring capacity; it does not transcribe the implementation's expiry expression. Fresh and distinct-payload controls are required to pass. Both CSP versions 1 and 2 are exercised. Upstream tests are retained byte-for-byte from the cited commit and have their own clock seam.

## Reproduction

Place these files in `enduro-evidence/` under an otherwise empty work directory. Clone EnduroSat into sibling `endurosat-csp-es/` and check out the pinned SHA. Clone `libcheck/check` into sibling `libcheck/` and check out `11970a7e112dfe243a2e68773f014687df2900e8` (0.15.2). Install CMake 4.4.5 into `build-tools/` with `python3 -m pip install cmake==4.4.5 --target build-tools`. GCC 14.2.0, GNU Make, pkg-config, pthread and standard Linux headers were used.

Run from the work directory:

```sh
./build-tools/cmake/data/bin/cmake -S libcheck -B libcheck/build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX="$PWD/libcheck-installed"
./build-tools/cmake/data/bin/cmake --build libcheck/build -j 2
./build-tools/cmake/data/bin/cmake --install libcheck/build
PKG_CONFIG_PATH="$PWD/libcheck-installed/lib/pkgconfig" ./build-tools/cmake/data/bin/cmake -S endurosat-csp-es -B endurosat-csp-es/build-mathgraph -DCSP_BUILD_SAMPLES=ON -DCMAKE_BUILD_TYPE=Debug
python3 enduro-evidence/run.py
```

Raw per-arm outputs, exact command arguments, source hashes and compiler/dependency identities are retained. `run.py` temporarily applies two literal source changes and restores source in a finally clause. Its final assertions require failure -> success -> failure. The candidate patch is the same two search changes as upstream #1036, without replacing EnduroSat's CRC-trailer logic.

## Exclusions and failed setup

The first local configure could not run because CMake was absent. After installing CMake, the default all-target build stopped at example `zmqproxy.c` because optional ZeroMQ development headers were absent. These are setup/environmental results, not correctness counterexamples. The selected `csp_es` and `csp_tests` targets built with the project's unmodified CMake files after installing libcheck; the actual unit suite and additional regressions executed. Full all-target build, original CI transport/integration matrix, simulator, 16-bit MCU execution and other architectures remain unqualified. Wire-format examination identified a separate possible investigation but no independent wire-format matrix was executed in this iteration.

## Culture and commercial decision

Read README, MIT LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, both issue templates and the native build/test workflow. CONTRIBUTING welcomes fixes, portability and test coverage, requests reproducible text logs and expected/actual behavior, and encourages coordinating general fixes with upstream libcsp. It says branch from `main`, whereas current default/source is `develop`; submission base needs reconciliation before any contribution. No PR template or separate security policy was present in the inspected root/.github files.

Current GitHub metadata has issues disabled, despite the bug-report instructions. Only two public PRs were found; #2 closed unmerged on 2026-11-22 without a visible comment/review, and both PR discussions were empty. Receptiveness is therefore UNKNOWN, not established by welcoming documentation. No contact, issue, PR or email was made.

Compared with old Dawn forks, this company-owned fork has a recent explicit portability contract and current project-specific regressions. That makes it a useful bounded next research target. Existing Yamcs, Sedaro and Antaris reports remain pending; OpenC3 PR #4433 already exists and must not be duplicated. Public ownership and a passing backport do not establish current flight use, a buyer, a job opening or commercial demand.

## Current residual and smallest next step

The immediate engineering opportunity is a small attributed backport preserving the fork's CRC work. This is already reviewable in `candidate.patch` and the receipts. The unresolved collaboration residual is which contribution route/base the company actually supports; no external action is authorized by this research checkpoint. If deeper novel correctness research is prioritized, the smallest next technical experiment is an independent golden-byte CSP 1/2 header test on valid field boundaries, then actual target execution for any 16-bit claim. Do not promote a host-only result to 16-bit correctness.

Reuse: source/version comparison prevented relabeling an upstream fix as a discovery. This is ordinary change-propagation assurance. The experiment establishes bounded compatibility and causal effect; it does not demonstrate MathGraph superiority over conventional review or paid value.

The actual 104-prompt catalogue is recorded in `catalogue-coverage.json`. Assessed facets overlap and are not independent detectors, independent mechanisms or whole-project coverage. Other modes remain explicitly UNASSESSED.
