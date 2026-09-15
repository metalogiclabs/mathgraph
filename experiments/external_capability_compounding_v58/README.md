# V58 — Fresh external capability compounding

V58 is frozen before semantically opening any problem row at or after offset 2628.

- Phase A: Wrong Book 3000 rows 2628:2756.
- Phase B: Wrong Book 3500 rows 2628:2756.
- Upstream commit: `bed33e36c33fca139d902addd8cb77cd4172fe64`.
- No upstream proof file or verdict label is read.
- cvc5 is used only as a bounded finite-model constructor. A SAT model is
  terminal FALSE only after independent exhaustive MathGraph verification.
- cvc5 UNSAT is a non-terminal proof candidate; V58 does not promote TRUE.

The developer retains verified finite magmas, tries them before fresh synthesis,
and may generate bounded one-cell descendants of retained capabilities.  The
Phase-A archive is frozen/restarted before Phase B, and Phase-B transfer plus
individual ancestor ablations are measured before Phase-B learning.

The cold control receives the identical cvc5 constructor and timeout on every
Phase-B task but no retained capability.

All scientific gates are fixed in `run.py` before the fresh stream is opened.
Failure is retained as evidence rather than repaired on these rows.
