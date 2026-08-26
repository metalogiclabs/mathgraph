#!/usr/bin/env python3
"""V159: numerically stable continuation of V158 with persistent fold checkpoints.

Scientific representation/gate are unchanged from V158. This wrapper only:
1) treats non-finite residual outputs conservatively as zero correction,
2) persists trained fold models on the RunPod workspace so retries do not repeat training,
3) logs non-finite counts explicitly.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
V158_PATH = HERE.parent / "trace_the_ace_v158" / "run_v158_long_context_residual.py"
spec = importlib.util.spec_from_file_location("v158_core", V158_PATH)
v158 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v158)

_orig_train = v158.train_residual
_orig_predict = v158.predict_residual


def _checkpoint_key(model_name, texts, max_len, epochs, lr, batch, grad_accum):
    h = hashlib.sha256()
    h.update(str(model_name).encode())
    h.update(str((len(texts), max_len, epochs, lr, batch, grad_accum)).encode())
    if texts:
        h.update(texts[0][:2000].encode("utf-8", "ignore"))
        h.update(texts[-1][-2000:].encode("utf-8", "ignore"))
    return h.hexdigest()[:20]


def stable_train(model_name, tokenizer, texts, targets, max_len, epochs, lr, batch, grad_accum):
    root = Path(os.environ.get("V159_CHECKPOINT_ROOT", "/workspace/trace-ace-checkpoints/v159"))
    key = _checkpoint_key(model_name, texts, max_len, epochs, lr, batch, grad_accum)
    ckpt = root / key
    marker = ckpt / ".complete"
    if marker.exists():
        print(f"REUSING_CHECKPOINT {ckpt}", flush=True)
        from transformers import AutoModelForSequenceClassification
        model = AutoModelForSequenceClassification.from_pretrained(
            ckpt, num_labels=1, problem_type="regression", trust_remote_code=True,
            torch_dtype=torch.bfloat16,
        ).cuda()
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()
        return model

    model = _orig_train(model_name, tokenizer, texts, targets, max_len, epochs, lr, batch, grad_accum)
    ckpt.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(ckpt, safe_serialization=True)
    tokenizer.save_pretrained(ckpt)
    marker.touch()
    print(f"SAVED_CHECKPOINT {ckpt}", flush=True)
    return model


def stable_predict(model, tokenizer, texts, max_len, batch):
    z = np.asarray(_orig_predict(model, tokenizer, texts, max_len, batch), dtype=np.float64)
    bad = ~np.isfinite(z)
    if bad.any():
        n = int(bad.sum())
        print(f"NONFINITE_RESIDUAL_OUTPUTS {n}/{len(z)} -> zero correction", flush=True)
        z = z.copy()
        z[bad] = 0.0
    return np.clip(z, -4.0, 4.0)


def stable_choose_lambda(y, pbase, d):
    pbase = np.nan_to_num(np.asarray(pbase, dtype=float), nan=0.5, posinf=1-1e-5, neginf=1e-5)
    pbase = np.clip(pbase, 1e-5, 1-1e-5)
    d = np.nan_to_num(np.asarray(d, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    return v158_choose_lambda_original(y, pbase, d)


v158_choose_lambda_original = v158.choose_lambda
v158.train_residual = stable_train
v158.predict_residual = stable_predict
v158.choose_lambda = stable_choose_lambda

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--transcripts", type=Path, required=True)
    p.add_argument("--work", type=Path, default=Path("/workspace/trace-ace-work/v159"))
    p.add_argument("--out", type=Path, default=Path("v159_results.json"))
    p.add_argument("--model", default=v158.MODEL_DEFAULT)
    p.add_argument("--limit", type=int, default=8000)
    p.add_argument("--folds", type=int, default=3)
    p.add_argument("--max-len", type=int, default=8192)
    p.add_argument("--char-cap", type=int, default=30000)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--eval-batch", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=8)
    v158.main(p.parse_args())
