# V59 External Submission Handoff

Candidate: frozen Crystal 64 ms clock gate.

Upstream base:
`official-stockfish/Stockfish@0a215d6c9e48856ef630013b8ab8312941a59057`

Patch:
`external/chess/v59/stockfish-clock-gate-64ms.patch`

## Stockfish / Fishtest handoff

Fishtest requires a real GitHub fork of `official-stockfish/Stockfish`; a copied non-fork repository will not work.

1. Fork `official-stockfish/Stockfish` to the submitting GitHub account.
2. Sync the fork's `master` with official Stockfish master.
3. Create a branch, for example:
   `crystal-high-effort-short-budget`
4. Apply `stockfish-clock-gate-64ms.patch`.
5. Build Stockfish.
6. Run the default `./stockfish bench`.
7. Use the exact signature emitted by V59's `BENCH_SIGNATURE.txt` as the branch/test bench.
8. Commit only this one idea.

Suggested commit message:

    Avoid high-effort time discount at very short local budgets

    A late-overturn audit found that root incumbents can consume a large
    fraction of search effort for many completed iterations before a better
    root move appears. Preserve Stockfish's existing high-best-move-effort
    time reduction generally, but disable that reduction when the current
    optimum move budget is at most 64 ms.

    The 64 ms gate was frozen before independent replication and external-
    protocol screens. No board classifier or additional search heuristic is
    introduced.

    Bench: <copy exact V59 BENCH_SIGNATURE value>

9. Push the branch to the Stockfish fork.
10. On Fishtest, use that fork as the Test repository and the exact branch name.
11. Submit a Standard STC test at `10+0.1`.
12. Do not stop a Standard SPRT because of intermediate scores.
13. If STC passes, reschedule/run LTC at `60+0.6`.
14. If LTC passes, open the upstream Stockfish PR and include the STC/LTC test links and bench signature.

## Local / pre-submission authority

Do not describe the patch as stronger than Stockfish unless the held-out transfer gates support it.

Current frozen evidence as of package creation:
- V55 fast: +7.126 Elo / 1024
- V55 mid: +3.393 Elo / 1024
- V55 slow: +2.036 Elo / 1024
- V56 fast fresh replication: +3.223 Elo / 2048
- V56 mid fresh replication: -0.679 Elo / 2048 (statistically flat)
- V56 slow: pending
- V57 nominal CCRL Blitz 2'+1": pending
- V58 Fishtest-style STC 10+0.1: pending

## CCRL Blitz handoff

Official CCRL Blitz conditions to reproduce:
- Equivalent TC: 2 minutes + 1 second increment on CCRL reference calibration.
- Ponder off.
- Equal hash: 128 or 256 MB.
- Same generic book for both engines.
- Book line length no more than 12 moves per side.
- Endgame tablebases according to CCRL tester conditions.
- Actual rating-list evidence must come from CCRL tester hardware/calibration; GitHub-runner matches are pre-screens only.

## Promotion discipline

- A positive point estimate alone is not enough.
- Prefer an SPRT pass or a confidence interval excluding zero for the same frozen candidate.
- Do not move the 64 ms threshold in response to V56/V57/V58 held-out outcomes; a failure becomes a new residual rather than a tuning target.
