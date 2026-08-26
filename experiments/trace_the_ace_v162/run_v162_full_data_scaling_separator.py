#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

HERE = Path(__file__).resolve().parent
V145 = HERE.parent / 'trace_the_ace_v145'
sys.path.insert(0, str(V145))
from run_v145_semantic_gate import build_v75
from v75_canonical_trajectory import load_training, trajectory_views, load_transcript, SEED


def safe_logit(p):
    return logit(np.clip(np.asarray(p, float), 1e-5, 1 - 1e-5))


def objective_prior(train_obj, train_y, val_obj, alpha=2.0):
    mu = (float(np.sum(train_y)) + 1.0) / (len(train_y) + 2.0)
    sums, counts = {}, {}
    for o, y in zip(train_obj, train_y):
        o = str(o); sums[o] = sums.get(o, 0.0) + float(y); counts[o] = counts.get(o, 0) + 1
    out = np.empty(len(val_obj), float)
    for i, o in enumerate(val_obj):
        o = str(o); n = counts.get(o, 0); s = sums.get(o, 0.0)
        out[i] = (s + alpha * mu) / (n + alpha) if n else mu
    return np.clip(out, 1e-5, 1 - 1e-5)


def compile_all(frame, transcripts: Path):
    cache, views, nums, keep = {}, [], [], []
    missing = set()
    for i, r in enumerate(frame.itertuples(index=False), 1):
        sid, obj = str(r.session_id), str(r.learning_objective)
        p = transcripts / f'{sid}.csv'
        if not p.exists():
            missing.add(sid)
            continue
        if sid not in cache:
            cache[sid] = load_transcript(p)
        v, n, _ = trajectory_views(cache[sid], obj)
        views.append(v); nums.append(n); keep.append(i-1)
        if i % 5000 == 0:
            print(f'compiled {i}/{len(frame)} keep={len(keep)} missing_sessions={len(missing)}', flush=True)
    if not keep:
        raise RuntimeError('no rows with transcript coverage')
    f = frame.iloc[keep].reset_index(drop=True)
    return f, views, np.vstack(nums), len(missing)


def fit_predict(X, y, tr, va):
    m = LogisticRegression(C=.25, max_iter=400, solver='liblinear', random_state=SEED)
    m.fit(X[tr], y[tr])
    return np.clip(m.predict_proba(X[va])[:,1], 1e-5, 1-1e-5)


def main(a):
    frame = load_training(a.features, a.labels).reset_index(drop=True)
    print({'source_rows': len(frame), 'source_sessions': int(frame.session_id.nunique()), 'source_objectives': int(frame.learning_objective.nunique())}, flush=True)
    frame, views, numeric, missing_sessions = compile_all(frame, a.transcripts)
    print({'covered_rows': len(frame), 'covered_sessions': int(frame.session_id.nunique()), 'missing_sessions': missing_sessions}, flush=True)
    X = build_v75(frame, views, numeric)
    y = frame.target.to_numpy(int)
    groups = frame.session_id.astype(str).to_numpy()
    obj = frame.learning_objective.astype(str).to_numpy()

    splitter = GroupShuffleSplit(n_splits=1, test_size=.20, random_state=SEED)
    tr_all, va = next(splitter.split(np.zeros(len(y)), y, groups))
    # Frozen 8k training comparator drawn only from the same training-group pool.
    rng = np.random.default_rng(SEED)
    n_small = min(a.small_train, len(tr_all))
    tr_small = np.sort(rng.choice(tr_all, size=n_small, replace=False))

    p_small = fit_predict(X, y, tr_small, va)
    p_full = fit_predict(X, y, tr_all, va)

    # Objective-prior graft is a retained cheap capability; test it on both scales.
    pp_small = objective_prior(obj[tr_small], y[tr_small], obj[va], 2.0)
    pp_full = objective_prior(obj[tr_all], y[tr_all], obj[va], 2.0)
    # Fixed 0.40 is the previously retained V156 transfer setting, not tuned here.
    pg_small = expit(.60*safe_logit(p_small) + .40*safe_logit(pp_small))
    pg_full = expit(.60*safe_logit(p_full) + .40*safe_logit(pp_full))

    def metrics(p):
        return {'logloss': float(log_loss(y[va], p)), 'auc': float(roc_auc_score(y[va], p))}
    ms, mf, mgs, mgf = map(metrics, (p_small,p_full,pg_small,pg_full))
    scale_gain = ms['logloss'] - mf['logloss']
    graft_scale_gain = mgs['logloss'] - mgf['logloss']
    full_graft_gain = mf['logloss'] - mgf['logloss']
    if graft_scale_gain >= .005:
        decision = 'FULL_DATA_PHASE_CHANGE'
    elif graft_scale_gain >= .0025:
        decision = 'FULL_DATA_STRONG_GAIN'
    elif scale_gain >= .0015:
        decision = 'FULL_DATA_BASE_GAIN'
    else:
        decision = 'DATA_SCALE_NOT_THE_MISSING_GAIN'
    out = {
      'protocol':'V162_FULL_DATA_SCALING_SEPARATOR',
      'source_rows': int(len(load_training(a.features,a.labels))),
      'covered_rows': int(len(frame)), 'missing_sessions': int(missing_sessions),
      'validation_rows': int(len(va)), 'small_train_rows': int(len(tr_small)), 'full_train_rows': int(len(tr_all)),
      'small_v75': ms, 'full_v75': mf, 'small_v75_prior': mgs, 'full_v75_prior': mgf,
      'scale_gain': float(scale_gain), 'grafted_scale_gain': float(graft_scale_gain),
      'full_prior_gain': float(full_graft_gain), 'decision': decision,
      'residual':'Recent V145-V161 separators repeatedly used an 8k portable bundle. Test whether training-data truncation itself is the live obstruction before inventing another representation.'
    }
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--features',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--transcripts',type=Path,required=True); p.add_argument('--small-train',type=int,default=8000); p.add_argument('--out',type=Path,default=Path('v162_results.json')); main(p.parse_args())
