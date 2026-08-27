# Real case studies

These cases are deliberately not synthetic demonstrations of the VDN definitions. They replay previously executed external experiments from pinned GitHub Actions artifacts and ask whether the minimal VDN objects reveal something useful without changing the source results.

`kernel_census_case.py` treats checker implementations as states and tutorial tests as verifier contexts. It computes the full behavioral quotient and then CompleteCover-searches context subsets until the same quotient is preserved.

`uvrm_v6_case.py` consumes the raw protected scoring rows and run metadata from UVRM Graph V6. It recomputes all arm aggregates and checks two precommitted separators: matched-budget GRAPH versus reconstruction, and correct typed relations versus permuted relation semantics.

The Palomar case is executable Lean rather than a Python replay and is checked by CI.
