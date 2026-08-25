#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
V145 = HERE.parent / "trace_the_ace_v145"
sys.path.insert(0, str(V145))
from run_v145_semantic_gate import build_v75
from v75_canonical_trajectory import SEED

ALPHA = 2.0
WEIGHT = 0.40


def safe_logit(p):
    return logit(np.clip(np.asarray(p, float), 1e-5, 1 - 1e-5))


def objective_prior(train_obj, train_y, val_obj, alpha=ALPHA):
    mu = (float(np.sum(train_y)) + 1.0) / (len(train_y) + 2.0)
    sums, counts = {}, {}
    for o, y in zip(train_obj, train_y):
        o = str(o)
        sums[o] = sums.get(o, 0.0) + float(y)
        counts[o] = counts.get(o, 0) + 1
    out = np.empty(len(val_obj), float)
    for i, o in enumerate(val_obj):
        o = str(o)
        n = counts.get(o, 0)
        s = sums.get(o, 0.0)
        out[i] = (s + alpha * mu) / (n + alpha) if n else mu
    return np.clip(out, 1e-5, 1 - 1e-5)


def load_bundle(path: Path):
    b = np.load(path, allow_pickle=True)
    frame = pd.DataFrame({"learning_objective": b["objective"].astype(str)})
    views = []
    for i in range(len(frame)):
        row = {}
        for key in ("raw", "student", "local", "canonical", "terminal"):
            v = b[f"view_{key}"][i]
            row[key] = v.item() if hasattr(v, "item") else str(v)
        views.append(row)
    X = build_v75(frame, views, b["numeric"].astype(float))
    return X, b["y"].astype(int), b["session_id"].astype(str), b["objective_group"].astype(str)


def run_fold(bundle: Path, fold: int, out: Path):
    X, y, sessions, obj = load_bundle(bundle)
    splits = list(GroupKFold(5).split(np.zeros(len(y)), y, sessions))
    tr, va = splits[fold - 1]

    base = LogisticRegression(C=.25, max_iter=350, solver="liblinear", random_state=SEED)
    base.fit(X[tr], y[tr])
    pb = np.clip(base.predict_proba(X[va])[:, 1], 1e-5, 1 - 1e-5)

    pp = objective_prior(obj[tr], y[tr], obj[va], ALPHA)
    pg = expit((1.0 - WEIGHT) * safe_logit(pb) + WEIGHT * safe_logit(pp))

    rng = np.random.default_rng(SEED)
    sh = obj[rng.permutation(len(obj))]
    ps = objective_prior(sh[tr], y[tr], sh[va], ALPHA)
    psh = expit((1.0 - WEIGHT) * safe_logit(pb) + WEIGHT * safe_logit(ps))

    res = {
        "protocol": "V156_V75_FIXED_OBJECTIVE_PRIOR_GRAFT",
        "warning": "TRANSFER_GATE_NOT_SUBMISSION_EVIDENCE",
        "fold": fold,
        "rows": int(len(va)),
        "alpha": ALPHA,
        "weight": WEIGHT,
        "base_logloss": float(log_loss(y[va], pb)),
        "graft_logloss": float(log_loss(y[va], pg)),
        "shuffled_logloss": float(log_loss(y[va], psh)),
        "improvement": float(log_loss(y[va], pb) - log_loss(y[va], pg)),
        "shuffled_improvement": float(log_loss(y[va], pb) - log_loss(y[va], psh)),
        "base_auc": float(roc_auc_score(y[va], pb)),
        "graft_auc": float(roc_auc_score(y[va], pg)),
        "win": bool(log_loss(y[va], pg) < log_loss(y[va], pb)),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2), flush=True)


def merge(root: Path, out: Path):
    files = sorted(root.rglob("v156_fold_*.json"))
    if len(files) != 5:
        raise RuntimeError(f"expected 5 fold files, found {len(files)}: {files}")
    folds = [json.loads(p.read_text()) for p in files]
    folds.sort(key=lambda x: x["fold"])
    n = sum(f["rows"] for f in folds)
    def wavg(key):
        return sum(f[key] * f["rows"] for f in folds) / n
    base = wavg("base_logloss")
    graft = wavg("graft_logloss")
    shuf = wavg("shuffled_logloss")
    improvement = base - graft
    shuffled_improvement = base - shuf
    separator = improvement - shuffled_improvement
    wins = sum(bool(f["win"]) for f in folds)
    if improvement >= 0.0015 and wins >= 4 and separator >= 0.0015:
        decision = "PRIOR_GRAFT_SURVIVES_V75_STRONG_STACK"
    elif improvement >= 0.0005 and wins >= 3 and separator >= 0.00075:
        decision = "SMALL_V75_GRAFT_GAIN"
    else:
        decision = "PRIOR_GAIN_ABSORBED_BY_V75"
    res = {
        "protocol": "V156_V75_FIXED_OBJECTIVE_PRIOR_GRAFT",
        "warning": "TRANSFER_GATE_NOT_SUBMISSION_EVIDENCE",
        "rows": n,
        "alpha": ALPHA,
        "weight": WEIGHT,
        "base_logloss": base,
        "graft_logloss": graft,
        "shuffled_logloss": shuf,
        "improvement": improvement,
        "shuffled_improvement": shuffled_improvement,
        "separator": separator,
        "fold_wins": wins,
        "folds": folds,
        "decision": decision,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path)
    p.add_argument("--fold", type=int)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--merge-root", type=Path)
    a = p.parse_args()
    if a.merge_root:
        merge(a.merge_root, a.out)
    else:
        if not a.bundle or not a.fold or not 1 <= a.fold <= 5:
            p.error("fold mode requires --bundle and --fold 1..5")
        run_fold(a.bundle.resolve(), a.fold, a.out.resolve())


if __name__ == "__main__":
    main()
