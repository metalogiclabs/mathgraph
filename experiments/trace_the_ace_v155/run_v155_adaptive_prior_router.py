#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
V150 = HERE.parent / 'trace_the_ace_v150'
sys.path.insert(0, str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base, safe_logit

SEED = 20260826


def prior_with_support(train_obj, train_y, val_obj, alpha):
    mu = (float(train_y.sum()) + 1.0) / (len(train_y) + 2.0)
    sums, counts = {}, {}
    for o, y in zip(train_obj, train_y):
        sums[o] = sums.get(o, 0.0) + float(y)
        counts[o] = counts.get(o, 0) + 1
    p = np.empty(len(val_obj), float)
    n = np.empty(len(val_obj), float)
    for i, o in enumerate(val_obj):
        ni = counts.get(o, 0); si = sums.get(o, 0.0)
        p[i] = (si + alpha * mu) / (ni + alpha) if ni else mu
        n[i] = ni
    return np.clip(p, 1e-5, 1 - 1e-5), n


def adaptive_weight(base_p, support, family, wmax, tau, gamma):
    base_p = np.clip(np.asarray(base_p), 1e-5, 1 - 1e-5)
    support = np.asarray(support, float)
    if family == 'fixed':
        return np.full(len(base_p), wmax, float)
    s = support / (support + tau)
    if family == 'support':
        return wmax * s
    # confidence term is 1 at p=.5 and approaches 0 as the base becomes certain.
    u = np.clip(4.0 * base_p * (1.0 - base_p), 0.0, 1.0)
    if family == 'support_uncertainty':
        return wmax * s * np.power(u, gamma)
    raise ValueError(family)


def blend(base_p, prior_p, w):
    return expit((1.0 - w) * safe_logit(base_p) + w * safe_logit(prior_p))


def candidate_grid():
    out = []
    for w in (.10, .15, .20, .25, .30, .35, .40, .45, .50):
        out.append(('fixed', w, 1.0, 1.0))
    for fam in ('support', 'support_uncertainty'):
        for w in (.25, .35, .45, .55, .65, .75):
            for tau in (1.0, 2.0, 5.0, 10.0, 20.0, 50.0):
                gammas = (1.0,) if fam == 'support' else (.5, 1.0, 2.0)
                for gamma in gammas:
                    out.append((fam, w, tau, gamma))
    return out


def eval_session(y, num, obj, groups, prior_obj):
    groups = np.asarray(groups).astype(str)
    folds = []
    p0 = np.zeros(len(y)); p1 = np.zeros(len(y)); pfixed = np.zeros(len(y))
    chosen = []
    for k, (tr, va) in enumerate(GroupKFold(5).split(np.zeros(len(y)), y, groups), 1):
        gtr = groups[tr]
        inner_splits = list(GroupKFold(min(4, len(np.unique(gtr)))).split(np.zeros(len(tr)), y[tr], gtr))
        inner_base = np.zeros(len(tr))
        # Freeze alpha=2 from V154; only test the residual: weight routing by support/confidence.
        inner_prior = np.zeros(len(tr)); inner_support = np.zeros(len(tr))
        for itr, iva in inner_splits:
            bm = fit_base(num[tr][itr], obj[tr][itr], y[tr][itr])
            inner_base[iva] = predict_base(bm, num[tr][iva], obj[tr][iva])
            pp, nn = prior_with_support(prior_obj[tr][itr], y[tr][itr], prior_obj[tr][iva], 2.0)
            inner_prior[iva], inner_support[iva] = pp, nn

        best = None
        for fam, wmax, tau, gamma in candidate_grid():
            w = adaptive_weight(inner_base, inner_support, fam, wmax, tau, gamma)
            pr = blend(inner_base, inner_prior, w)
            ll = float(log_loss(y[tr], pr))
            if best is None or ll < best[0]:
                best = (ll, fam, wmax, tau, gamma)
        _, fam, wmax, tau, gamma = best

        # Fair fixed-weight comparator chosen inside the same inner OOF data.
        fbest = None
        for wconst in (.10, .15, .20, .25, .30, .35, .40, .45, .50):
            ll = float(log_loss(y[tr], blend(inner_base, inner_prior, np.full(len(tr), wconst))))
            if fbest is None or ll < fbest[0]: fbest = (ll, wconst)
        _, fixed_w = fbest

        bm = fit_base(num[tr], obj[tr], y[tr]); pb = predict_base(bm, num[va], obj[va])
        pp, nn = prior_with_support(prior_obj[tr], y[tr], prior_obj[va], 2.0)
        ww = adaptive_weight(pb, nn, fam, wmax, tau, gamma)
        pa = blend(pb, pp, ww)
        pfix = blend(pb, pp, np.full(len(va), fixed_w))
        p0[va], p1[va], pfixed[va] = pb, pa, pfix
        row = {
            'fold': k, 'family': fam, 'wmax': wmax, 'tau': tau, 'gamma': gamma,
            'fixed_weight': fixed_w, 'mean_weight': float(np.mean(ww)),
            'median_support': float(np.median(nn)), 'zero_support_rate': float(np.mean(nn == 0)),
            'base': float(log_loss(y[va], pb)), 'adaptive': float(log_loss(y[va], pa)),
            'fixed': float(log_loss(y[va], pfix)),
        }
        row['adaptive_win'] = bool(row['adaptive'] < row['base'])
        row['beats_fixed'] = bool(row['adaptive'] < row['fixed'])
        folds.append(row); chosen.append(fam)

    def metrics(p): return {'logloss': float(log_loss(y, p)), 'auc': float(roc_auc_score(y, p))}
    mb, ma, mf = metrics(p0), metrics(p1), metrics(pfixed)
    return {
        'base': mb, 'adaptive': ma, 'fixed': mf,
        'adaptive_improvement': mb['logloss'] - ma['logloss'],
        'fixed_improvement': mb['logloss'] - mf['logloss'],
        'adaptive_over_fixed': mf['logloss'] - ma['logloss'],
        'fold_wins': int(sum(f['adaptive_win'] for f in folds)),
        'beats_fixed_folds': int(sum(f['beats_fixed'] for f in folds)),
        'chosen_families': chosen, 'folds': folds,
    }


def main(a):
    b = load_bundle(a.bundle.resolve()); y=b['y']; num=b['numeric']; obj=b['objective']; sess=b['session']
    rng = np.random.default_rng(SEED); sh = obj[rng.permutation(len(obj))]
    real = eval_session(y, num, obj, sess, obj)
    shuffled = eval_session(y, num, obj, sess, sh)
    sep = real['adaptive_improvement'] - shuffled['adaptive_improvement']
    if real['adaptive_improvement'] >= .0035 and real['fold_wins'] >= 4 and sep >= .002:
        decision = 'BIG_ADAPTIVE_PRIOR_GAIN'
    elif real['adaptive_over_fixed'] >= .0005 and real['beats_fixed_folds'] >= 3 and sep >= .001:
        decision = 'ADAPTIVE_ROUTER_SEPARATOR_FOUND'
    elif real['fixed_improvement'] >= .0015 and sep >= .001:
        decision = 'FIXED_PRIOR_RETAINED_ADAPTIVITY_REVOKED'
    else:
        decision = 'PRIOR_GAIN_NOT_STABLE'
    out = {
        'protocol': 'V155_SUPPORT_CONFIDENCE_ADAPTIVE_OBJECTIVE_PRIOR',
        'warning': 'TRIAGE_ONLY_NOT_SUBMISSION_EVIDENCE', 'rows': len(y),
        'residual': 'V154 retained objective prior at +0.002519 session-cold, but one fold lost. Test whether support and base uncertainty identify when to trust the prior.',
        'real': real, 'shuffled_objective_control': shuffled, 'separator': sep, 'decision': decision,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle', type=Path, required=True); p.add_argument('--out', type=Path, default=Path('v155_results.json')); main(p.parse_args())
