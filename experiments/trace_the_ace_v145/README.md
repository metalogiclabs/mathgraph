# Trace the Ace V145 — semantic epistemic phase-change gate

This bundle tests the one change that is structurally different from V75–V135:
a frozen language model judges objective-specific student evidence instead of
having regular expressions decide whether an answer shows independent mastery.

It is **not a submission ZIP**. It spends no leaderboard slot. It produces
`v145_results.json` with one unambiguous decision:

- `PHASE_CHANGE_CONFIRMED`: semantic features reduce log loss by at least 0.003
  on both session-cold and objective-cold five-fold validation, win at least four
  folds in each regime, have a positive grouped-bootstrap lower bound, and a
  shuffled-row control does not improve the baseline. It must also beat two
  model-based counterfactuals: the wrong objective paired with real evidence,
  and the correct objective paired with no evidence.
- `DO_NOT_SPEND_SUBMISSION`: the semantic channel has not earned promotion.

## Canonical run: GitHub Actions controlling a RunPod GPU

The repository workflow targets a self-hosted runner labelled
`trace-ace-gpu`. Put the three private data files under
`/workspace/trace_the_ace` on the persistent RunPod volume, register the pod as
a GitHub runner with that label, then dispatch **Trace the Ace V145 Semantic
Gate**. GitHub records the frozen configuration and publishes the decision and
raw semantic scores as workflow artifacts.

## Direct fallback on an A100/H100 GPU

The transcript argument accepts either the extracted directory or the existing
603 MB transcript ZIP in Google Drive. The script extracts it once into `--work`.

```bash
pip install -q "vllm>=0.8" "transformers>=4.51" pandas scipy scikit-learn
python run_v145_semantic_gate.py \
  --features /path/to/train_features_TMQTWsB.csv \
  --labels /path/to/train_labels_44ujmj2.csv \
  --transcripts /path/to/trace_the_ace_transcripts_v123_single_run_fresh.zip \
  --model Qwen/Qwen3-8B-AWQ \
  --limit 8000 \
  --work /workspace/v145_work \
  --out /workspace/v145_sniff_results.json
```

The 8,000-row run is the sniff gate. If and only if it says
`PHASE_CHANGE_CONFIRMED`, rerun without `--limit` and preferably with the
competition-preloaded quantized model:

```bash
python run_v145_semantic_gate.py \
  --features /path/to/train_features_TMQTWsB.csv \
  --labels /path/to/train_labels_44ujmj2.csv \
  --transcripts /path/to/trace_the_ace_transcripts_v123_single_run_fresh.zip \
  --model Qwen/Qwen3-14B-AWQ \
  --work /workspace/v145_full \
  --out /workspace/v145_full_results.json
```

The semantic outputs are checkpointed in `semantic_scores.jsonl`, so rerunning
after an interruption resumes from the last completed row. Do not compare smoke
scores across these models; the promotion decision comes only from the two
group-cold gates and their controls.

## Quick integrity test

```bash
python run_v145_semantic_gate.py --self-test
```

If the full gate passes, the next step is to freeze the semantic extractor and
cross-fitted calibrator into a competition runtime, then smoke-test packaging.
Only that promoted runtime becomes a candidate for one of the final three full
submissions.
