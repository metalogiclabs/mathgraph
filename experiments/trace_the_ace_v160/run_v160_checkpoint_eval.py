#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from scipy.special import expit

HERE = Path(__file__).resolve().parent
V158_PATH = HERE.parent / "trace_the_ace_v158" / "run_v158_long_context_residual.py"
spec = importlib.util.spec_from_file_location("v158_core", V158_PATH)
v158 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v158)


def finite_residual(z):
    z = np.asarray(z, dtype=np.float64)
    bad = ~np.isfinite(z)
    if bad.any():
        print(f"NONFINITE_RESIDUAL_OUTPUTS {int(bad.sum())}/{len(z)} -> zero correction", flush=True)
        z = z.copy(); z[bad] = 0.0
    return np.clip(z, -4.0, 4.0)


def choose_lambda(y, pbase, d):
    pbase = np.nan_to_num(np.asarray(pbase, dtype=float), nan=0.5, posinf=1-1e-5, neginf=1e-5)
    pbase = np.clip(pbase, 1e-5, 1-1e-5)
    d = finite_residual(d)
    best = None
    for lam in (0.0, .10, .20, .35, .50, .75, 1.0):
        p = expit(v158.safe_logit(pbase) + lam * np.clip(4.0 * d, -4.0, 4.0))
        ll = float(log_loss(y, p))
        if best is None or ll < best[0]: best = (ll, lam)
    return float(best[1]), float(best[0])


def main(a):
    np.random.seed(v158.SEED); torch.manual_seed(v158.SEED); torch.cuda.manual_seed_all(v158.SEED)
    assert torch.cuda.is_available(), "V160 requires CUDA"

    frame = v158.load_training(a.features.resolve(), a.labels.resolve()).reset_index(drop=True)
    if a.limit and a.limit < len(frame):
        frame = frame.sample(n=a.limit, random_state=v158.SEED).reset_index(drop=True)
    transcripts = v158.resolve_transcripts(a.transcripts.resolve(), a.work.resolve())
    texts, rev_texts, wrong_texts, numeric, objectives = v158.compile_rows(frame, transcripts, a.char_cap)
    y = frame.target.to_numpy(int)
    groups = frame.session_id.astype(str).to_numpy()
    splits = list(GroupKFold(a.folds).split(np.zeros(len(y)), y, groups))
    tr, va = splits[a.fold - 1]

    gss = GroupShuffleSplit(n_splits=1, test_size=.16, random_state=v158.SEED + a.fold)
    mtr_rel, cal_rel = next(gss.split(np.zeros(len(tr)), y[tr], groups[tr]))
    mtr, cal = tr[mtr_rel], tr[cal_rel]

    # Reconstruct the exact base/prior calibration used by V159 session fold 1.
    _, prior_weight = v158.inner_oof_base(numeric[mtr], objectives[mtr], y[mtr], groups[mtr])
    p_cal = v158.full_base_predict(numeric[mtr], objectives[mtr], y[mtr], numeric[cal], objectives[cal], prior_weight)
    p_base = v158.full_base_predict(numeric[tr], objectives[tr], y[tr], numeric[va], objectives[va], prior_weight)

    ckpts = sorted(p.parent for p in a.checkpoint_root.resolve().rglob('.complete'))
    if not ckpts:
        raise FileNotFoundError(f"No complete V159 checkpoint under {a.checkpoint_root}")
    ckpt = ckpts[0]
    print(f"USING_CHECKPOINT {ckpt}", flush=True)

    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tok = AutoTokenizer.from_pretrained(ckpt, trust_remote_code=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        ckpt, num_labels=1, problem_type='regression', trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    ).cuda().eval()

    d_cal = finite_residual(v158.predict_residual(model, tok, [texts[i] for i in cal], a.max_len, a.eval_batch))
    lam, cal_ll = choose_lambda(y[cal], p_cal, d_cal)
    print(json.dumps({"selected_lambda": lam, "calibration_logloss": cal_ll, "prior_weight": prior_weight}), flush=True)

    d = finite_residual(v158.predict_residual(model, tok, [texts[i] for i in va], a.max_len, a.eval_batch))
    d_rev = finite_residual(v158.predict_residual(model, tok, [rev_texts[i] for i in va], a.max_len, a.eval_batch))
    d_wrong = finite_residual(v158.predict_residual(model, tok, [wrong_texts[i] for i in va], a.max_len, a.eval_batch))
    corr = lambda z: expit(v158.safe_logit(p_base) + lam * np.clip(4.0 * z, -4.0, 4.0))
    p, pr, pw = corr(d), corr(d_rev), corr(d_wrong)

    base_ll = float(log_loss(y[va], p_base)); resid_ll = float(log_loss(y[va], p))
    rev_ll = float(log_loss(y[va], pr)); wrong_ll = float(log_loss(y[va], pw))
    improvement = base_ll - resid_ll
    out = {
        "protocol": "V160_RESCUED_V159_SESSION_FOLD_CHECKPOINT_EVAL",
        "fold": a.fold,
        "checkpoint": str(ckpt),
        "rows": int(len(va)),
        "prior_weight": float(prior_weight),
        "lambda": lam,
        "calibration_logloss": cal_ll,
        "base_logloss": base_ll,
        "residual_logloss": resid_ll,
        "improvement": improvement,
        "base_auc": float(roc_auc_score(y[va], p_base)),
        "residual_auc": float(roc_auc_score(y[va], p)),
        "chronology_reversed_logloss": rev_ll,
        "objective_shuffled_logloss": wrong_ll,
        "chronology_separator": rev_ll - resid_ll,
        "objective_separator": wrong_ll - resid_ll,
        "decision": "CONTINUE_V159_FULL" if improvement >= .005 and rev_ll - resid_ll >= .001 and wrong_ll - resid_ll >= .001 else "STOP_OR_REDESIGN",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--features', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    p.add_argument('--transcripts', type=Path, required=True)
    p.add_argument('--checkpoint-root', type=Path, default=Path('/workspace/trace-ace-checkpoints/v159'))
    p.add_argument('--work', type=Path, default=Path('/workspace/trace-ace-work/v160'))
    p.add_argument('--out', type=Path, default=Path('/workspace/trace-ace-results/v160_results.json'))
    p.add_argument('--limit', type=int, default=8000)
    p.add_argument('--folds', type=int, default=3)
    p.add_argument('--fold', type=int, default=1)
    p.add_argument('--max-len', type=int, default=8192)
    p.add_argument('--char-cap', type=int, default=30000)
    p.add_argument('--eval-batch', type=int, default=2)
    main(p.parse_args())
