# Crystal Chess V59 — External Qualification Package

## Candidate

Upstream base:
`official-stockfish/Stockfish@0a215d6c9e48856ef630013b8ab8312941a59057`

Frozen patch:
`stockfish-clock-gate-64ms.patch`

Semantic change:
- Preserve Stockfish time management exactly except:
- when `mainThread->tm.optimum() <= 64` milliseconds,
- set `highBestMoveEffort = 1.0`.
- No board classifier, no additional search heuristic, no parameter sweep.

## Evidence lineage

### V54
Universal removal of the high-best-move-effort discount:
- 1+0.01, 4096 games: +6.872 Elo
- 5+0.05, 1024 games: -7.126 Elo
- Conclusion: universal change rejected; time-budget regime promoted.

### V55
Frozen 64 ms gate:
- 1+0.01, 1024 games: +7.126 Elo
- 2+0.02, 1024 games: +3.393 Elo
- 5+0.05, 1024 games: +2.036 Elo
- All confidence intervals still crossed zero.

### V56 independent replication
Same frozen gate, fresh seeds, 2048 games per clock:
- fast 1+0.01: 502/483/1063, +3.223 Elo, CI [-6.447, +12.899]
- mid 2+0.02: 422/426/1200, -0.679 Elo, CI [-9.672, +8.314]
- slow: still pending when this package was prepared.

Interpretation: the fast-direction signal replicated; mid is statistically flat. No claim of general positive Elo is warranted yet.

## External qualification gates

### Stockfish/Fishtest path
Current Stockfish testing guidance:
1. Base the test on current Stockfish master.
2. Standard functional change: STC `10+0.1`.
3. If STC passes, run LTC `60+0.6`.
4. Fishtest SPRT decides pass/fail/yellow.
5. If LTC passes, open a PR against official-stockfish/Stockfish.

This package is prepared so the exact patch can be copied to a Stockfish fork without reinterpretation.

### CCRL Blitz path
Prospective CCRL-like screen:
- TC: 2'+1"
- Ponder: off
- Same generic opening book, <=12 moves
- Same hash per engine (256 MB in V57)
- Actual CCRL publication still requires CCRL-calibrated tester conditions.

## Promotion rule

Do not promote the candidate to "stronger than Stockfish" unless:
- the remaining V56 slow arm is non-regressive,
- V57 nominal CCRL Blitz transfer is non-regressive,
- V58 Fishtest-style STC is non-regressive,
- and preferably an official Fishtest STC/LTC SPRT reaches pass.

If any of those reverses materially, the failing protocol is the next residual. Do not tune the 64 ms threshold using the held-out result that falsified it.

Qualification trigger: verify the frozen package with the clean rewritten verifier; no candidate change.
