## Frozen prospective test

Opened-data calibration run **34960757212** passed all calibration checks before
the fresh runner was committed. The parameters are frozen exactly as calibrated:

- top source-nearest parents: 3
- maximum Hamming distance: 4
- Z3 time per parent: 300 ms
- total neighborhood solver budget: at most 900 ms
- cold cvc5 comparison budget: 900 ms

Fresh evidence begins at row 2756. The runner compares the original V58 archive
with the post-Phase-A archive on the full Phase-B block *before Phase-B
acquisition*, then performs exact ancestor deletion/restoration ablations.
