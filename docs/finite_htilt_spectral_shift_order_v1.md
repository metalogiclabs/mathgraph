# Finite H-Tilt Spectral Shift Order v1

This document records the first spectral-shift micro-boundary in the finite H-Tilt theorem tower.

## Verified theorem

For real coordinates representing two complex numbers:

- target mode: `lambda = a + ib`
- competitor mode: `mu = u + iv`
- real shift: `c`

define:

`shiftedSqMod(c,a,b) = (c+a)^2 + b^2`

The Lean proof verifies:

`shiftedSqMod(c,a,b) - shiftedSqMod(c,u,v) = 2c(a-u) + ((a^2+b^2) - (u^2+v^2)).`

It also verifies that the sufficient dominance condition

`|(u^2+v^2) - (a^2+b^2)| < 2c(a-u)`

implies

`shiftedSqMod(c,u,v) < shiftedSqMod(c,a,b).`

## Role in the tower

This is a small algebraic portal toward Perron-root alignment. It says that a sufficiently large positive real shift converts strict real-part advantage into strict shifted squared-modulus advantage, modulo a bounded unshifted modulus residual.

## Boundary

This artifact does not prove the finite-spectrum maximum, does not prove any matrix spectral theorem, and does not invoke Perron-Frobenius. It is pure real algebra only.
