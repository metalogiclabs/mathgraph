#!/usr/bin/env python3
"""Trace the Ace V71: objective-conditioned mastery events.

This development experiment converts each tutoring transcript into a sequence of
question -> student response -> tutor feedback episodes, scores objective
relevance, estimates independence/hint/correction state, and evaluates whether
those mastery-state features add signal beyond a sparse lexical baseline.

The script intentionally inspects CSV headers before making schema decisions.
It never uses information across test samples at inference time.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

SEED = 20260815
TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
MATH_RE = re.compile(r"(?:\d|[+\-*/=×÷<>]|\b(?:half|quarter|third|tenths?|hundredths?|thousandths?)\b)", re.I)
QUESTION_RE = re.compile(r"\?|\b(?:what|which|how|why|can you|could you|tell me|work out|calculate|solve|find)\b", re.I)
POS_RE = re.compile(r"\b(?:yes|yeah|correct|right|exactly|perfect|good|great|well done|that's it|thats it|you got it|spot on)\b", re.I)
NEG_RE = re.compile(r"\b(?:no|not quite|incorrect|wrong|careful|try again|almost|remember|instead|actually)\b", re.I)
HINT_RE = re.compile(r"\b(?:hint|remember|think about|what if|try|look at|start with|first step|help you)\b", re.I)
AGREE_RE = re.compile(r"^(?:yeah|yes|yep|okay|ok|mm+|mhm|uh huh|right|sure)[.! ]*$", re.I)

STOP = {
    "the","a","an","and","or","to","of","in","on","for","with","is","are","be","as","by","from",
    "this","that","these","those","you","your","we","it","its","into","using","use","up","than","then"
}


def tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(str(text).lower()) if len(t) > 1 and t not in STOP}


def is_substantive_answer(answer: str) -> bool:
    """Keep concise mathematical answers while rejecting acknowledgement-only turns."""
    a = str(answer).strip()
    if not a or AGREE_RE.match(a):
        return False
    if MATH_RE.search(a):
        return True
    return len(tokens(a)) >= 2


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def char_ngram_overlap(a: str, b: str, n: int = 4) -> float:
    def grams(s: str) -> set[str]:
        s = re.sub(r"\s+", " ", s.lower()).strip()
        return {s[i:i+n] for i in range(max(0, len(s)-n+1))}
    ga, gb = grams(a), grams(b)
    return jaccard(ga, gb)


def inspect_headers(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


@dataclass
class Episode:
    q_idx: int
    a_idx: int
    f_idx: int | None
    question: str
    answer: str
    feedback: str
    relevance: float
    feedback_pos: float
    feedback_neg: float
    hinted: float
    answer_substantive: float
    answer_agreement: float
    recency: float


def normalize_roles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    roles = out["role"].astype(str).str.lower().tolist()
    text = out["content"].fillna("").astype(str).tolist()
    repaired = roles[:]
    for i in range(len(out)-1):
        a, b = text[i].strip(), text[i+1].strip()
        if roles[i] == "student" and roles[i+1] == "tutor":
            a_question = bool(QUESTION_RE.search(a)) and len(a.split()) >= 3
            b_short_answer = len(b.split()) <= 6 and not QUESTION_RE.search(b)
            if a_question and b_short_answer:
                repaired[i], repaired[i+1] = "tutor", "student"
    out["role_repaired"] = repaired
    out["role_changed"] = np.asarray(repaired) != np.asarray(roles)
    return out


def extract_episodes(df: pd.DataFrame, objective: str) -> list[Episode]:
    df = normalize_roles(df).reset_index(drop=True)
    roles = df["role_repaired"].tolist()
    content = df["content"].fillna("").astype(str).tolist()
    objective_tokens = tokens(objective)
    episodes: list[Episode] = []
    n = max(1, len(df)-1)

    for q_idx in range(len(df)-1):
        if roles[q_idx] != "tutor" or not QUESTION_RE.search(content[q_idx]):
            continue
        a_idx = None
        for j in range(q_idx+1, min(len(df), q_idx+5)):
            if roles[j] == "student" and content[j].strip():
                a_idx = j
                break
            if roles[j] == "tutor" and QUESTION_RE.search(content[j]) and j > q_idx+1:
                break
        if a_idx is None:
            continue

        f_idx = None
        for j in range(a_idx+1, min(len(df), a_idx+5)):
            if roles[j] == "tutor":
                f_idx = j
                break
        q, a = content[q_idx], content[a_idx]
        f = content[f_idx] if f_idx is not None else ""
        local_text = q + " " + a + " " + f
        rel = max(jaccard(tokens(local_text), objective_tokens), 0.5 * char_ngram_overlap(local_text, objective))
        pos = 1.0 if POS_RE.search(f) else 0.0
        neg = 1.0 if NEG_RE.search(f) else 0.0
        hint = 1.0 if HINT_RE.search(q) else 0.0
        agreement = 1.0 if AGREE_RE.match(a.strip()) else 0.0
        substantive = float(is_substantive_answer(a))
        recency = a_idx / n
        episodes.append(Episode(q_idx,a_idx,f_idx,q,a,f,rel,pos,neg,hint,substantive,agreement,recency))
    return episodes


def mastery_features(df: pd.DataFrame, objective: str) -> tuple[np.ndarray, str, dict]:
    eps = extract_episodes(df, objective)
    changed = float(normalize_roles(df)["role_changed"].mean()) if len(df) else 0.0
    if not eps:
        return np.zeros(24, dtype=np.float64), "", {"episodes":0,"role_repair_rate":changed}
    rel = np.array([e.relevance for e in eps])
    weights = np.maximum(rel, 0.02) * np.exp(2.0 * (np.array([e.recency for e in eps]) - 1.0))
    pos = np.array([e.feedback_pos for e in eps]); neg = np.array([e.feedback_neg for e in eps])
    hint = np.array([e.hinted for e in eps]); sub = np.array([e.answer_substantive for e in eps])
    agr = np.array([e.answer_agreement for e in eps]); rec = np.array([e.recency for e in eps])
    independent_positive = pos * sub * (1.0-hint); corrected = neg * sub
    k = max(1, min(8, len(eps))); top = np.argsort(rel)[-k:]; tail = np.argsort(rec)[-k:]
    wsum = float(weights.sum()) + 1e-12
    feats = np.array([
        len(eps), rel.mean(), rel.max(), np.quantile(rel,0.75), pos.mean(), neg.mean(), hint.mean(), sub.mean(), agr.mean(),
        independent_positive.mean(), corrected.mean(), float((weights*pos).sum()/wsum), float((weights*neg).sum()/wsum),
        float((weights*independent_positive).sum()/wsum), float(pos[top].mean()), float(neg[top].mean()),
        float(independent_positive[top].mean()), float(pos[tail].mean()), float(neg[tail].mean()),
        float(independent_positive[tail].mean()), float(rec[pos>0].mean()) if np.any(pos>0) else 0.0,
        float(rec[neg>0].mean()) if np.any(neg>0) else 0.0, changed, float(sum(e.feedback_pos-e.feedback_neg for e in eps[-5:])),
    ], dtype=np.float64)
    ranked = sorted(eps, key=lambda e: (e.relevance * (0.25 + 0.75*e.recency)), reverse=True)[:8]
    text = " ".join(f"[Q]{e.question} [STUDENT]{e.answer} [FEEDBACK]{e.feedback}" for e in ranked)
    meta = {"episodes":len(eps),"role_repair_rate":changed,"max_relevance":float(rel.max())}
    return feats, text, meta


def load_transcript(path: Path) -> pd.DataFrame:
    cols = inspect_headers(path)
    required = {"session_id","utterance_id","role","content","timestamp"}
    missing = required - set(cols)
    if missing: raise ValueError(f"{path.name}: missing transcript columns {sorted(missing)}; got {cols}")
    return pd.read_csv(path)


def build_frame(features_path: Path, labels_path: Path, transcript_dir: Path):
    fcols = inspect_headers(features_path); lcols = inspect_headers(labels_path)
    print("features columns", fcols); print("labels columns", lcols)
    required_f = {"response_id","session_id","learning_objective"}
    if not required_f.issubset(fcols): raise ValueError(f"features missing {sorted(required_f-set(fcols))}")
    target = "is_correct" if "is_correct" in lcols else "correct" if "correct" in lcols else None
    if target is None: raise ValueError(f"labels need is_correct or correct; got {lcols}")
    features = pd.read_csv(features_path); labels = pd.read_csv(labels_path)
    return features.merge(labels[["response_id",target]], on="response_id", how="inner", validate="one_to_one").rename(columns={target:"target"})


def fixed_group_folds(groups: Iterable[str], n_splits: int = 5):
    groups = np.asarray(list(groups)); dummy = np.zeros(len(groups))
    return list(GroupKFold(n_splits=n_splits).split(dummy, dummy, groups))


def fit_eval(X, y, folds, name: str):
    oof = np.zeros(len(y), dtype=np.float64); rows = []
    for fold,(tr,va) in enumerate(folds,1):
        m = LogisticRegression(C=0.35, max_iter=250, solver="liblinear", random_state=SEED)
        m.fit(X[tr], y[tr]); p = np.clip(m.predict_proba(X[va])[:,1], 1e-5, 1-1e-5); oof[va] = p
        rows.append({"fold":fold,"rows":len(va),"logloss":log_loss(y[va],p),"auc":roc_auc_score(y[va],p)}); print(name, rows[-1])
    return oof, rows


def run(args):
    frame = build_frame(args.features, args.labels, args.transcripts)
    cache: dict[str,pd.DataFrame] = {}; numeric, episode_text, meta = [], [], []
    for i,row in frame.iterrows():
        sid = str(row.session_id)
        if sid not in cache: cache[sid] = load_transcript(args.transcripts / f"{sid}.csv")
        f,t,m = mastery_features(cache[sid], str(row.learning_objective)); numeric.append(f); episode_text.append(t); meta.append(m)
        if args.limit and i+1 >= args.limit: frame = frame.iloc[:i+1].copy(); break
    numeric = np.vstack(numeric); episode_text = episode_text[:len(frame)]; y = frame.target.to_numpy(dtype=int)
    hv = HashingVectorizer(n_features=2**18, alternate_sign=False, norm="l2", ngram_range=(1,2), lowercase=True)
    objective_text = frame.learning_objective.fillna("").astype(str).tolist()
    X_obj = hv.transform(["[OBJECTIVE] "+x for x in objective_text]); X_ep = hv.transform(["[EPISODES] "+x for x in episode_text])
    X_num = csr_matrix((numeric - numeric.mean(0)) / (numeric.std(0)+1e-6)); X_base = X_obj; X_full = hstack([X_obj,X_ep,X_num], format="csr")
    session_folds = fixed_group_folds(frame.session_id, 5)
    objective_folds = fixed_group_folds(frame.learning_objective_id if "learning_objective_id" in frame else frame.learning_objective, 5)
    results = {}
    for split,folds in [("session",session_folds),("objective",objective_folds)]:
        p0,r0 = fit_eval(X_base,y,folds,f"baseline/{split}"); p1,r1 = fit_eval(X_full,y,folds,f"mastery/{split}")
        results[split] = {"baseline_logloss":float(log_loss(y,p0)),"mastery_logloss":float(log_loss(y,p1)),"delta":float(log_loss(y,p1)-log_loss(y,p0)),"baseline_auc":float(roc_auc_score(y,p0)),"mastery_auc":float(roc_auc_score(y,p1)),"folds_baseline":r0,"folds_mastery":r1}
    results["diagnostics"] = {"rows":len(frame),"sessions":int(frame.session_id.nunique()),"objectives":int(frame.learning_objective.nunique()),"mean_episode_count":float(np.mean([m["episodes"] for m in meta[:len(frame)]])),"mean_role_repair_rate":float(np.mean([m["role_repair_rate"] for m in meta[:len(frame)]]))}
    print(json.dumps(results, indent=2)); args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(results, indent=2))


def self_test():
    for x in ["42", "0.5", "3/4", "x = 6"]: assert is_substantive_answer(x), x
    for x in ["yeah", "ok", "mhm"]: assert not is_substantive_answer(x), x
    df = pd.DataFrame([["s","1","tutor","What is 6 times 7?","2026-01-01T00:00:00"],["s","2","student","42","2026-01-01T00:00:01"],["s","3","tutor","Exactly right, well done.","2026-01-01T00:00:02"],["s","4","tutor","Now what is 8 times 7?","2026-01-01T00:00:03"],["s","5","student","54","2026-01-01T00:00:04"],["s","6","tutor","Not quite, try again.","2026-01-01T00:00:05"]], columns=["session_id","utterance_id","role","content","timestamp"])
    f,t,m = mastery_features(df,"multiplying one-digit numbers"); assert m["episodes"] == 2; assert f[7] == 1.0; assert f[4] > 0 and f[5] > 0; assert "42" in t and "54" in t
    print("SELF_TEST_PASS", json.dumps(m))


def parse_args():
    p = argparse.ArgumentParser(); p.add_argument("--features", type=Path); p.add_argument("--labels", type=Path); p.add_argument("--transcripts", type=Path); p.add_argument("--out", type=Path, default=Path("v71_mastery_results.json")); p.add_argument("--limit", type=int, default=0); p.add_argument("--self-test", action="store_true"); return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.self_test: self_test()
    else:
        if not (a.features and a.labels and a.transcripts): raise SystemExit("--features, --labels and --transcripts are required unless --self-test is used")
        run(a)
