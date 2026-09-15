# V61 — Verified proof compilation

V58 showed finite countermodel acquisition and reuse. V59 showed local table
geometry does not generalize. V60 showed tiny term-defined operation clones add
little beyond cold finite search.

V61 develops the other side of the truth boundary.

For a source identity S and target identity T, it searches exact equational
rewrite chains from T.lhs to T.rhs using S in both directions under arbitrary
term substitution. Every generated proof path is replayed by a separate
one-step verifier.

A TRAIN theorem is then retained as a source-specific rewrite macro. Its
certificate is replayed from S alone before the macro is admitted. On later
problems with the same source law, the bounded search compares S alone against
S plus retained verified macros.

Training uses only rows 2628:2756, already opened by V58. Validation uses only
rows 2756:2820, already opened by V59. Rows 2820+ remain untouched for a later
prospective run if calibration passes.
