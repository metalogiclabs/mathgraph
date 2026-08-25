# Palomar candidate: closure-relative capability growth

This package extracts the smallest exact mathematical core from MathGraph's bounded experiments on closure obstruction, quotient transport, capability identity, and future-relative representation.

The candidate deliberately separates four notions that are easy to conflate:

1. literal rewrite identity;
2. capability identity modulo transformations already present in the old language;
3. reachability under the currently retained capability regime;
4. raw formability in the host constructor language.

The finite state space has four coordinates and an old cyclic symmetry. Two LT→LE rewrites at different coordinates are orbit-equivalent under that symmetry. In the first retained regime, cyclic transport plus the LT→LE capability cannot create OR, so the protected target is unreachable. The second regime adjoins AND→OR, after which the target is reachable by reusing LT→LE and then AND→OR. Nevertheless the later AND→OR rewrite is already a literal member of the raw one-site constructor language.

The intended bounded interpretation is therefore:

> closure-relative capability identity and strict verified reachability growth do not imply growth of raw syntax.

This is a candidate formalization, not a claim of representation-independent invention or recursive self-extension.

## Palomar surface

- `Challenge.lean` contains only the four advertised theorem statements.
- `Solution.lean` contains the proofs.
- `comparator.json` compares exactly those declarations and enables NanoDa.
- Lean is pinned to 4.32.0 to match the checker-compatible standalone package used by the prior MathGraph Palomar rehearsal.
