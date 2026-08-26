#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import json
import math
import random
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from scipy.sparse import csr_matrix, hstack

HERE = Path(__file__).resolve().parent
V145 = HERE.parent / "trace_the_ace_v145"
sys.path.insert(0, str(V145))
from v71_mastery_events import inspect_headers, load_transcript, normalize_roles
from v75_canonical_trajectory import trajectory_views

SEED = 20260826
MODEL_DEFAULT = "answerdotai/ModernBERT-base"


def safe_logit(p):
    return logit(np.clip(np.asarray(p, dtype=float), 1e-5, 1 - 1e-5))


def resolve_transcripts(path: Path, work: Path) -> Path:
    if path.is_dir():
        roots = [path] + [p for p in path.rglob("*") if p.is_dir()]
    elif path.suffix.lower() == ".zip":
        out = work / "transcripts_extracted"
        marker = out / ".complete"
        if not marker.exists():
            if out.exists():
                shutil.rmtree(out)
            out.mkdir(parents=True)
            print(f"Extracting {path} -> {out}", flush=True)
            with zipfile.ZipFile(path) as zf:
                zf.extractall(out)
            marker.touch()
        roots = [out] + [p for p in out.rglob("*") if p.is_dir()]
    else:
        raise ValueError(f"transcripts must be directory or zip: {path}")
    scored = []
    for p in roots:
        try:
            n = sum(1 for _ in p.glob("*.csv"))
        except OSError:
            n = 0
        if n:
            scored.append((n, p))
    if not scored:
        raise FileNotFoundError("No transcript CSV directory found")
    root = max(scored)[1]
    print(f"Transcript directory: {root}", flush=True)
    return root


def load_training(features: Path, labels: Path) -> pd.DataFrame:
    # Inspect headers first; schema decisions must be evidence-based.
    fcols = inspect_headers(features)
    lcols = inspect_headers(labels)
    print("features columns", fcols)
    print("labels columns", lcols)
    need = {"response_id", "session_id", "learning_objective"}
    if not need.issubset(fcols):
        raise ValueError(f"features missing {sorted(need - set(fcols))}")
    target = "is_correct" if "is_correct" in lcols else "correct" if "correct" in lcols else None
    if target is None:
        raise ValueError(f"labels need is_correct or correct; got {lcols}")
    f = pd.read_csv(features)
    y = pd.read_csv(labels)
    return f.merge(y[["response_id", target]], on="response_id", validate="one_to_one").rename(columns={target: "target"})


def ordered_transcript(df: pd.DataFrame) -> tuple[str, str]:
    d = normalize_roles(df).reset_index(drop=True)
    lines = []
    for i, r in enumerate(d[["role_repaired", "content"]].itertuples(index=False)):
        role = str(r.role_repaired).upper()
        content = " ".join(str(r.content).split())
        if content:
            lines.append(f"[{i:04d}] [{role}] {content}")
    raw = "\n".join(lines)
    rev = "\n".join(reversed(lines))
    return raw, rev


def cap_transcript(text: str, char_cap: int) -> str:
    if len(text) <= char_cap:
        return text
    # Keep both temporal ends. The target remains outside this clipped region.
    head = int(char_cap * 0.38)
    tail = char_cap - head
    return text[:head] + "\n[...MIDDLE OMITTED ONLY BECAUSE OF CONTEXT LIMIT...]\n" + text[-tail:]


def render(objective: str, transcript: str, char_cap: int) -> str:
    return (
        "[TARGET LEARNING OBJECTIVE]\n" + str(objective).strip() +
        "\n\n[ORDERED ROLE-LABELLED TUTORING TRANSCRIPT]\n" + cap_transcript(transcript, char_cap) +
        "\n\n[PREDICT STUDENT CORRECTNESS RESIDUAL FOR THIS TARGET]"
    )


def compile_rows(frame: pd.DataFrame, transcripts: Path, char_cap: int):
    cache = {}
    texts, reversed_texts, numeric = [], [], []
    objectives = frame.learning_objective.astype(str).to_numpy()
    rng = np.random.default_rng(SEED + 91)
    wrong_objectives = objectives[rng.permutation(len(objectives))]
    for i, row in enumerate(frame.itertuples(index=False), 1):
        sid = str(row.session_id)
        if sid not in cache:
            df = load_transcript(transcripts / f"{sid}.csv")
            raw, rev = ordered_transcript(df)
            cache[sid] = (df, raw, rev)
        df, raw, rev = cache[sid]
        _, feats, _ = trajectory_views(df, str(row.learning_objective))
        numeric.append(feats)
        texts.append(render(str(row.learning_objective), raw, char_cap))
        reversed_texts.append(render(str(row.learning_objective), rev, char_cap))
        if i % 1000 == 0:
            print(f"compiled {i}/{len(frame)}", flush=True)
    wrong_texts = [render(w, cache[str(r.session_id)][1], char_cap) for w, r in zip(wrong_objectives, frame.itertuples(index=False))]
    return texts, reversed_texts, wrong_texts, np.vstack(numeric), objectives


def fit_base(num, obj, y):
    enc = OneHotEncoder(handle_unknown="ignore", min_frequency=2)
    O = enc.fit_transform(np.asarray(obj).reshape(-1, 1))
    sc = StandardScaler().fit(num)
    X = hstack([O, csr_matrix(sc.transform(num))], format="csr")
    m = LogisticRegression(C=.25, max_iter=300, solver="liblinear", random_state=SEED).fit(X, y)
    return enc, sc, m


def predict_base(model, num, obj):
    enc, sc, m = model
    X = hstack([enc.transform(np.asarray(obj).reshape(-1, 1)), csr_matrix(sc.transform(num))], format="csr")
    return np.clip(m.predict_proba(X)[:, 1], 1e-5, 1 - 1e-5)


def objective_prior(train_obj, train_y, val_obj, alpha=2.0):
    mu = (float(train_y.sum()) + 1.0) / (len(train_y) + 2.0)
    sums, counts = {}, {}
    for o, y in zip(train_obj, train_y):
        sums[o] = sums.get(o, 0.0) + float(y)
        counts[o] = counts.get(o, 0) + 1
    out = np.empty(len(val_obj), dtype=float)
    for i, o in enumerate(val_obj):
        n, s = counts.get(o, 0), sums.get(o, 0.0)
        out[i] = (s + alpha * mu) / (n + alpha) if n else mu
    return np.clip(out, 1e-5, 1 - 1e-5)


def inner_oof_base(num, obj, y, groups):
    groups = np.asarray(groups).astype(str)
    n = min(4, len(np.unique(groups)))
    if n < 2:
        raise ValueError("not enough groups for inner cross-fit")
    pb = np.zeros(len(y)); pp = np.zeros(len(y))
    for tr, va in GroupKFold(n).split(np.zeros(len(y)), y, groups):
        bm = fit_base(num[tr], obj[tr], y[tr])
        pb[va] = predict_base(bm, num[va], obj[va])
        pp[va] = objective_prior(obj[tr], y[tr], obj[va], alpha=2.0)
    best = None
    for w in (0.0, .025, .05, .10, .15, .20, .30, .40):
        p = expit((1 - w) * safe_logit(pb) + w * safe_logit(pp))
        ll = float(log_loss(y, p))
        if best is None or ll < best[0]:
            best = (ll, w)
    w = best[1]
    return expit((1 - w) * safe_logit(pb) + w * safe_logit(pp)), float(w)


def full_base_predict(num_tr, obj_tr, y_tr, num_va, obj_va, prior_weight):
    bm = fit_base(num_tr, obj_tr, y_tr)
    pb = predict_base(bm, num_va, obj_va)
    pp = objective_prior(obj_tr, y_tr, obj_va, alpha=2.0)
    return expit((1 - prior_weight) * safe_logit(pb) + prior_weight * safe_logit(pp))


class TextResidualDataset(torch.utils.data.Dataset):
    def __init__(self, texts, labels=None):
        self.texts = texts
        self.labels = labels
    def __len__(self):
        return len(self.texts)
    def __getitem__(self, i):
        row = {"text": self.texts[i]}
        if self.labels is not None:
            row["label"] = float(self.labels[i])
        return row


class Collator:
    def __init__(self, tok, max_len):
        self.tok, self.max_len = tok, max_len
    def __call__(self, rows):
        enc = self.tok([r["text"] for r in rows], padding=True, truncation=True,
                       max_length=self.max_len, return_tensors="pt")
        if "label" in rows[0]:
            enc["labels"] = torch.tensor([r["label"] for r in rows], dtype=torch.float32)
        return enc


def make_model(model_name):
    from transformers import AutoModelForSequenceClassification
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=1, problem_type="regression", torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    return model


def train_residual(model_name, tokenizer, texts, targets, max_len, epochs, lr, batch, grad_accum):
    from torch.utils.data import DataLoader
    model = make_model(model_name).cuda()
    model.train()
    ds = TextResidualDataset(texts, targets)
    dl = DataLoader(ds, batch_size=batch, shuffle=True, collate_fn=Collator(tokenizer, max_len),
                    generator=torch.Generator().manual_seed(SEED))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.02)
    total_steps = max(1, math.ceil(len(dl) * epochs / grad_accum))
    warm = max(1, int(total_steps * 0.06))
    def lr_scale(step):
        if step < warm: return step / warm
        x = (step - warm) / max(1, total_steps - warm)
        return max(0.05, 0.5 * (1 + math.cos(math.pi * x)))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_scale)
    scaler_steps = 0
    opt.zero_grad(set_to_none=True)
    for ep in range(epochs):
        for step, batch_data in enumerate(dl, 1):
            batch_data = {k: v.cuda(non_blocking=True) for k, v in batch_data.items()}
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = model(**batch_data).loss / grad_accum
            loss.backward()
            if step % grad_accum == 0 or step == len(dl):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step(); sched.step(); opt.zero_grad(set_to_none=True); scaler_steps += 1
                if scaler_steps % 25 == 0:
                    print(f"optimizer_step={scaler_steps}/{total_steps} loss={float(loss)*grad_accum:.5f}", flush=True)
    return model


def predict_residual(model, tokenizer, texts, max_len, batch):
    from torch.utils.data import DataLoader
    model.eval()
    ds = TextResidualDataset(texts)
    dl = DataLoader(ds, batch_size=batch, shuffle=False, collate_fn=Collator(tokenizer, max_len))
    out = []
    with torch.no_grad():
        for bd in dl:
            bd = {k: v.cuda(non_blocking=True) for k, v in bd.items()}
            with torch.autocast("cuda", dtype=torch.bfloat16):
                z = model(**bd).logits.squeeze(-1).float().cpu().numpy()
            out.append(z)
    return np.concatenate(out)


def smooth_logit_target(y, p):
    ys = np.where(np.asarray(y) > 0, .98, .02)
    return np.clip(safe_logit(ys) - safe_logit(p), -4.0, 4.0) / 4.0


def choose_lambda(y, pbase, d):
    best = None
    for lam in (0.0, .10, .20, .35, .50, .75, 1.0):
        p = expit(safe_logit(pbase) + lam * np.clip(4.0 * d, -4.0, 4.0))
        ll = float(log_loss(y, p))
        if best is None or ll < best[0]: best = (ll, lam)
    return float(best[1]), float(best[0])


def eval_regime(name, frame, texts, reversed_texts, wrong_texts, numeric, objectives, groups, args, tokenizer):
    y = frame.target.to_numpy(int)
    groups = np.asarray(groups).astype(str)
    splits = list(GroupKFold(args.folds).split(np.zeros(len(y)), y, groups))
    p0 = np.zeros(len(y)); p1 = np.zeros(len(y)); prev = np.zeros(len(y)); pwrong = np.zeros(len(y))
    fold_rows = []
    for k, (tr, va) in enumerate(splits, 1):
        print(f"=== {name} fold {k}/{len(splits)} ===", flush=True)
        # Group-held calibration subset determines only the residual shrinkage.
        gss = GroupShuffleSplit(n_splits=1, test_size=.16, random_state=SEED + k)
        mtr_rel, cal_rel = next(gss.split(np.zeros(len(tr)), y[tr], groups[tr]))
        mtr, cal = tr[mtr_rel], tr[cal_rel]

        inner_p, prior_weight = inner_oof_base(numeric[mtr], objectives[mtr], y[mtr], groups[mtr])
        residual_target = smooth_logit_target(y[mtr], inner_p)
        model = train_residual(args.model, tokenizer, [texts[i] for i in mtr], residual_target,
                               args.max_len, args.epochs, args.lr, args.batch, args.grad_accum)

        p_cal = full_base_predict(numeric[mtr], objectives[mtr], y[mtr], numeric[cal], objectives[cal], prior_weight)
        d_cal = predict_residual(model, tokenizer, [texts[i] for i in cal], args.max_len, args.eval_batch)
        lam, cal_ll = choose_lambda(y[cal], p_cal, d_cal)

        p_base = full_base_predict(numeric[tr], objectives[tr], y[tr], numeric[va], objectives[va], prior_weight)
        d = predict_residual(model, tokenizer, [texts[i] for i in va], args.max_len, args.eval_batch)
        d_rev = predict_residual(model, tokenizer, [reversed_texts[i] for i in va], args.max_len, args.eval_batch)
        d_wrong = predict_residual(model, tokenizer, [wrong_texts[i] for i in va], args.max_len, args.eval_batch)
        corr = lambda z: expit(safe_logit(p_base) + lam * np.clip(4.0 * z, -4.0, 4.0))
        p = corr(d); pr = corr(d_rev); pw = corr(d_wrong)
        p0[va], p1[va], prev[va], pwrong[va] = p_base, p, pr, pw
        row = {
            "fold": k, "rows": int(len(va)), "prior_weight": prior_weight, "lambda": lam,
            "calibration_logloss": cal_ll,
            "base": float(log_loss(y[va], p_base)), "residual": float(log_loss(y[va], p)),
            "chronology_reversed": float(log_loss(y[va], pr)), "objective_shuffled": float(log_loss(y[va], pw)),
        }
        fold_rows.append(row); print(json.dumps(row), flush=True)
        del model
        gc.collect(); torch.cuda.empty_cache()

    def metrics(p):
        return {"logloss": float(log_loss(y, p)), "auc": float(roc_auc_score(y, p))}
    b, r, rev, wrong = metrics(p0), metrics(p1), metrics(prev), metrics(pwrong)
    improvement = b["logloss"] - r["logloss"]
    return {
        "base": b, "residual": r, "chronology_reversed": rev, "objective_shuffled": wrong,
        "improvement": improvement,
        "chronology_separator": rev["logloss"] - r["logloss"],
        "objective_separator": wrong["logloss"] - r["logloss"],
        "fold_wins": int(sum(x["residual"] < x["base"] for x in fold_rows)),
        "folds": fold_rows,
    }


def main(args):
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
    if not torch.cuda.is_available():
        raise RuntimeError("V158 requires CUDA GPU")
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    frame = load_training(args.features.resolve(), args.labels.resolve())
    if args.limit and args.limit < len(frame):
        frame = frame.sample(n=args.limit, random_state=SEED).reset_index(drop=True)
    else:
        frame = frame.reset_index(drop=True)
    transcripts = resolve_transcripts(args.transcripts.resolve(), work)
    texts, rev_texts, wrong_texts, numeric, objectives = compile_rows(frame, transcripts, args.char_cap)
    print({"rows": len(frame), "sessions": frame.session_id.nunique(), "objectives": frame.learning_objective.nunique(),
           "model": args.model, "max_len": args.max_len}, flush=True)

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    session = eval_regime("session", frame, texts, rev_texts, wrong_texts, numeric, objectives,
                          frame.session_id.astype(str).to_numpy(), args, tok)
    objective = eval_regime("objective", frame, texts, rev_texts, wrong_texts, numeric, objectives,
                            frame.learning_objective.astype(str).to_numpy(), args, tok)

    gate = (
        session["improvement"] >= .005 and objective["improvement"] >= .005 and
        session["fold_wins"] >= args.folds - 1 and objective["fold_wins"] >= args.folds - 1 and
        session["chronology_separator"] >= .001 and session["objective_separator"] >= .001 and
        objective["chronology_separator"] >= .001 and objective["objective_separator"] >= .001
    )
    near = session["improvement"] >= .003 and objective["improvement"] >= .003
    decision = "PHASE_CHANGE_CONFIRMED" if gate else "PROMISING_BUT_BELOW_MAX_GAIN_GATE" if near else "NO_MAX_GAIN_TRANSCRIPT_SIGNAL"
    out = {
        "protocol": "V158_LONG_CONTEXT_TARGET_CONDITIONED_RAW_TRANSCRIPT_RESIDUAL",
        "warning": "OOF_SCIENTIFIC_GATE_NOT_A_SUBMISSION",
        "rows": len(frame), "seed": SEED, "model": args.model, "max_len": args.max_len,
        "residual_target": "cross-fitted strong base + alpha-2 objective prior; token model learns only logit residual",
        "controls": "same trained model; within-transcript chronology reversed and target objective shuffled",
        "session": session, "objective_cold": objective, "decision": decision,
        "promotion_rule": ">=0.005 logloss improvement in both regimes, >=folds-1 wins, and both control separators >=0.001",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--transcripts", type=Path, required=True)
    p.add_argument("--work", type=Path, default=Path("/root/trace-ace-results/v158-work"))
    p.add_argument("--out", type=Path, default=Path("v158_results.json"))
    p.add_argument("--model", default=MODEL_DEFAULT)
    p.add_argument("--limit", type=int, default=8000)
    p.add_argument("--folds", type=int, default=3)
    p.add_argument("--max-len", type=int, default=8192)
    p.add_argument("--char-cap", type=int, default=30000)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--eval-batch", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=8)
    main(p.parse_args())
