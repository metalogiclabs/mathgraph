#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).resolve().parent
V145 = HERE.parent / 'trace_the_ace_v145'
sys.path.insert(0, str(V145))
from v71_mastery_events import inspect_headers, load_transcript, extract_episodes
from v75_canonical_trajectory import trajectory_views

SEED = 20260827
EPS = 1e-5


def fit_base(Xnum, obj, y):
    enc = OneHotEncoder(handle_unknown='ignore', min_frequency=2)
    O = enc.fit_transform(obj.reshape(-1, 1))
    sc = StandardScaler().fit(Xnum)
    X = hstack([O, csr_matrix(sc.transform(Xnum))], format='csr')
    m = LogisticRegression(C=.25, max_iter=300, solver='liblinear', random_state=SEED).fit(X, y)
    return enc, sc, m


def pred_base(model, Xnum, obj):
    enc, sc, m = model
    X = hstack([enc.transform(obj.reshape(-1, 1)), csr_matrix(sc.transform(Xnum))], format='csr')
    return np.clip(m.predict_proba(X)[:, 1], EPS, 1-EPS)


def fit_aug(Xnum, G, obj, y):
    enc = OneHotEncoder(handle_unknown='ignore', min_frequency=2)
    O = enc.fit_transform(obj.reshape(-1, 1))
    sc = StandardScaler().fit(np.hstack([Xnum, G]))
    X = hstack([O, csr_matrix(sc.transform(np.hstack([Xnum, G])))], format='csr')
    m = LogisticRegression(C=.25, max_iter=300, solver='liblinear', random_state=SEED).fit(X, y)
    return enc, sc, m


def pred_aug(model, Xnum, G, obj):
    enc, sc, m = model
    X = hstack([enc.transform(obj.reshape(-1, 1)), csr_matrix(sc.transform(np.hstack([Xnum, G])))], format='csr')
    return np.clip(m.predict_proba(X)[:, 1], EPS, 1-EPS)


def compile_rows(frame: pd.DataFrame, tdir: Path):
    # Inspect headers before schema decisions, then build one target-independent episode parse per session.
    print('FEATURE_HEADERS', list(frame.columns), flush=True)
    first = tdir / f"{str(frame.iloc[0].session_id)}.csv"
    print('TRANSCRIPT_HEADERS', inspect_headers(first), flush=True)

    obj_table = (frame[['learning_objective_id','learning_objective']]
                 .drop_duplicates('learning_objective_id')
                 .sort_values('learning_objective_id'))
    obj_ids = obj_table.learning_objective_id.astype(str).tolist()
    obj_text = obj_table.learning_objective.fillna('').astype(str).tolist()
    obj_to_i = {q:i for i,q in enumerate(obj_ids)}

    # Parse every session once. extract_episodes with empty objective preserves episode structure;
    # objective identity is assigned below from question text against the objective catalogue.
    sessions = {}
    episode_texts = []
    episode_refs = []
    unique_sessions = frame.session_id.astype(str).drop_duplicates().tolist()
    for n, sid in enumerate(unique_sessions, 1):
        df = load_transcript(tdir / f'{sid}.csv')
        eps = extract_episodes(df, '')
        sessions[sid] = eps
        for j, e in enumerate(eps):
            episode_texts.append(e.question + ' ' + e.answer + ' ' + e.feedback)
            episode_refs.append((sid, j))
        if n % 1000 == 0:
            print(f'parsed sessions {n}/{len(unique_sessions)} episodes={len(episode_texts)}', flush=True)

    # Catalogue matching gives each observed episode a source objective. This is label-free.
    vec = TfidfVectorizer(ngram_range=(1,2), min_df=1, max_features=120000, sublinear_tf=True)
    Mobj = vec.fit_transform(obj_text)
    source_map = defaultdict(list)
    chunk = 5000
    for st in range(0, len(episode_texts), chunk):
        T = vec.transform(episode_texts[st:st+chunk])
        sim = T @ Mobj.T
        best = np.asarray(sim.argmax(axis=1)).ravel()
        vals = np.asarray(sim.max(axis=1).toarray()).ravel()
        for k, (oi, sv) in enumerate(zip(best, vals)):
            sid, j = episode_refs[st+k]
            source_map[sid].append((j, int(oi), float(sv)))
        print(f'matched episodes {min(st+chunk,len(episode_texts))}/{len(episode_texts)}', flush=True)

    # One canonical whole-trajectory baseline plus event relation records per response row.
    whole = []
    events = []
    exact = []
    cache_df = {}
    for n, row in enumerate(frame.itertuples(index=False), 1):
        sid = str(row.session_id)
        if sid not in cache_df:
            cache_df[sid] = load_transcript(tdir / f'{sid}.csv')
        _, wf, _ = trajectory_views(cache_df[sid], str(row.learning_objective))
        whole.append(wf)
        tgt = obj_to_i[str(row.learning_objective_id)]
        eps = sessions[sid]
        matches = source_map[sid]
        erow = []
        ex_pos = ex_neg = ex_mass = 0.0
        for (j, src, simv) in matches:
            if j >= len(eps):
                continue
            e = eps[j]
            # Signed evidence: independent positive feedback vs corrected/negative evidence.
            pos = e.feedback_pos * e.answer_substantive * (1.0 - e.hinted)
            neg = e.feedback_neg * max(e.answer_substantive, 0.5)
            signal = float(pos - neg)
            if signal == 0.0 or simv < .02:
                continue
            rec = float(0.15 + 0.85 * e.recency)
            x = signal * rec * simv
            erow.append((src, x, simv, rec))
            if src == tgt:
                ex_mass += abs(x)
                if x > 0: ex_pos += x
                else: ex_neg += -x
        events.append(erow)
        exact.append([ex_pos, ex_neg, ex_pos-ex_neg, ex_mass, float(len(erow))])
        if n % 2000 == 0:
            print(f'compiled rows {n}/{len(frame)}', flush=True)
    return np.vstack(whole), np.asarray(exact, float), events, obj_to_i


def learn_graph(indices, target_idx, y, events, nobj, source_perm=None, shrink=25.0):
    # Directional edge weight w(source,target), centred by target prevalence.
    sum_x2 = defaultdict(float)
    sum_xy = defaultdict(float)
    cnt = defaultdict(int)
    prior_sum = np.zeros(nobj, float)
    prior_n = np.zeros(nobj, float)
    for i in indices:
        t = target_idx[i]
        prior_sum[t] += y[i]; prior_n[t] += 1
    global_p = float(np.mean(y[indices]))
    pri = (prior_sum + 20*global_p) / (prior_n + 20)
    for i in indices:
        t = target_idx[i]
        r = float(y[i] - pri[t])
        for src, x, simv, rec in events[i]:
            s = int(source_perm[src]) if source_perm is not None else int(src)
            key = (s, int(t))
            sum_x2[key] += x*x
            sum_xy[key] += x*r
            cnt[key] += 1
    W = {}
    for key, xy in sum_xy.items():
        c = cnt[key]
        # support shrinkage plus ridge-like denominator
        support = c/(c+shrink)
        W[key] = support * xy/(sum_x2[key] + 2.0)
    return W, cnt


def graph_features(indices, target_idx, events, W, cnt, source_perm=None):
    G = np.zeros((len(indices), 9), float)
    for z, i in enumerate(indices):
        t = int(target_idx[i])
        contrib = []
        supports = []
        related_mass = 0.0
        same_mass = 0.0
        for src, x, simv, rec in events[i]:
            s = int(source_perm[src]) if source_perm is not None else int(src)
            w = W.get((s,t), 0.0)
            c = w*x
            contrib.append(c)
            supports.append(cnt.get((s,t), 0))
            if s == t: same_mass += c
            else: related_mass += c
        if contrib:
            a = np.asarray(contrib,float)
            G[z] = [a.sum(), np.abs(a).sum(), np.maximum(a,0).sum(), -np.minimum(a,0).sum(),
                    a.max(), a.min(), related_mass, same_mass, np.log1p(sum(supports))]
    return G


def eval_session(y, obj, sess, whole, exact, events, target_idx, nobj, source_perm=None):
    outer = list(GroupKFold(5).split(np.zeros(len(y)), y, sess))
    p_base = np.zeros(len(y)); p_exact = np.zeros(len(y)); p_graph = np.zeros(len(y))
    folds=[]
    for k,(tr,va) in enumerate(outer,1):
        # Cross-fit graph features on outer training so the augmented learner never sees an edge
        # statistic containing its own target label.
        Gtr = np.zeros((len(tr),9),float)
        gtr_groups = sess[tr]
        nin = min(4, len(np.unique(gtr_groups)))
        for itr, iva in GroupKFold(nin).split(np.zeros(len(tr)), y[tr], gtr_groups):
            src_idx = tr[itr]; dst_idx = tr[iva]
            W,cnt = learn_graph(src_idx,target_idx,y,events,nobj,source_perm)
            Gtr[iva] = graph_features(dst_idx,target_idx,events,W,cnt,source_perm)
        W,cnt = learn_graph(tr,target_idx,y,events,nobj,source_perm)
        Gva = graph_features(va,target_idx,events,W,cnt,source_perm)

        bm = fit_base(whole[tr],obj[tr],y[tr]); pb=pred_base(bm,whole[va],obj[va])
        em = fit_aug(whole[tr],exact[tr],obj[tr],y[tr]); pe=pred_aug(em,whole[va],exact[va],obj[va])
        gm = fit_aug(whole[tr],Gtr,obj[tr],y[tr]); pg=pred_aug(gm,whole[va],Gva,obj[va])
        p_base[va]=pb; p_exact[va]=pe; p_graph[va]=pg
        lb=float(log_loss(y[va],pb)); le=float(log_loss(y[va],pe)); lg=float(log_loss(y[va],pg))
        folds.append({'fold':k,'base':lb,'exact':le,'graph':lg,'exact_gain':lb-le,'graph_gain':lb-lg,'graph_win':lg<lb})
        print(f'fold {k}/5 base={lb:.6f} exact={le:.6f} graph={lg:.6f} gain={lb-lg:.6f}',flush=True)
    return {
      'base_logloss':float(log_loss(y,p_base)),
      'exact_logloss':float(log_loss(y,p_exact)),
      'graph_logloss':float(log_loss(y,p_graph)),
      'exact_improvement':float(log_loss(y,p_base)-log_loss(y,p_exact)),
      'graph_improvement':float(log_loss(y,p_base)-log_loss(y,p_graph)),
      'base_auc':float(roc_auc_score(y,p_base)),
      'graph_auc':float(roc_auc_score(y,p_graph)),
      'fold_wins':int(sum(f['graph_win'] for f in folds)), 'folds':folds
    }


def main(a):
    print('FEATURE_HEADERS', inspect_headers(a.features), flush=True)
    print('LABEL_HEADERS', inspect_headers(a.labels), flush=True)
    f=pd.read_csv(a.features); l=pd.read_csv(a.labels)
    req={'response_id','session_id','learning_objective_id','learning_objective'}
    if not req.issubset(f.columns): raise ValueError(f'missing feature columns {sorted(req-set(f.columns))}')
    if 'is_correct' not in l.columns: raise ValueError('labels missing is_correct')
    frame=f.merge(l[['response_id','is_correct']],on='response_id',validate='one_to_one')
    y=frame.is_correct.to_numpy(int); obj=frame.learning_objective_id.astype(str).to_numpy(); sess=frame.session_id.astype(str).to_numpy()
    whole,exact,events,obj_to_i=compile_rows(frame,a.transcripts)
    target_idx=np.asarray([obj_to_i[x] for x in obj],int); nobj=len(obj_to_i)
    mainres=eval_session(y,obj,sess,whole,exact,events,target_idx,nobj,None)
    rng=np.random.default_rng(SEED); perm=rng.permutation(nobj)
    ctrl=eval_session(y,obj,sess,whole,exact,events,target_idx,nobj,perm)
    sep=mainres['graph_improvement']-ctrl['graph_improvement']
    if mainres['graph_improvement']>=.005 and mainres['fold_wins']>=4 and sep>=.002:
        decision='DIRECTIONAL_TRANSFER_GRAPH_PHASE_CHANGE'
    elif mainres['graph_improvement']>=.002 and mainres['fold_wins']>=3 and sep>=.00075:
        decision='PROMISING_DIRECTIONAL_TRANSFER_SIGNAL'
    elif mainres['graph_improvement']>mainres['exact_improvement']+.0005 and sep>=.0005:
        decision='RELATIONAL_LAYER_REAL_BUT_SMALL'
    else:
        decision='NO_BIG_GAIN_FROM_DIRECTIONAL_TRANSFER_GRAPH'
    out={'protocol':'V166_DIRECTIONAL_OBJECTIVE_TRANSFER_GRAPH','rows':len(frame),'objectives':nobj,
         'session':mainres,'shuffled_source_control':ctrl,'separator':sep,'decision':decision,
         'residual':'V165 preserved target-conditioned episode states but did not improve session-cold loss. V166 adds the missing relational layer: label-free episode-to-source-objective assignment plus strictly cross-fitted learned directional source→target transfer weights.'}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--features',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--transcripts',type=Path,required=True); p.add_argument('--out',type=Path,required=True); main(p.parse_args())
