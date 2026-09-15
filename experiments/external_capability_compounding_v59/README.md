# V59 — Compile specimens into model neighborhoods

V58 established fresh acquisition and later reuse, but the acquired Cayley
tables were too local. V59 tests the smallest representation upgrade suggested
by that residual.

A retained finite model is no longer treated as one point. It becomes the
center of a bounded, source-constrained neighborhood. For a new implication,
V59 ranks retained models by source-law violation, then solves only for a table
within a fixed Hamming radius that satisfies the source exactly and falsifies
the new target. Every generated child is exhaustively rechecked by MathGraph.

The calibration workflow is restricted to V58-opened rows 2628:2756. Its only
purpose is to decide whether the generic operator is viable before the next
untouched rows are opened. Fresh evidence must start at row 2756 or later.
