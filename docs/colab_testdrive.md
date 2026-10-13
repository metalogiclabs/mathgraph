# Colab / Local Test Drive

```bash
git clone https://github.com/metalogiclabs/mathgraph.git
cd mathgraph
python scripts/run_colab_testdrive.py --use-current-checkout --quick-smoke
python scripts/run_colab_testdrive.py --use-current-checkout --allow-live-verifier --allow-missing-verifier
```

Public scripts bootstrap the repository root automatically, so editable install
is optional for local script use. Live verifier execution remains opt-in, and
missing Lean may skip cleanly when explicitly allowed. Test-drive success is
advisory unless an artifact carries explicit verifier, trusted-importer,
finite-validator, or chain-audit boundary evidence.
