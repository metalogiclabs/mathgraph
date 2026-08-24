#!/usr/bin/env python3
"""Trace the Ace V75: canonical student-state trajectories.

Goal: improve genuinely unseen log loss by removing nuisance variation while
preserving educational variation. This module converts raw tutoring dialogue into
multiple deterministic views plus a compact chronological event sequence. It
never deletes the raw view and never uses labels to construct features.

The script inspects CSV headers before schema decisions and processes each
(session, objective) independently at inference time.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

from v71_mastery_events import (
    AGREE_RE,
    HINT_RE,
    NEG_RE,
    POS_RE,
    QUESTION_RE,
    char_ngram_overlap,
    inspect_headers,
    jaccard,
    load_transcript,
    normalize_roles,
    tokens,
)

SEED = 20260815
LOW_INFO_RE = re.compile(
    r"^(?:hi|hello|hey|bye|goodbye|thanks|thank you|yeah|yes|yep|okay|ok|mm+|mhm|uh huh|right|sure|cool|great)[.! ]*$",
    re.I,
)
SELF_CORRECT_RE = re.compile(r"\b(?:wait|sorry|actually|i mean|no,? it(?:'s| is)|let me change|correction)\b", re.I)
EXPLAIN_RE = re.compile(r"\b(?:because|so that|therefore|since|i know|the reason|which means)\b", re.I)
TRANSFER_RE = re.compile(r"\b(?:another|next one|different|now try|what about|similar|new example)\b", re.I)
ADMIN_RE = re.compile(
    r"\b(?:can you hear me|internet|connection|camera|microphone|lesson today|how are you|good morning|good afternoon|see you|homework portal)\b",
    re.I,
)
MATH_ANSWER_RE = re.compile(
    r"(?:\d|[=+\-/*×÷%]|\b(?:half|quarter|third|tenths?|hundredths?|thousandths?)\b)",
    re.I,
)

MATH_REPLACEMENTS = (
    (re.compile(r"[−–—]"), "-"),
    (re.compile(r"[×✕]"), " x "),
    (re.compile(r"[÷]"), " / "),
    (re.compile(r"\s+"), " "),
)

STATE_ORDER = {
    "UNRESOLVED_ERROR": -2.0,
    "CORRECTED_BY_TUTOR": -1.0,
    "AGREEMENT_ONLY": -0.25,
    "NO_JUDGMENT": 0.0,
    "CORRECT_AFTER_HINT": 0.75,
    "SELF_CORRECT": 1.0,
    "INDEPENDENT_CORRECT": 1.5,
    "TRANSFER_SUCCESS": 2.0,
}


@dataclass
class CanonicalEvent:
    state: str
    relevance: float
    recency: float
    assistance: float
    substantive: float
    low_info: float
    explanation: float
    question: str
    answer: str
    feedback: str


def normalize_math(text: str) -> str:
    s = str(text).strip()
    for pattern, repl in MATH_REPLACEMENTS:
        s = pattern.sub(repl, s)
    # Standardize a few harmless surface variants while retaining original text in
    # separate views. Avoid semantic rewriting of spoken numbers/fractions.
    s = re.sub(r"(?<=\d)\s*%", "%", s)
    s = re.sub(r"\s*([=+\-/*])\s*", r" \1 ", s)
    return re.sub(r"\s+", " ", s).strip()


def low_information(text: str) -> bool:
    s = str(text).strip()
    return bool(LOW_INFO_RE.match(s) or ADMIN_RE.search(s))


def substantive_answer(text: str) -> bool:
    """Recognize real student work without penalizing short mathematical answers.

    A one-token response such as `42`, `0.5`, `3/4`, or `x=6` is high-value
    evidence even though it has fewer lexical tokens than a verbal explanation.
    Pure acknowledgements remain non-substantive.
    """
    s = str(text).strip()
    if not s or AGREE_RE.match(s):
        return False
    if MATH_ANSWER_RE.search(s):
        return True
    return len(tokens(s)) >= 2


def role_repair_with_confidence(df: pd.DataFrame) -> pd.DataFrame:
    """Retain original/repaired roles and attach conservative repair confidence."""
    repaired = normalize_roles(df)
    conf = np.zeros(len(repaired), dtype=float)
    changed = repaired["role_changed"].to_numpy(dtype=bool)
    conf[changed] = 0.9
    # Short acknowledgements in suspiciously inverted local pairs are less certain.
    for i in np.flatnonzero(changed):
        txt = str(repaired.iloc[i]["content"]).strip()
        if len(txt.split()) <= 2:
            conf[i] = 0.75
    repaired["role_repair_confidence"] = conf
    return repaired


def objective_relevance(question: str, answer: str, feedback: str, objective: str) -> float:
    local = f"{question} {answer} {feedback}"
    obj_tok = tokens(objective)
    return float(max(jaccard(tokens(local), obj_tok), 0.5 * char_ngram_overlap(local, objective)))


def classify_state(question: str, answer: str, feedback: str) -> tuple[str, float]:
    """Return canonical state and assistance level in [0, 1]."""
    q, a, f = map(str, (question, answer, feedback))
    pos = bool(POS_RE.search(f))
    neg = bool(NEG_RE.search(f))
    hinted = bool(HINT_RE.search(q))
    agreement = bool(AGREE_RE.match(a.strip()))
    substantive = substantive_answer(a)
    self_correct = bool(SELF_CORRECT_RE.search(a))
    transfer = bool(TRANSFER_RE.search(q))

    if neg and substantive:
        return "UNRESOLVED_ERROR", 0.0
    if agreement and pos:
        return "AGREEMENT_ONLY", 1.0
    if self_correct and pos and substantive:
        return "SELF_CORRECT", 0.25
    if pos and substantive and hinted:
        return "CORRECT_AFTER_HINT", 0.65
    if pos and substantive and transfer:
        return "TRANSFER_SUCCESS", 0.0
    if pos and substantive:
        return "INDEPENDENT_CORRECT", 0.0
    if neg or (hinted and agreement):
        return "CORRECTED_BY_TUTOR", 1.0
    return "NO_JUDGMENT", float(hinted)


def extract_canonical_events(df: pd.DataFrame, objective: str) -> list[CanonicalEvent]:
    d = role_repair_with_confidence(df).reset_index(drop=True)
    roles = d["role_repaired"].astype(str).str.lower().tolist()
    content = d["content"].fillna("").astype(str).tolist()
    n = max(1, len(d) - 1)
    out: list[CanonicalEvent] = []

    for qi in range(len(d) - 1):
        if roles[qi] != "tutor" or not QUESTION_RE.search(content[qi]):
            continue
        ai = None
        for j in range(qi + 1, min(len(d), qi + 6)):
            if roles[j] == "student" and content[j].strip():
                ai = j
                break
            if roles[j] == "tutor" and QUESTION_RE.search(content[j]) and j > qi + 1:
                break
        if ai is None:
            continue
        fi = None
        for j in range(ai + 1, min(len(d), ai + 6)):
            if roles[j] == "tutor":
                fi = j
                break
        q = content[qi]
        a = content[ai]
        f = content[fi] if fi is not None else ""
        state, assistance = classify_state(q, a, f)
        rel = objective_relevance(q, a, f, objective)
        substantive = float(substantive_answer(a))
        out.append(
            CanonicalEvent(
                state=state,
                relevance=rel,
                recency=ai / n,
                assistance=assistance,
                substantive=substantive,
                low_info=float(low_information(a)),
                explanation=float(bool(EXPLAIN_RE.search(a))),
                question=normalize_math(q),
                answer=normalize_math(a),
                feedback=normalize_math(f),
            )
        )
    return out


def trajectory_views(df: pd.DataFrame, objective: str) -> tuple[dict[str, str], np.ndarray, dict]:
    d = role_repair_with_confidence(df).reset_index(drop=True)
    events = extract_canonical_events(d, objective)

    raw = " ".join(
        f"[{str(r.role).upper()}] {str(r.content)}"
        for r in d[["role", "content"]].itertuples(index=False)
    )
    student_only = " ".join(
        normalize_math(str(r.content))
        for r in d[["role_repaired", "content"]].itertuples(index=False)
        if str(r.role_repaired).lower() == "student" and not low_information(str(r.content))
    )

    ranked = sorted(events, key=lambda e: e.relevance * (0.2 + 0.8 * e.recency), reverse=True)
    local = " ".join(
        f"[Q] {e.question} [S] {e.answer} [F] {e.feedback}"
        for e in ranked[:12]
    )
    canonical = " ".join(
        f"[{e.state}] rel={e.relevance:.3f} rec={e.recency:.3f} assist={e.assistance:.2f}"
        for e in events
    )
    terminal_events = sorted(events, key=lambda e: (e.relevance * (0.25 + 0.75 * e.recency)), reverse=True)[:6]
    terminal = " ".join(
        f"[{e.state}] [S] {e.answer} [F] {e.feedback}"
        for e in terminal_events
    )

    if events:
        rel = np.array([e.relevance for e in events], dtype=float)
        rec = np.array([e.recency for e in events], dtype=float)
        assist = np.array([e.assistance for e in events], dtype=float)
        subst = np.array([e.substantive for e in events], dtype=float)
        low = np.array([e.low_info for e in events], dtype=float)
        expl = np.array([e.explanation for e in events], dtype=float)
        state_score = np.array([STATE_ORDER[e.state] for e in events], dtype=float)
        w = np.maximum(rel, 0.02) * np.exp(2.5 * (rec - 1.0))
        w /= w.sum() + 1e-12
        top = np.argsort(rel * (0.25 + 0.75 * rec))[-min(6, len(events)):]
        tail = np.argsort(rec)[-min(6, len(events)):]
        positive = np.isin([e.state for e in events], ["INDEPENDENT_CORRECT", "SELF_CORRECT", "TRANSFER_SUCCESS", "CORRECT_AFTER_HINT"]).astype(float)
        errors = np.isin([e.state for e in events], ["UNRESOLVED_ERROR", "CORRECTED_BY_TUTOR"]).astype(float)
        independent = np.isin([e.state for e in events], ["INDEPENDENT_CORRECT", "SELF_CORRECT", "TRANSFER_SUCCESS"]).astype(float)
        feats = np.array([
            len(events), rel.mean(), rel.max(), np.quantile(rel, 0.75),
            rec.mean(), assist.mean(), subst.mean(), low.mean(), expl.mean(),
            positive.mean(), errors.mean(), independent.mean(),
            float((w * state_score).sum()), float((w * positive).sum()), float((w * errors).sum()),
            float((w * independent).sum()), float(state_score[top].mean()), float(state_score[tail].mean()),
            float(positive[top].mean()), float(errors[top].mean()), float(independent[top].mean()),
            float(positive[tail].mean()), float(errors[tail].mean()), float(independent[tail].mean()),
            float(np.max(rec[independent > 0])) if np.any(independent > 0) else 0.0,
            float(np.max(rec[errors > 0])) if np.any(errors > 0) else 0.0,
            float(np.sum(independent * (rel >= np.quantile(rel, 0.75)))),
            float(np.sum(errors * (rel >= np.quantile(rel, 0.75)))),
        ], dtype=float)
    else:
        feats = np.zeros(28, dtype=float)

    views = {
        "raw": raw,
        "student": student_only,
        "local": local,
        "canonical": canonical,
        "terminal": terminal,
    }
    meta = {
        "events": len(events),
        "role_repair_rate": float(d["role_changed"].mean()) if len(d) else 0.0,
        "student_chars": len(student_only),
        "raw_chars": len(raw),
    }
    return views, feats, meta


def load_training(features: Path, labels: Path) -> pd.DataFrame:
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


def folds_for(groups: pd.Series, n_splits: int = 5):
    g = groups.astype(str).to_numpy()
    dummy = np.zeros(len(g))
    return list(GroupKFold(n_splits=n_splits).split(dummy, dummy, g))


def oof_eval(X, y, folds, name: str):
    pred = np.zeros(len(y), dtype=float)
    per_fold = []
    for k, (tr, va) in enumerate(folds, 1):
        model = LogisticRegression(C=0.25, max_iter=300, solver="liblinear", random_state=SEED)
        model.fit(X[tr], y[tr])
        p = np.clip(model.predict_proba(X[va])[:, 1], 1e-5, 1 - 1e-5)
        pred[va] = p
        row = {"fold": k, "rows": len(va), "logloss": float(log_loss(y[va], p)), "auc": float(roc_auc_score(y[va], p))}
        print(name, row)
        per_fold.append(row)
    return pred, per_fold


def run(args) -> None:
    frame = load_training(args.features, args.labels)
    if args.limit:
        frame = frame.iloc[: args.limit].copy()

    cache: dict[str, pd.DataFrame] = {}
    view_rows: list[dict[str, str]] = []
    nums, metas = [], []
    for i, row in frame.iterrows():
        sid = str(row.session_id)
        if sid not in cache:
            cache[sid] = load_transcript(args.transcripts / f"{sid}.csv")
        v, n, m = trajectory_views(cache[sid], str(row.learning_objective))
        view_rows.append(v); nums.append(n); metas.append(m)
        if (len(view_rows) % 2500) == 0:
            print("canonicalized rows", len(view_rows))

    numeric = np.vstack(nums)
    y = frame.target.to_numpy(dtype=int)
    hv = HashingVectorizer(n_features=2**18, alternate_sign=False, norm="l2", ngram_range=(1, 2), lowercase=True)
    objective = hv.transform(["[OBJECTIVE] " + str(x) for x in frame.learning_objective])
    raw = hv.transform(["[RAW] " + v["raw"] for v in view_rows])
    student = hv.transform(["[STUDENT] " + v["student"] for v in view_rows])
    local = hv.transform(["[LOCAL] " + v["local"] for v in view_rows])
    canonical = hv.transform(["[STATE] " + v["canonical"] for v in view_rows])
    terminal = hv.transform(["[TERMINAL] " + v["terminal"] for v in view_rows])
    z = (numeric - numeric.mean(0)) / (numeric.std(0) + 1e-6)
    num = csr_matrix(z)

    matrices = {
        "objective_only": objective,
        "raw": hstack([objective, raw], format="csr"),
        "student": hstack([objective, student], format="csr"),
        "local": hstack([objective, local, num], format="csr"),
        "canonical": hstack([objective, canonical, terminal, num], format="csr"),
        "all_views": hstack([objective, raw, student, local, canonical, terminal, num], format="csr"),
    }
    session_folds = folds_for(frame.session_id)
    objective_groups = frame.learning_objective_id if "learning_objective_id" in frame.columns else frame.learning_objective
    objective_folds = folds_for(objective_groups)

    results = {"diagnostics": {
        "rows": int(len(frame)),
        "sessions": int(frame.session_id.nunique()),
        "objectives": int(frame.learning_objective.nunique()),
        "mean_events": float(np.mean([m["events"] for m in metas])),
        "mean_role_repair_rate": float(np.mean([m["role_repair_rate"] for m in metas])),
        "mean_student_to_raw_char_ratio": float(np.mean([m["student_chars"] / max(1, m["raw_chars"]) for m in metas])),
    }}
    for split, folds in (("session", session_folds), ("objective", objective_folds)):
        results[split] = {}
        for name, X in matrices.items():
            p, pf = oof_eval(X, y, folds, f"{split}/{name}")
            results[split][name] = {
                "logloss": float(log_loss(y, p)),
                "auc": float(roc_auc_score(y, p)),
                "worst_fold_logloss": float(max(r["logloss"] for r in pf)),
                "folds": pf,
            }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


def self_test() -> None:
    # Includes an obvious role inversion, a hinted success, an error, and a later
    # independent transfer success. Raw view must remain available.
    df = pd.DataFrame([
        ["s", "1", "student", "Hi, can you hear me?", "2026-01-01T00:00:00"],
        ["s", "2", "tutor", "Yeah.", "2026-01-01T00:00:01"],
        ["s", "3", "tutor", "Remember the 7 times table. What is 6 times 7?", "2026-01-01T00:00:02"],
        ["s", "4", "student", "42", "2026-01-01T00:00:03"],
        ["s", "5", "tutor", "Exactly right.", "2026-01-01T00:00:04"],
        ["s", "6", "tutor", "What is 8 times 7?", "2026-01-01T00:00:05"],
        ["s", "7", "student", "54", "2026-01-01T00:00:06"],
        ["s", "8", "tutor", "Not quite, try again.", "2026-01-01T00:00:07"],
        ["s", "9", "tutor", "Another one: what is 9 times 7?", "2026-01-01T00:00:08"],
        ["s", "10", "student", "63 because nine sevens are sixty three", "2026-01-01T00:00:09"],
        ["s", "11", "tutor", "Perfect, that's right.", "2026-01-01T00:00:10"],
    ], columns=["session_id", "utterance_id", "role", "content", "timestamp"])
    views, feats, meta = trajectory_views(df, "multiplying one-digit numbers using the 7 times table")
    ev = extract_canonical_events(df, "multiplying one-digit numbers using the 7 times table")
    states = [e.state for e in ev]
    assert substantive_answer("42")
    assert substantive_answer("0.5")
    assert substantive_answer("3/4")
    assert not substantive_answer("yeah")
    assert "CORRECT_AFTER_HINT" in states
    assert "UNRESOLVED_ERROR" in states
    assert "TRANSFER_SUCCESS" in states
    assert "Hi, can you hear me?" in views["raw"]
    assert "Hi, can you hear me?" not in views["student"]
    assert feats.shape == (28,)
    assert meta["role_repair_rate"] > 0
    print("V75_SELF_TEST_PASS", json.dumps({"states": states, **meta}))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path)
    p.add_argument("--labels", type=Path)
    p.add_argument("--transcripts", type=Path)
    p.add_argument("--out", type=Path, default=Path("v75_canonical_trajectory.json"))
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
    else:
        if not args.features or not args.labels or not args.transcripts:
            raise SystemExit("--features, --labels and --transcripts are required")
        run(args)
