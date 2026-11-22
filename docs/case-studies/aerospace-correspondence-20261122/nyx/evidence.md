# Nyx: when exported numbers acquire the wrong reference frame

**Status, 22 November 2026:** accepted upstream correction with source-bound historical native evidence; fresh source and recorded-CI recheck completed. No new native Nyx execution was performed while preparing this package.

## The engineering claim

An accepted trajectory export must retain the reference-frame identity of each selected state, or explicitly reject a selection that its file format cannot represent. Coordinates and velocities derive their physical meaning from that frame.

Nyx's Parquet trajectory format stores one reference frame for a table. In the examined source, the exporter selected the frame of the original trajectory's first state. That choice could be wrong for the rows actually selected for export. It also could not faithfully describe a mixed-frame selection. The importer applied one parsed frame to the recovered states. The code could therefore return usable data whose physical interpretation differed from the selected source states. [Accepted correction and maintainer review][pr]

This is a correspondence obligation at an export/import boundary. It does not require the numerical integrator to be wrong. It also does not establish a failure in a deployed flight system.

## The correction

The accepted patch chooses the frame from the selected rows and rejects mixed-frame selections. Its three upstream regressions cover:

1. A homogeneous trajectory round trip, preserving frame, position and velocity coordinates.
2. Distinct source frames, requiring preservation or the specified explicit mixed-frame rejection.
3. A filtered export, requiring metadata for the selected row rather than an excluded earlier row.

The scoped production change is in `nyx-core/src/md/trajectory/traj.rs`; the tests are in `nyx-core/tests/parquet_frame_fidelity.rs`. The separate RIC-difference exporter and importer-side metadata validation are outside this repair. The finite regressions do not prove every export path correct.

## Evidence and source identity

| Evidence | Source and observation |
| --- | --- |
| Original source | `09ab47dd4233ad3b80efc64479bf5339739b5570` |
| Accepted PR head | `7d3253506471a7b9ff58e87fbee50e4a025e0b3f` |
| Upstream merge | `71e31c137bfe2fea641a21455febb84c936fc409`; PR #615 merged 13 November 2026 |
| Historical physical experiment | [Run 42925288557][native], workflow source `20a1c9f1a70669ca02664a1e8c6e87cc1ce32df3`; original mixed/filtered witnesses classified as failing the protected property, repaired five-test suite classified as passing |
| Accepted-merge-tree regression evidence | [Coverage job 130252496810][coverage] records the three named upstream regressions, 3 passed / 0 failed |
| Associated PR workflow CI | [Run 42937928116][finalrun] failed: Coverage, Check and Tests succeeded; Lints failed. A green whole-PR result is not claimed. |

The physical experiment used a compatibility shim in the unrelated nonpremium sequence-configuration module. Its workflow checked that the audited export/import source files were unchanged before applying the targeted exporter repair. The shim is not part of the accepted production PR. That historical experiment and the final-head upstream qualification are separate evidence boundaries.

The historical raw artifact is [13812684242][artifact], with GitHub-reported SHA-256 `a68b835d817c5dcb41c381d2447e52aea1e5b43c6435f18b6879eb215c56ca22`. The artifact itself was not downloaded in this session. Accordingly, the publication summary omits numerical residual magnitudes that appear in the PR description.

## What was freshly checked

Nine source/license files were fetched from their declared immutable revisions and independently matched to their Git blob identities. The historical patch script was executed against the exact original exporter source; its output matched the accepted PR-head exporter byte for byte. Timestamped output receipts in the historical native job and the three regression results in the upstream coverage job were rechecked. The coverage job actually checked out synthetic merge `78ab554425ee06caa844260f27076f4da8a66d73`, not the PR head itself. Git commit inspection confirms that this executed checkout and the accepted upstream merge share the exact tree `6d8f077d27a158c52171ce7a6f8c10aae75a8c60`. The PR head has a different tree because it predates two event-detection changes; its exporter, importer and Parquet test blobs are identical to those in the executed checkout. The package retains small verbatim log excerpts, their original line numbers, and SHA-256 values for the full fetched logs.

Run the offline recheck from this directory:

```sh
python3 verify_evidence.py
```

The result is `PASS_SOURCE_AND_RECORDED_CI_RECHECK`, with `native_execution_this_run: NOT_RUN`. The verifier checks file integrity, pinned source identities, source/CI associations, recorded outcomes and exact patch correspondence. It does not authenticate a publisher, rerun the Rust program or establish a new native result. Rust and Cargo are absent in the preparation workspace.

Three negative controls were also checked: a modified source file, a missing executed receipt, and a missing named passing regression each fail the evidence recheck. The latter two controls update their manifest hashes, so they test outcome validation beyond ordinary hash mismatch. Results are in `negative_controls.json`.

For a new native run, use the original [pinned five-test workflow][workflow] and its included probe/shim/repair files, or check out accepted merge `71e31c137bfe2fea641a21455febb84c936fc409` and run the upstream regression target:

```sh
cargo test --release --package nyx-space --test parquet_frame_fidelity -- --nocapture
```

This command is an upstream replay instruction, not a command executed here. Record the toolchain, resolved dependencies and source checkout for any new run. The historical experiment generated a dependency lockfile; this package does not include that lockfile or the planetary binary fixtures, so it is not a byte-identical historical build environment.

## Reusable lesson

For a scientific export, preserving numerical fields is insufficient when metadata changes their interpretation. The useful check follows the selected data through the actual consumer and compares the intended observation in the relevant frame. Matched valid controls and an explicit rejection policy make that check actionable.

This accepted result supports a concrete aerospace assurance case study. It does not establish automated discovery by a deployed MathGraph product, comparative superiority, an institutional endorsement, or general mission assurance.

## Source notices

Copied Nyx source retains its original copyright and AGPL-3.0-or-later notices. The upstream license is included as `sources/NYX_LICENSE`. The public Metalogic research probe and helper files are retained with their original notices and pinned source links; no new blanket license for the combined package is asserted. The full source manifest supplies Git blob identities and SHA-256 checksums.

[pr]: https://github.com/nyx-space/nyx/pull/615
[native]: https://github.com/metalogiclabs/mathgraph/actions/runs/42925288557
[coverage]: https://github.com/nyx-space/nyx/actions/runs/42937928116/job/130252496810
[finalrun]: https://github.com/nyx-space/nyx/actions/runs/42937928116
[artifact]: https://github.com/metalogiclabs/mathgraph/actions/runs/42925288557/artifacts/13812684242
[workflow]: https://github.com/metalogiclabs/mathgraph/blob/20a1c9f1a70669ca02664a1e8c6e87cc1ce32df3/.github/workflows/check-nyx-parquet-physical-v2.yml
