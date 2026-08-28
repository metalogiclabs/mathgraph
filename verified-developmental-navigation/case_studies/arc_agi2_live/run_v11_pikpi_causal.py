import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2", HERE / "run_v2.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

# Preserve safe recolor handling used by V3/V4.
_original = v2.v1.infer_recolor
def safe_infer_recolor(pairs, pre=lambda x: x):
    for inp, _ in pairs:
        try:
            z = pre(inp)
        except Exception:
            return None
        if z is None:
            return None
    return _original(pairs, pre=pre)
v2.v1.infer_recolor = safe_infer_recolor

# These are the four source-distinct ARC-AGI-1 evaluation tasks on which V4
# established a strict depth-2 held-out capability gain over the frozen base.
# They are frozen here before this test; no new target selection occurs.
TARGETS = ["0c786b71", "59341089", "833dafe3", "be03b35f"]
PRIMARY_BUDGET = 1000
SECONDARY_BUDGETS = [100, 250, 500, 1000, 2500, 5000]


def pseudo_task(pairs):
    # v1.signature only reads train input/output pairs.
    return {"train": [{"input": [list(r) for r in i], "output": [list(r) for r in o]} for i,o in pairs], "test": []}


def all_programs_ordered(pairs, order):
    for fam in order:
        for name, p in v2.programs(fam, pairs):
            yield fam, name, p


def safe_apply(p, g):
    try:
        return p(g)
    except Exception:
        return None


def exact_pairs(p, pairs):
    try:
        return v2.v1.exact_on_pairs(p, pairs)
    except Exception:
        return False


def composition_rank(task, first_order_fn, second_order_fn, max_candidates=25000):
    pairs = v2.v1.task_pairs(task)
    tried = 0
    first_order = first_order_fn(task)
    for fam1, name1, p1 in all_programs_ordered(pairs, first_order):
        transformed = []
        ok = True
        for inp, out in pairs:
            z = safe_apply(p1, inp)
            if z is None:
                ok = False
                break
            transformed.append((z, out))
        if not ok:
            continue
        second_order = second_order_fn(transformed)
        for fam2, name2, p2 in all_programs_ordered(transformed, second_order):
            tried += 1
            if tried > max_candidates:
                return {"fit": False, "rank": None, "tried": max_candidates, "truncated": True}
            def comp(g, p1=p1, p2=p2):
                z = safe_apply(p1, g)
                return None if z is None else safe_apply(p2, z)
            if exact_pairs(comp, pairs):
                solved = bool(v2.v1.task_solved(comp, task))
                return {
                    "fit": True, "heldout_solved": solved, "rank": tried, "tried": tried,
                    "program": f"{fam1}/{name1} THEN {fam2}/{name2}", "truncated": False,
                }
    return {"fit": False, "rank": None, "tried": tried, "truncated": False}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_v11_pikpi_causal.py ARC1_TRAIN ARC1_EVAL")
    train = v2.v1.load_tasks(sys.argv[1])
    ev = v2.v1.load_tasks(sys.argv[2])
    if len(train) != 400 or len(ev) != 400:
        raise SystemExit(f"unexpected ARC-AGI-1 counts train={len(train)} eval={len(ev)}")

    global_order, sig_orders, gok, gseen, solved_ids = v2.train_router(train)

    def warm_first(task):
        return sig_orders.get(v2.v1.signature(task), global_order)
    def warm_second(pairs):
        return sig_orders.get(v2.v1.signature(pseudo_task(pairs)), global_order)

    def cold_first(task):
        return global_order
    def cold_second(pairs):
        return global_order

    # Raw-history reconstruction: recompute the same signature-conditioned order
    # directly from training records for each target rather than using retained
    # sig_orders. If it reproduces WARM, the learned quotient is a compression,
    # not privileged information.
    def reconstruct_order(sig):
        import collections
        gok2 = collections.Counter(); gseen2 = collections.Counter()
        sok = collections.Counter(); sseen = collections.Counter()
        for _, t in sorted(train.items()):
            ts = v2.v1.signature(t)
            for fam in v2.NEW_BASE:
                gseen2[fam] += 1
                ok = v2.family_success(t, fam)
                if ok: gok2[fam] += 1
                if ts == sig:
                    sseen[fam] += 1
                    if ok: sok[fam] += 1
        def grate(f): return (gok2[f] + 1) / (gseen2[f] + 2)
        go = sorted(v2.NEW_BASE, key=lambda f:(-grate(f), v2.NEW_BASE.index(f)))
        if not sum(sseen.values()): return go
        def score(f): return (sok[f] + 4*grate(f)) / (sseen[f] + 4)
        return sorted(v2.NEW_BASE, key=lambda f:(-score(f), go.index(f)))

    raw_cache = {}
    def raw_for_sig(sig):
        if sig not in raw_cache: raw_cache[sig] = reconstruct_order(sig)
        return raw_cache[sig]
    def raw_first(task): return raw_for_sig(v2.v1.signature(task))
    def raw_second(pairs): return raw_for_sig(v2.v1.signature(pseudo_task(pairs)))

    # Sham: same retained structure size, but reverse each signature-conditioned
    # family order. This keeps the representation format while destroying the law.
    def sham_first(task): return list(reversed(warm_first(task)))
    def sham_second(pairs): return list(reversed(warm_second(pairs)))

    arms = {
        "WARM_RETAINED_PI": (warm_first, warm_second),
        "RAW_HISTORY_RECONSTRUCT": (raw_first, raw_second),
        "COLD_GLOBAL": (cold_first, cold_second),
        "SHAM_REVERSED_PI": (sham_first, sham_second),
    }

    rows = []
    for tid in TARGETS:
        task = ev[tid]
        for arm, (f1, f2) in arms.items():
            r = composition_rank(task, f1, f2)
            rows.append({"task": tid, "arm": arm, **r})

    by_arm = {}
    for arm in arms:
        rr = [r for r in rows if r["arm"] == arm]
        ranks = [r["rank"] for r in rr if r.get("heldout_solved") and r.get("rank") is not None]
        by_arm[arm] = {
            "heldout_solved": sum(bool(r.get("heldout_solved")) for r in rr),
            "ranks": ranks,
            "mean_rank": (sum(ranks)/len(ranks)) if ranks else None,
            "median_rank": (sorted(ranks)[len(ranks)//2-1:len(ranks)//2+1] if len(ranks)%2==0 else [sorted(ranks)[len(ranks)//2]]),
            "budget_success": {str(b): sum(bool(r.get("heldout_solved")) and r.get("rank") is not None and r["rank"] <= b for r in rr) for b in SECONDARY_BUDGETS},
        }

    primary = {arm: by_arm[arm]["budget_success"][str(PRIMARY_BUDGET)] for arm in arms}
    strict_pi_to_k = (
        primary["WARM_RETAINED_PI"] > primary["COLD_GLOBAL"]
        and primary["WARM_RETAINED_PI"] > primary["SHAM_REVERSED_PI"]
    )
    raw_matches_warm = all(
        next(r for r in rows if r["task"]==tid and r["arm"]=="WARM_RETAINED_PI").get("rank") ==
        next(r for r in rows if r["task"]==tid and r["arm"]=="RAW_HISTORY_RECONSTRUCT").get("rank")
        for tid in TARGETS
    )

    result = {
        "schema": "verified-developmental-navigation.arc-pi-to-k-causal.v11",
        "source": {"repository":"fchollet/ARC-AGI","commit":"399030444e0ab0cc8b4e199870fb20b863846f34"},
        "frozen_targets_from_v4": TARGETS,
        "primary_budget": PRIMARY_BUDGET,
        "secondary_budgets": SECONDARY_BUDGETS,
        "question": "Does the retained signature-conditioned interface causally move depth-2 constructor discovery inside a fixed verifier budget?",
        "arms": ["WARM_RETAINED_PI","RAW_HISTORY_RECONSTRUCT","COLD_GLOBAL","SHAM_REVERSED_PI"],
        "by_arm": by_arm,
        "primary_budget_successes": primary,
        "strict_pi_to_k_gate": strict_pi_to_k,
        "raw_history_reconstructs_warm_ranks": raw_matches_warm,
        "interpretation_rule": {
            "positive": "WARM beats both COLD and SHAM at the preregistered 1000-candidate budget.",
            "compression_only": "If RAW reconstructs WARM exactly, the retained Pi is a compiled sufficient interface/compression of prior evidence, not information unavailable in raw history.",
            "negative": "If WARM does not beat COLD and SHAM, the natural Pi->K causal arrow is not established by this interface."
        },
        "rows": rows,
    }
    out = HERE / "results_v11_pikpi_causal"
    out.mkdir(exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!="rows"}, indent=2, sort_keys=True))
    print("STRICT_PI_TO_K_GATE", strict_pi_to_k)
    print("RAW_HISTORY_RECONSTRUCTS_WARM_RANKS", raw_matches_warm)

if __name__ == "__main__":
    main()
