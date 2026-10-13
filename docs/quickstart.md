# Quickstart

## Lean/Mathlib readers: three real entry points (October 2026)

1. **[Browse the pinned Mathlib slice](https://mathgraph.org/explore/):** 2,345 declaration occurrences in 13 Mathlib v4.34.1 modules. Relations `DECLARES`, `TYPE_REFERENCES` and `IMPORTS_MODULE` are structural, not proof dependencies.
2. **[Inspect the public JPL L4YAML case](https://mathgraph.org/records/mg-l4yaml-source-check-20261010/):** an independent third-party source check with exact Lean receipt pins, 48 decoded YAML cases and 4 extra guards; not an endorsement or universal YAML proof.
3. **[Run the source-catalogue consumer](https://mathgraph.org/developers/#source-catalogue):** standard-library Python verifies published structure against an exact policy, not theorem validity. The source snapshot is `8e8f5f529b44852815627206dc5b45062f0c96d6`; use a separately trusted policy digest.

Documentation/search tools such as doc-gen4, Loogle and LeanSearch serve a different purpose: MathGraph explores **source-to-evidence provenance and scoped status**, not a better or complete declaration search engine. Original code licensing is proposed as Apache-2.0 and subject to review; see `LICENSE` and `THIRD_PARTY_NOTICES.md`.

## Research/demo commands

## 1. Fresh Clone

```bash
git clone https://github.com/metalogiclabs/mathgraph.git
cd mathgraph
```

## 2. Quick Release Check

```bash
python scripts/run_release_check.py --quick
```

## 3. Public Demo, Advisory Mode

```bash
python scripts/run_public_demo.py --out-dir demo_out
```

## 4. Public Demo, Live Verifier If Lean Is Available

```bash
python scripts/run_public_demo.py \
  --allow-execution \
  --allow-missing-verifier \
  --accept-verified-entries-in-memory \
  --out-dir demo_out
```

## 5. Colab / Local Test Drive

```bash
python scripts/run_colab_testdrive.py --use-current-checkout --quick-smoke
```

## Optional: Curated Local Mathlib Demo

```bash
python scripts/run_real_mathlib_demo.py --ensure-examples
python scripts/run_real_mathlib_demo.py --config examples/real_mathlib_demo/curated_real_mathlib_demo_config.example.json --project-root /path/to/local/mathlib
```

The command is local-path-only and skips cleanly when no project path is available.

Optional selected-module verification:

```bash
python scripts/run_mathlib_module_verification.py --use-synthetic-request --project-root examples/mathlib_micro_subset
python scripts/run_real_mathlib_demo.py --project-root /path/to/mathlib4 --run-module-verification --execution-mode lake-env-lean --allow-execution --allow-missing-verifier
```

Use `lake env lean` mode for real Mathlib/Lake projects. Raw Lean mode is mainly
for synthetic or simple projects.

## 6. Boundary Reminder

CLI success is not proof. Demo success is not proof. Only verifier, trusted
importer, finite validator, or chain audit evidence promotes truth.
