# OSTk tabulated flight-profile sample order

Status: WARRANTED finite counterexample, verified locally and on a clean Ubuntu 24.04 hosted runner.

[Hosted native replay](https://github.com/metalogiclabs/mathgraph/actions/runs/45355578637), experiment commit `c66267347f2f83934f07b947401854c82a50ff37`. The actual artifact ZIP was downloaded and independently checked: SHA-256 `8e41438b1962987d765e1c8a90fcd5fbf8b151d5158ca60f5af734b8c9149756`, 38 ZIP files, all 37 manifest entries and CRCs correct. Raw x-coordinate discrepancies were independently recomputed from query time and x(t) = 100 + 7t. Released / compiled original / repair / withdrawal: 594 / 594 / 0 / 594 of 840; unchanged upstream C++ tests 10/10 in every arm. Original and withdrawal CSVs are byte-identical to the released native trace.

`flight::profile::model::Tabulated` accepts and sorts its input states, but records the interpolation time origin from the input's first element before sorting. Query times use the chronological interval start. If the input's first element is not earliest, these origins differ and interpolated coordinates can be wrong.

With samples at 0, 10 and 20 seconds, x(t) = 100 + 7t metres, a query at 5 seconds returns 135 m for sorted input and 205 m for the same samples supplied in order [10, 0, 20]. All samples have one common reference frame and distinct timestamps.

Source: open-space-collective/open-space-toolkit-astrodynamics main `ddc1924a0912bfafc89ef3a217ad21cfc2d98b1f`. The target `src/OpenSpaceToolkit/Astrodynamics/Flight/Profile/Model/Tabulated.cpp` has blob `a07b0f3cba89f7a44924e7420ca7399771b43ceb`, identical at release 18.0.1 (`05612c0483d922ea27a4ff78afd2099439eeeace`). No sorted-input precondition is documented in the public constructor header; the implementation explicitly sorts.

## Replay

On an Ubuntu 24.04 runner with Python 3, Git, g++ supporting C++20 and dpkg-deb:

```sh
python3 research/ostk-profile-time-origin-20261124/replay.py
```

Run in a fresh directory: the driver creates `ostk-replay-work` and `ostk-native-evidence`. Preparation downloads public pinned source and hash-checked versioned dependencies. The actual experiment uses synthetic states and an empty data repository. No operational spacecraft or services are involved.

The driver compiles the original and repaired profile translation units, the unchanged upstream 10-test C++ profile suite and a standalone synthetic oracle. It checks released binary, compiled original, repair, and withdrawal. The expected discrepancy counts are 594 / 594 / 0 / 594 across 840 cases per arm, with 10/10 original tests passing in each. The released/original/withdrawal CSVs must be byte-identical.

The diagnostic fix moves the time-origin reference after sorting. The driver preserves the exact patch, commands, hashes, raw CSVs and JUnit XML. An identical build-only Core String `make_format_args` compatibility shim is required for modern GCC; it is separate from the profile repair. This is a focused translation-unit qualification against released native dependencies, not a complete project build or whole-project assurance claim.

## Additional local evidence

* Published Python wheel 18.0.1: the same 840-case matrix yields 594 position discrepancies. Recompiled original / repair / withdrawal yields 594 / 0 / 594; original and withdrawal match the wheel CSV exactly.
* 35 selected original Python subset/broker/profile tests pass before, with repair, and after withdrawal. The 10 C++ profile tests also pass throughout.
* Initial angular-velocity frame-conversion hypothesis: no discrepancies in 576 synthetic mixed-axis cases using independent matrix and finite-difference oracles. That hypothesis was rejected within this tested boundary.
* Four-sample CubicSpline construction threw `{y} is wrong` and is outside the qualified permutation matrix; its constructor/cardinality boundary remains UNKNOWN.
* Python import/data-download setup failures and shutdown lifetime warnings were not promoted to correctness findings.

The C++ .deb and Python wheel shared libraries are distinct binaries; both reproduce the finding, but no byte identity or exact build equivalence between them is claimed. Neither the full upstream test suite nor all possible states/interpolators have been qualified. Targeted public issue/PR searches found no matching report; novelty is not established exhaustively.

No upstream issue or pull request has been submitted for this finding.
