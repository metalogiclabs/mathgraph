#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
V146 = HERE.parent / "trace_the_ace_v146"
sys.path.insert(0, str(V146))
from run_v146_residual_router import load_bundle, fit_base, inner_oof_base

SPLITS = ("full_session", "full_objective", "control_session", "control_objective")


def select_split(name, X, y, sg, og, ci):
    if name == "full_session":
        return X, y, np.asarray(sg).astype(str), np.arange(len(y), dtype=np.int64)
    if name == "full_objective":
        return X, y, np.asarray(og).astype(str), np.arange(len(y), dtype=np.int64)
    if name == "control_session":
        return X[ci], y[ci], np.asarray(sg)[ci].astype(str), np.asarray(ci, dtype=np.int64)
    if name == "control_objective":
        return X[ci], y[ci], np.asarray(og)[ci].astype(str), np.asarray(ci, dtype=np.int64)
    raise ValueError(name)


def build_cache(split_name: str, bundle: Path, out: Path, meta: Path):
    X, _S, y, sg, og, ci, _Sswap, _Sempty = load_bundle(bundle)
    Xs, ys, groups, source_index = select_split(split_name, X, y, sg, og, ci)
    groups = np.asarray(pd.Series(groups).astype(str))
    folds = list(GroupKFold(5).split(np.zeros(len(ys)), ys, groups))

    payload = {
        "protocol": np.asarray("V148_DURABLE_V75_CROSSFIT_CACHE"),
        "split": np.asarray(split_name),
        "source_index": source_index,
        "y": np.asarray(ys, dtype=np.int8),
        "groups": groups.astype(object),
    }
    records = []
    t0 = time.time()
    for k, (tr, va) in enumerate(folds, 1):
        ft0 = time.time()
        p_inner = inner_oof_base(Xs[tr], ys[tr], groups[tr])
        base = fit_base(Xs[tr], ys[tr])
        pb = np.clip(base.predict_proba(Xs[va])[:, 1], 1e-5, 1 - 1e-5)
        payload[f"fold{k}_tr"] = np.asarray(tr, dtype=np.int64)
        payload[f"fold{k}_va"] = np.asarray(va, dtype=np.int64)
        payload[f"fold{k}_p_inner"] = np.asarray(p_inner, dtype=np.float64)
        payload[f"fold{k}_p_heldout"] = np.asarray(pb, dtype=np.float64)
        rec = {
            "fold": k,
            "train_rows": int(len(tr)),
            "valid_rows": int(len(va)),
            "seconds": float(time.time() - ft0),
        }
        records.append(rec)
        print(f"CACHE {split_name} fold {k}/5 seconds={rec['seconds']:.1f}", flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **payload)
    summary = {
        "protocol": "V148_DURABLE_V75_CROSSFIT_CACHE",
        "split": split_name,
        "rows": int(len(ys)),
        "source_rows": int(len(y)),
        "folds": records,
        "total_seconds": float(time.time() - t0),
        "cache_bytes": int(out.stat().st_size),
    }
    meta.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


def self_test():
    assert set(SPLITS) == {"full_session", "full_objective", "control_session", "control_objective"}
    print("V148_CROSSFIT_CACHE_SELF_TEST_PASS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path)
    p.add_argument("--split", choices=SPLITS)
    p.add_argument("--out", type=Path)
    p.add_argument("--meta", type=Path)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        self_test()
        return
    if not all((a.bundle, a.split, a.out, a.meta)):
        p.error("--bundle --split --out --meta are required")
    build_cache(a.split, a.bundle.resolve(), a.out.resolve(), a.meta.resolve())


if __name__ == "__main__":
    main()
