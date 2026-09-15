# V62 — Critical-pair lemma genesis

V61 showed that target-only rewriting is the wrong proof graph: it found zero
proofs before the calibration timed out. Inspection of already-open TRUE
certificates showed the recurring structure instead:

source identity -> derived universal lemmas -> more derived lemmas -> target.

V62 tests the smallest generic implementation of that structure. It saturates
the source identity by verified self-overlap / critical-pair generation.
Every admitted lemma carries a derivation record and is replayed before use.
Targets may then use only replay-verified equations.

This workflow is diagnostic only on TRUE cases that were already opened before
V62. It does not inspect any row at or after 2820.
