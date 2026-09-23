# Public Demo

```bash
python scripts/run_public_demo.py --ensure-configs
python scripts/run_public_demo.py --out-dir demo_out
python scripts/run_public_demo.py --allow-execution --allow-missing-verifier --accept-verified-entries-in-memory --out-dir demo_out
```

The public demo uses repo-local synthetic fixtures, prints a concise summary, and
writes polished artifacts when `--out-dir` is supplied. Demo success is advisory
unless explicit verifier/importer/finite-validator/chain-audit evidence is present.


## Epistemic Status Cards

MathGraph's public surfaces keep four statuses separate:

- verification — may carry truth authority only when a verifier/importer/finite-validator/chain-audit boundary is present;
- human digest — understanding/exposition state only;
- statement fidelity — quality of the informal-to-formal correspondence, qualified independently;
- generalization — reusable-schema status only.

The last three do not promote truth.

Render the qualified real-artifact example:

```bash
python scripts/render_epistemic_status.py \
  --artifact artifacts/lawbook/finite_htilt_survivor_law_v1.json \
  --sidecar experiments/epistemic_orthogonality_v0/finite_htilt_survivor_state.json \
  --format markdown
```

The API artifact envelope also includes an `epistemic_status` field. Missing evidence is rendered as `UNKNOWN`, not inferred from adjacent statuses.
