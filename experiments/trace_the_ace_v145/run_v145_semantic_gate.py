#!/usr/bin/env python3
"""Trace the Ace V145: target-conditioned semantic epistemic gate.

This is deliberately an experiment, not a leaderboard submission.  A frozen
instruction model converts objective-specific dialogue evidence into seven
continuous epistemic attributes.  Those attributes are allowed into a model
only if they improve both session-cold and objective-cold out-of-fold log loss,
survive a grouped bootstrap, and fail when row alignment is shuffled.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if not (HERE / "v71_mastery_events.py").exists() and (HERE.parent / "v135").exists():
    sys.path.insert(0, str(HERE.parent / "v135"))
from v71_mastery_events import load_transcript
from v75_canonical_trajectory import SEED, load_training, trajectory_views

FIELDS = (
    "mastery", "independence", "guided_success", "unresolved_error",
    "self_correction", "contradiction", "evidence_sufficiency",
)
NUMBER_RE = re.compile(r"(?:^|[;,\s])(?:[a-z_]+\s*=\s*)?(-?(?:\d+(?:\.\d*)?|\.\d+))", re.I)

SYSTEM = """You are an educational evidence judge. Estimate what the STUDENT can do for the exact TARGET OBJECTIVE, not whether the tutor explained it. Treat a correct answer after the answer was supplied or heavily hinted as weak mastery evidence. Later independent transfer is strongest. Unresolved errors and contradictions are negative. Irrelevant dialogue is no evidence. Return exactly seven numbers from 0 to 1, comma-separated, with no words, in this order: mastery, independence, guided_success, unresolved_error, self_correction, contradiction, evidence_sufficiency."""


def prompt_for(objective: str, local_evidence: str) -> str:
    evidence = local_evidence.strip() or "[NO RELEVANT QUESTION-ANSWER-FEEDBACK EVENT FOUND]"
    # Bound tokens and keep both ends: the beginning often states the problem,
    # while the end often contains the most diagnostic independent attempt.
    if len(evidence) > 6500:
        evidence = evidence[:2600] + "\n[...middle omitted...]\n" + evidence[-3900:]
    return f"TARGET OBJECTIVE: {objective}\nEVIDENCE:\n{evidence}\nSEVEN NUMBERS:"


def parse_scores(text: str) -> np.ndarray | None:
    vals = []
    for raw in NUMBER_RE.findall(str(text).lower().replace("\n", " ")):
        try:
            x = float(raw)
        except ValueError:
            continue
        if 0.0 <= x <= 1.0:
            vals.append(x)
    if len(vals) < len(FIELDS):
        return None
    return np.asarray(vals[-len(FIELDS):], dtype=np.float32)


def resolve_transcripts(path: Path, work: Path) -> Path:
    if path.is_dir():
        candidates = [path] + [p for p in path.rglob("*") if p.is_dir()]
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
        candidates = [out] + [p for p in out.rglob("*") if p.is_dir()]
    else:
        raise ValueError(f"transcripts must be a directory or zip: {path}")
    scored = []
    for p in candidates:
        try:
            n = sum(1 for _ in p.glob("*.csv"))
        except OSError:
            n = 0
        if n:
            scored.append((n, p))
    if not scored:
        raise FileNotFoundError("No transcript CSV directory found")
    best = max(scored)[1]
    print(f"Transcript directory: {best}", flush=True)
    return best


def compile_rows(frame: pd.DataFrame, transcripts: Path):
    cache, views, nums, prompts = {}, [], [], []
    for i, r in enumerate(frame.itertuples(index=False), 1):
        sid, objective = str(r.session_id), str(r.learning_objective)
        if sid not in cache:
            cache[sid] = load_transcript(transcripts / f"{sid}.csv")
        v, n, _ = trajectory_views(cache[sid], objective)
        views.append(v); nums.append(n); prompts.append(prompt_for(objective, v["local"]))
        if i % 2500 == 0:
            print(f"Compiled evidence {i}/{len(frame)}", flush=True)
    return views, np.vstack(nums), prompts


def render_chat(tokenizer, user: str) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def infer_semantics(prompts: list[str], model: str, cache_path: Path, batch: int) -> np.ndarray:
    done, raw_rows = [], []
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            row = json.loads(line); parsed = parse_scores(row.get("output", ""))
            if parsed is None:
                break
            done.append(parsed); raw_rows.append(row)
    if len(done) > len(prompts):
        done, raw_rows = [], []
    # Remove a partial/bad tail before resuming, otherwise appending would make
    # the cache permanently ambiguous on the next run.
    if cache_path.exists() and len(raw_rows) != len(cache_path.read_text().splitlines()):
        cache_path.write_text("".join(json.dumps(r) + "\n" for r in raw_rows))
    if len(done) == len(prompts):
        print(f"Reusing {len(done)} cached semantic rows", flush=True)
        return np.vstack(done)

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    llm = LLM(model=model, trust_remote_code=True, dtype="auto", max_model_len=int(os.environ.get("V145_MAX_MODEL_LEN", "4096")),
              gpu_memory_utilization=float(os.environ.get("V145_GPU_MEMORY", ".90")))
    sampling = SamplingParams(temperature=0.0, max_tokens=48, stop=["\n\n"])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    start = len(done)
    for lo in range(start, len(prompts), batch):
        hi = min(len(prompts), lo + batch)
        rendered = [render_chat(tokenizer, p) for p in prompts[lo:hi]]
        outputs = llm.generate(rendered, sampling, use_tqdm=False)
        with cache_path.open("a") as fh:
            for j, out in enumerate(outputs, lo):
                text = out.outputs[0].text.strip()
                parsed = parse_scores(text)
                if parsed is None:
                    # Neutral/uncertain is safer than silently dropping a row.
                    parsed = np.asarray([.5, .5, .5, .5, .5, .5, 0.0], np.float32)
                row = {"row": j, "output": text, **{k: float(v) for k, v in zip(FIELDS, parsed)}}
                fh.write(json.dumps(row) + "\n"); fh.flush()
                done.append(parsed)
        print(f"Semantic inference {hi}/{len(prompts)}", flush=True)
    return np.vstack(done)


def build_v75(frame: pd.DataFrame, views, numeric):
    hv = HashingVectorizer(n_features=2**18, alternate_sign=False, norm="l2", ngram_range=(1, 2), lowercase=True)
    parts = [hv.transform(["[OBJECTIVE] " + str(x) for x in frame.learning_objective])]
    for key in ("raw", "student", "local", "canonical", "terminal"):
        parts.append(hv.transform([f"[{key.upper()}] " + v[key] for v in views]))
    z = (numeric - numeric.mean(0)) / (numeric.std(0) + 1e-6)
    parts.append(csr_matrix(z))
    return hstack(parts, format="csr")


def grouped_bootstrap_improvement(y, p0, p1, groups, reps=2000):
    loss0 = -(y*np.log(p0) + (1-y)*np.log(1-p0))
    loss1 = -(y*np.log(p1) + (1-y)*np.log(1-p1))
    d = loss0 - loss1
    codes, uniq = pd.factorize(pd.Series(groups).astype(str), sort=True)
    sums = np.bincount(codes, weights=d); counts = np.bincount(codes)
    rng = np.random.default_rng(SEED); vals = np.empty(reps)
    for b in range(reps):
        ix = rng.integers(0, len(uniq), len(uniq))
        vals[b] = sums[ix].sum() / counts[ix].sum()
    return [float(x) for x in np.quantile(vals, [.025, .5, .975])]


def evaluate_split(name, X, S, y, groups):
    splits = list(GroupKFold(5).split(np.zeros(len(y)), y, pd.Series(groups).astype(str)))
    p0 = np.zeros(len(y)); p1 = np.zeros(len(y)); ps = np.zeros(len(y)); psh = np.zeros(len(y))
    folds = []
    rng = np.random.default_rng(SEED + (0 if name == "session" else 1))
    shuffled = S[rng.permutation(len(S))]
    for k, (tr, va) in enumerate(splits, 1):
        scaler = StandardScaler().fit(S[tr]); ztr, zva = scaler.transform(S[tr]), scaler.transform(S[va])
        shsc = StandardScaler().fit(shuffled[tr]); shtr, shva = shsc.transform(shuffled[tr]), shsc.transform(shuffled[va])
        base = LogisticRegression(C=.25, max_iter=350, solver="liblinear", random_state=SEED).fit(X[tr], y[tr])
        aug = LogisticRegression(C=.25, max_iter=350, solver="liblinear", random_state=SEED).fit(hstack([X[tr], csr_matrix(ztr)]), y[tr])
        sem = LogisticRegression(C=.10, max_iter=350, solver="liblinear", random_state=SEED).fit(ztr, y[tr])
        shf = LogisticRegression(C=.25, max_iter=350, solver="liblinear", random_state=SEED).fit(hstack([X[tr], csr_matrix(shtr)]), y[tr])
        p0[va] = base.predict_proba(X[va])[:, 1]
        p1[va] = aug.predict_proba(hstack([X[va], csr_matrix(zva)]))[:, 1]
        ps[va] = sem.predict_proba(zva)[:, 1]
        psh[va] = shf.predict_proba(hstack([X[va], csr_matrix(shva)]))[:, 1]
        folds.append({"fold": k, "rows": len(va), "base": float(log_loss(y[va], p0[va])),
                      "semantic_augmented": float(log_loss(y[va], p1[va]))})
    for p in (p0, p1, ps, psh): np.clip(p, 1e-5, 1-1e-5, out=p)
    ll0, ll1, lls, llsh = map(lambda p: float(log_loss(y, p)), (p0, p1, ps, psh))
    return {"base_logloss": ll0, "semantic_augmented_logloss": ll1, "semantic_only_logloss": lls,
            "shuffled_control_logloss": llsh, "improvement": ll0-ll1,
            "shuffled_improvement": ll0-llsh, "base_auc": float(roc_auc_score(y, p0)),
            "semantic_augmented_auc": float(roc_auc_score(y, p1)),
            "bootstrap_improvement_95": grouped_bootstrap_improvement(y, p0, p1, groups),
            "fold_wins": int(sum(r["semantic_augmented"] < r["base"] for r in folds)), "folds": folds}


def semantic_control_eval(S_main, S_control, y, groups):
    """Cross-fitted contrast on identical rows; no transcript baseline involved."""
    splits = list(GroupKFold(5).split(np.zeros(len(y)), y, pd.Series(groups).astype(str)))
    pm = np.zeros(len(y)); pc = np.zeros(len(y))
    for tr, va in splits:
        sm = StandardScaler().fit(S_main[tr]); sc = StandardScaler().fit(S_control[tr])
        zmtr, zmva = sm.transform(S_main[tr]), sm.transform(S_main[va])
        zctr, zcva = sc.transform(S_control[tr]), sc.transform(S_control[va])
        mm = LogisticRegression(C=.10, max_iter=300, solver="liblinear", random_state=SEED).fit(zmtr, y[tr])
        mc = LogisticRegression(C=.10, max_iter=300, solver="liblinear", random_state=SEED).fit(zctr, y[tr])
        pm[va] = mm.predict_proba(zmva)[:, 1]; pc[va] = mc.predict_proba(zcva)[:, 1]
    lm, lc = float(log_loss(y, pm)), float(log_loss(y, pc))
    return {"main_logloss": lm, "control_logloss": lc, "main_advantage": lc-lm}


def choose_subset(frame, limit):
    if not limit or limit >= len(frame): return frame.reset_index(drop=True)
    # Random row selection, followed by group-cold validation; deterministic and
    # less biased than taking the chronologically first N rows.
    return frame.sample(n=limit, random_state=SEED).reset_index(drop=True)


def self_test():
    assert np.allclose(parse_scores("0.7, 0.8, 0.1, 0.0, 0.2, 0, 0.9"), [.7,.8,.1,0,.2,0,.9])
    assert parse_scores("not json") is None
    p = prompt_for("fractions", "x" * 8000)
    assert len(p) < 7000 and "middle omitted" in p
    print("V145_SELF_TEST_PASS")


def main(a):
    if a.self_test: self_test(); return
    work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    transcripts = resolve_transcripts(a.transcripts.resolve(), work)
    frame = choose_subset(load_training(a.features, a.labels), a.limit)
    print({"rows": len(frame), "sessions": frame.session_id.nunique(), "objectives": frame.learning_objective.nunique()})
    views, numeric, prompts = compile_rows(frame, transcripts)
    S = infer_semantics(prompts, a.model, work / "semantic_scores.jsonl", a.batch)
    X = build_v75(frame, views, numeric); y = frame.target.to_numpy(int)
    objective_groups = frame.learning_objective_id if "learning_objective_id" in frame else frame.learning_objective
    # Two model-based counterfactuals on a fixed diagnostic subset: wrong target
    # with real evidence, and correct target with no evidence. This distinguishes
    # genuine target-conditioned reading from generic session/style priors.
    rng = np.random.default_rng(SEED)
    ci = np.sort(rng.choice(len(frame), size=min(a.control_limit, len(frame)), replace=False))
    swapped = rng.permutation(frame.learning_objective.astype(str).to_numpy()[ci])
    swap_prompts = [prompt_for(obj, views[i]["local"]) for i, obj in zip(ci, swapped)]
    empty_prompts = [prompt_for(str(frame.iloc[i].learning_objective), "") for i in ci]
    Sswap = infer_semantics(swap_prompts, a.model, work / "objective_swap_scores.jsonl", a.batch)
    Sempty = infer_semantics(empty_prompts, a.model, work / "evidence_empty_scores.jsonl", a.batch)
    results = {
        "protocol": "V145_TARGET_CONDITIONED_SEMANTIC_EPISTEMIC_GATE",
        "model": a.model, "rows": len(frame), "fields": FIELDS,
        "session": evaluate_split("session", X, S, y, frame.session_id),
        "objective": evaluate_split("objective", X, S, y, objective_groups),
        "counterfactual_controls": {},
    }
    for key, groups in (("session", frame.session_id), ("objective", objective_groups)):
        results["counterfactual_controls"][key] = {
            "objective_swap": semantic_control_eval(S[ci], Sswap, y[ci], np.asarray(groups)[ci]),
            "evidence_empty": semantic_control_eval(S[ci], Sempty, y[ci], np.asarray(groups)[ci]),
        }
    pass_parts = []
    for key in ("session", "objective"):
        r = results[key]
        pass_parts.append(r["improvement"] >= .003 and r["fold_wins"] >= 4 and r["bootstrap_improvement_95"][0] > 0)
        pass_parts.append(r["shuffled_improvement"] < .0005)
        c = results["counterfactual_controls"][key]
        pass_parts.append(c["objective_swap"]["main_advantage"] >= .001)
        pass_parts.append(c["evidence_empty"]["main_advantage"] >= .001)
    results["decision"] = "PHASE_CHANGE_CONFIRMED" if all(pass_parts) else "DO_NOT_SPEND_SUBMISSION"
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path); p.add_argument("--labels", type=Path)
    p.add_argument("--transcripts", type=Path); p.add_argument("--work", type=Path, default=Path("v145_work"))
    p.add_argument("--out", type=Path, default=Path("v145_results.json"))
    p.add_argument("--model", default="Qwen/Qwen3-8B-AWQ"); p.add_argument("--batch", type=int, default=2048)
    p.add_argument("--limit", type=int, default=0, help="0 uses all rows; use 8000 for the sniff gate")
    p.add_argument("--control-limit", type=int, default=2500, help="rows for objective-swap and no-evidence controls")
    p.add_argument("--self-test", action="store_true"); a = p.parse_args()
    if not a.self_test and not all((a.features, a.labels, a.transcripts)):
        p.error("--features, --labels and --transcripts are required")
    main(a)
