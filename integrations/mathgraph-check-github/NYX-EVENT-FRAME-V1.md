# Nyx #613: first-party event-frame retrospective (V1)

This is an **advisory research control**, not a public MathGraph Check deployment,
an independent discovery of the bug, a customer pilot, or a blanket certification
of Rust/aerospace software.

## Claim being replayed

The event detector and Brent refinement in Nyx should evaluate the same
Earth-fixed longitude event frame. A test added by Nyx PR #613 expresses that
requirement. The retrospective transplants that exact test into the pre-fix
source, then runs it under the same dependency resolution on both revisions.

| Pin | Value |
| --- | --- |
| Upstream source | `nyx-space/nyx` |
| Pre-fix base | `d1c3598d5ccf4c984a1d3dd82c450e2af363e821` |
| Fixed PR head | `ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b` |
| Regression test blob | `830919f246536ccc65be4041e9a4b775220f57bb` |
| Native test | `propagation::stopcond::longitude_event_in_rotating_frame` |

Run the isolated workflow
[`MathGraph Check Nyx event-frame retrospective V1`](../../.github/workflows/mathgraph-check-nyx-event-frame-v1.yml)
on `research/mathgraph-check-nyx-v1-20261102` to obtain native outputs and a
bounded JSON receipt. This workflow has no permission to write to Nyx.

### Current native outcome (2026-11-02): `UNKNOWN`

- [Run #41409610430](https://github.com/metalogiclabs/mathgraph/actions/runs/41409610430)
  failed at setup because Nyx has no committed `Cargo.lock`.
- [Run #41410086743](https://github.com/metalogiclabs/mathgraph/actions/runs/41410086743)
  generated one shared lockfile, checked both source pins, and attempted Rust
  tests. **Both builds failed before the test ran**: `E0432` for
  `crate::dynamics::SolidTides` in `sequence/config.rs`. That type is gated on
  `premium`, intentionally disabled by this workflow. The archived verdict is
  `UNKNOWN`, not a reproduced failing-base / passing-head result.
- [Nyx licensing guidance](https://github.com/nyx-space/nyx/blob/ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b/README.md)
  limits premium-feature use by commercial entities above US$1m in annual gross
  revenue without a separate license. The workflow must not silently enable
  it; eligibility or maintainer-approved non-premium build remediation is a
  prerequisite for the next native replay.

## Strict interpretation

- A nonzero base command is **not** a successful regression control unless the
  selected test executed and failed with the expected `EventNotFound` panic.
- A zero head command is **not** enough unless exactly that selected test passed.
- Compile errors, missing data, no selected tests, a different panic, a changed
  source pin, or any missing readback must produce `UNKNOWN`.
- `CANDIDATE_BOUNDED` means internally coherent caller-supplied receipt fields;
  the pure parser cannot authenticate GitHub itself. Independent artifact/log
  readback is required before any claim of verified native observation.
- The optional reviewer Markdown always maps to a **neutral** Check preview.
  Other CI checks are contextual and only shown when attached to the exact head.

The workflow generates one `Cargo.lock` for the pinned head (Nyx does not
commit one), copies it to the base checkout, uses `cargo test --locked` for both,
and records the resolved lockfile and compiler version. It disables the
`premium` feature. Because resolution happens at replay time, a fresh replay
may resolve a different dependency set; compare stored lockfile hashes when
comparing runs.

## What this does not establish

It does not establish comparative performance against ordinary CI or a human
reviewer, discovery by the Check, general C++/Python/Rust assurance, permission
from the Nyx maintainers to operate on their behalf, or evidence that a buyer
would pay. Those require separate prospective evaluations.
