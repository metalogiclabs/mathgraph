# V57 route calibration

This calibration uses only V55/V56-opened problem IDs. Public certificates were
inspected post-hoc to identify route classes, but the workflow itself reads only
the frozen problem JSONL.

It calibrates a generic route stack:
1. E equational theorem prover;
2. exact finite-model construction for carrier sizes 2..6;
3. independent MathGraph finite verification;
4. UNKNOWN otherwise.

No result from this file is fresh evidence. Once the route stack is calibrated,
its budgets and code are frozen before any row >= 2628 is opened.
