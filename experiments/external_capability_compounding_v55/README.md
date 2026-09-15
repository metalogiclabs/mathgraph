# External Capability Compounding V55

This is the first prospective external version of the bounded developmental-capability test.

It uses only the frozen problem JSONL from `YanbiaoLab/equational-challenges` at commit
`bed33e36c33fca139d902addd8cb77cd4172fe64`. It never reads that repository's
published Lean proofs or verdict metadata.

The frozen stream is:

- Phase A: Wrong Book 3000 extension rows 2500:2628.
- Phase B: Wrong Book 3500 extension rows 2500:2628.

The upstream README states that the two extensions are disjoint. The workflow independently
checks that the selected IDs do not overlap and verifies the exact upstream dataset SHA-256
digests before execution.

The continuous developer may emit only:

- `FALSE` with an exhaustively checked finite countermodel;
- `UNKNOWN`.

A successful synthesized finite magma is retained as executable capability. Future tasks try
the retained archive before any new generic synthesis. Retained magmas also seed a fixed
one-cell mutation generator, so the experiment can distinguish direct reuse from a stronger
form of exaptation in which acquired capability changes the proposal generator.

At the Phase A/B boundary the archive is serialized, hashed, reloaded, and frozen for a
cross-extension transfer probe. Exact archive and individual-capability ablations are run on
transferred Phase-B consequences.

The cold control receives the identical fixed prior and identical task-keyed generic synthesis
sequence on every task, but no retained acquired capabilities.

The workflow fails if any predeclared V55 gate fails. A failure is a scientific result and must
not be repaired by weakening the gates after the external stream has been opened.
