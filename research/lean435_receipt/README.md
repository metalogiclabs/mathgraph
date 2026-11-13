# Lean 4.35 source-verification receipt — isolated qualification

**Status: CANDIDATE until the exact GitHub Actions execution and artifact are inspected.**

This is an implementation of the existing MathGraph *proposed* Lean proof receipt profile, not a novel kernel or mathematical discovery. It replays an **upstream-authored Lean core theorem**: `Nat.gcd_comm` from `leanprover/lean4:v4.35.0`, file `src/Init/Data/Nat/Gcd.lean` (Git blob `6b3ac409cc1ed8775644c5c6a00a1a59f96fac2b`). The source theorem is reused under `MathGraphReceipt.upstream_gcd_comm`; it is *not* independently re-proved from first principles.

- **Trusted challenge**: `Challenge.lean` fixes the exact theorem statement, with an intentional `sorry` only in that challenge.
- **Solution**: `Solution.lean` references the existing upstream theorem, with no new axioms.
- **Checks**: Lean v4.35.0 `lake check --paranoid` and `lake comparator --paranoid` (official kernel and bundled independent checkers), requiring exit code 0 for both.
- **Protected negatives**: substituted theorem statement and an injected axiom MUST produce comparator exit code 1 (not 2, an environmental failure).
- **CI evidence**: `evidence/receipt.json`, per-step logs/hashes, exact source SHA and upstream file identity are emitted only by `qualify.py`. If anything fails or is missing, status stays `UNKNOWN`.
- **Boundary**: a checked wrapper of an already proved upstream theorem; no new theorem, no JPL compatibility, no independence from the Lean original assumptions, no production release or MathGraph site badge.

Reproduce on Linux with bwrap installed, Lean release toolchain and Python 3:

```sh
cd research/lean435_receipt
python3 qualify.py
```

The intended next gate is independently consuming the exact artifact via the existing MathGraph Resolve protocol. Do **not** add a public verified badge or merge based only on this candidate source.
