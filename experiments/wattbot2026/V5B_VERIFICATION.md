# WattBot 2026 — V5b reproducibility and evidence boundary

**Authority level: engineering release candidate; official Kaggle V5b score UNKNOWN.**

This note does not replace the competition's official `WRITEUP_TEMPLATE.md`.
If V5b attains a top-three position, copy that official template, pin the
actual score-producing Git tag, and independently rerun the exact source
to qualify the entry.

## Competition and official external authority

- Competition: https://www.kaggle.com/competitions/WattBot2026
- Current independently authenticated MathGraph public incumbent:
  **0.537**, submission **57018114**, Kaggle COMPLETE,
  [read-only audit](https://github.com/metalogiclabs/mathgraph/actions/runs/37978640761).
- The leader in that snapshot scored **0.939**; #1 has NOT been attained.
- The public score weights: answer_value 0.75, citation ref_id F1 0.20,
  correctly formatted unanswerable rows 0.05. A published score does not
  establish real-world scientific entailment.

## Source and model input boundaries

- Official `Score.py` SHA-256:
  `e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075`.
- Full reader source Git blob:
  `4e1350ef72a44a333862dec23c737a2262ab99bc`.
- Development lesson compiler source Git blob:
  `99189ba7c9be96909279f9fc5e5590dc6f317772`.
- Original V4 source/transport generator blob:
  `509da00a860c403c71f484de481aa4458dc0c954`.
- ArXiv source manifest SHA-256:
  `4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9`.
- Report source manifest SHA-256:
  `a1720d14806ff219eaac8e0e8b8a5c8d6e87f596bba1a852505374ab4343b77d`.
- Official corpus acquisition: 114 attempted pinned arXiv sources,
  112 readable; 8 pinned reports attempted, 7 readable. Missing sources
  remain named UNKNOWN rather than silently substituted.
- Six 1100-character question-centred page-exact PDF excerpts supplied
  to each of two `google/gemini-2.5-flash-lite` model calls.
- Two development TRAIN worked examples per question, selected only from
  the 182 allowed development rows; all 63 previously inspected TRAIN
  holdout rows excluded from example bank. No protected TEST labels.
- Both model calls have `temperature=0.0` but backend replay
  determinism is **not yet independently established**. Do not claim
  bit-identical reruns without evidence.

## Distinct warrant states

1. Exact PDF page quotation independently checked:
   **PAGE_QUOTE_VERIFIED** only for source occurrence; NOT scientific entailment.
2. Nonblank model value whose claimed quotation could not be anchored:
   **CANDIDATE_UNVERIFIED**. Never mislabel as page-verified.
3. Explicit first-reader `is_blank` with no accepted lesson value:
   preserve `is_blank` plus blank evidence fields; this is an
   acknowledged refusal, NOT proof no scientific source could exist.
4. Invalid/missing answer after both reads: deterministic numeric fallback
   with explicit source-literal/provenance checks, still not semantic proof.

## Qualified experiments and release line

- Baseline official score: [V4 0.537](https://github.com/metalogiclabs/mathgraph/actions/runs/37978640761).
- [Two development example reader, official 63 TRAIN 0.69074074](https://github.com/metalogiclabs/mathgraph/actions/runs/37985937618),
  same-response primary comparator 0.61058201.
- [Exact V4-style V5b policy official TRAIN 0.70873016](https://github.com/metalogiclabs/mathgraph/actions/runs/37989697422);
  0.61058201 same-response initial provisional comparator.
- [V5b preflight](https://github.com/metalogiclabs/mathgraph/actions/runs/37990125234)
  passed, including numeric zero, explicit blank and null transport.
- [Full V5b generation-only qualification](https://github.com/metalogiclabs/mathgraph/actions/runs/37994161213):
  NO Kaggle submission in this workflow. Until success and exact CSV hash
  are inspected, a full protected TEST candidate is **UNKNOWN**.

A favorable reused TRAIN holdout result does not predict an identical
public Kaggle score. The 63-row holdout was inspected repeatedly, and
cross-model results cannot be added to same-response policy gains.

## Local reproducibility on authorized data

Pin the qualified branch/commit and provide the official downloaded
`WattBot2026.zip` and a locally supplied `OPENROUTER_API_KEY`. Never
commit or print the secret.

```bash
python -m pip install kaggle pandas numpy requests pymupdf pytest
python experiments/wattbot2026/submit_verified_lesson_v5.py --self-test
python experiments/wattbot2026/submit_verified_lesson_v5.py \
  --preflight-official-zip WattBot2026.zip
python experiments/wattbot2026/submit_verified_lesson_v5.py \
  --official-zip WattBot2026.zip --out /tmp/mathgraph_v5b.csv
python experiments/wattbot2026/submission_gate.py \
  --official-zip WattBot2026.zip --submission /tmp/mathgraph_v5b.csv
```

These commands **generate and validate only**; they do not spend Kaggle
submission quota. Never publish the protected TEST predictions or the
copyrighted source PDFs as GitHub Actions artifacts.

## Final top-three release gates

- Freeze source commit/tag **before** producing the scored Kaggle file.
- Check identical authoritative source manifests, stable official scorer
  SHA-256 and complete 317 unique ordered IDs.
- Reject any empty/null cell under ordinary Kaggle/pandas CSV parsing.
- Verify budget, provider availability and seed/replay determinism claims
  without relying on unsupported provider parameters.
- Obtain Kaggle `SubmissionStatus.COMPLETE`, exact official public score,
  rank, and distinguish public from hidden private evaluation.
- Use competition-official `WRITEUP_TEMPLATE.md` and the code-producing
  Git tag with the required Writeup Index link, without hidden-label
  use or hardcoded/manual predictions.

**Invariant:** smallest warranted present preserving the protected future.
A promising scoring candidate never becomes a verified scientific statement
merely because a number or citation matches.
