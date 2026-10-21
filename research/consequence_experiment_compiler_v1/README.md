# Consequence-to-experiment compiler V1

A **minimal executable dual** of consequential quotienting on **complete, finite, declared** action/observation systems. It synthesizes the cheapest additional family of observable experiment programs needed to realize a target consequential partition, or returns a checkable missing-pair obstruction with explicit grant versus missing-primitive diagnosis.

## Reproduce without dependencies

```bash
python test_protocol.py
python fuzz_independent.py
python independent_audit.py
```

`compiler.py` is the candidate. `independent_oracle.py` independently implements saturation, Bellman–Ford path costs and exhaustive experiment-subset checking. `independent_audit.py` replays saved per-case evidence without importing candidate source. `fixtures.py` declares all states/effects/observations/costs/permissions. `test_protocol.py` includes the 240+40 exact scenarios, provenance withdrawal, safe/unsafe future controls and 16 cached multi-goal snapshot tests. `fuzz_independent.py` runs 500 opaque seeded countermodels and false-receipt mutations.

`result.json`, `cases.json`, `fuzz_result.json`, and `independent_audit_receipt.json` are **generated** and retained as GitHub Actions artifacts; raw timing rows are not deterministic and are not an experimental claim of computational advantage. See `PROTOCOL.md` for source and epistemic boundaries.

The verified user-facing distinction is: **a missing grant is not a new missing primitive, and absent evidence is not certified equivalence**.