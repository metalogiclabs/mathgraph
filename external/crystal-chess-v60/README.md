# Crystal Chess External Test Package V60

This package freezes the current Crystal chess candidate for independent testing.

## Candidate

Upstream engine:
- `official-stockfish/Stockfish@0a215d6c9e48856ef630013b8ab8312941a59057`

Single source change:
- File: `src/search.cpp`
- Rule: if `mainThread->tm.optimum() <= 64`, set `highBestMoveEffort = 1.0`
- No evaluation, move ordering, pruning, NNUE, or search-depth logic is changed.

Patch:
- `stockfish-0a215d6c-crystal-v56.patch`

The patch was frozen after the V54 sign split and before V55/V56 replication. Do not tune the threshold during external testing.

## Evidence lineage

- V54 universal effort patch:
  - fast `1+0.01`: +6.872 Elo / 4096 games
  - slow `5+0.05`: -7.126 Elo / 1024 games
  - conclusion: universal patch rejected; time-budget regime promoted.
- V55 frozen 64 ms gate:
  - fast: +7.126 Elo / 1024 games
  - mid: +3.393 Elo / 1024 games
  - slow: +2.036 Elo / 1024 games
- V56 independent replication:
  - fast: +3.223 Elo / 2048 games
  - mid: -0.679 Elo / 2048 games
  - slow: pending at the time this package was created.
- V57 nominal CCRL Blitz `2+1`: in progress.
- V58 Fishtest-style STC `10+0.1`: in progress.
- V59 gate-exposure diagnostic: in progress.

The candidate is therefore still experimental. This package exists to enable independent falsification, not to assert an official rating.

## Reproduce

```bash
git clone https://github.com/official-stockfish/Stockfish.git
cd Stockfish
git checkout 0a215d6c9e48856ef630013b8ab8312941a59057
git apply /path/to/stockfish-0a215d6c-crystal-v56.patch
make -C src -j2 build ARCH=x86-64
src/stockfish bench 16 1 3 default depth
```

For an A/B test, build an unmodified copy from the same upstream commit and keep all UCI options, thread counts, hash size, opening pairs, and hardware identical.

## Recommended independent tests

1. Fishtest-style STC: `10+0.1`, 1 thread, 16 MB hash, paired UHO openings.
2. Fishtest-style LTC: `60+0.6` only if STC remains positive.
3. CCRL Blitz-like: `2+1`, ponder off, equal hash, identical generic book.
4. SMP transfer: repeat on 8 threads.
5. Cross-machine replication: at least two CPU families.
6. Official external list testing after the above survives.

## Claim boundary

Do not describe this package as CCRL #1, TCEC #1, or stronger than Stockfish until an external test under the relevant protocol establishes that result.

Stockfish is GPLv3; redistribution must comply with the upstream license.
