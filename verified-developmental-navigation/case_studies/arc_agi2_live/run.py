import collections
import json
import math
import statistics
import sys
from pathlib import Path

FAMILIES = [
    "geom",
    "recolor",
    "crop_color",
    "crop_nonbg",
    "scale_cells",
    "tile_grid",
    "downsample_uniform",
]
EXTENSION = "geometry_then_recolor"


def T(g):
    return tuple(tuple(r) for r in g)


def L(g):
    return [list(r) for r in g]


def shape(g):
    return (len(g), len(g[0]) if g else 0)


def rot90(g):
    return tuple(tuple(row) for row in zip(*g[::-1]))


def rot180(g):
    return rot90(rot90(g))


def rot270(g):
    return rot90(rot180(g))


def flip_h(g):
    return tuple(tuple(reversed(r)) for r in g)


def flip_v(g):
    return tuple(reversed(g))


def transpose(g):
    return tuple(tuple(row) for row in zip(*g))


def anti_transpose(g):
    return flip_h(flip_v(transpose(g)))


GEOMS = [
    ("identity", lambda g: g),
    ("rot90", rot90),
    ("rot180", rot180),
    ("rot270", rot270),
    ("flip_h", flip_h),
    ("flip_v", flip_v),
    ("transpose", transpose),
    ("anti_transpose", anti_transpose),
]


def colors(g):
    return set(x for r in g for x in r)


def bbox(g, pred):
    pts = [(i, j) for i, r in enumerate(g) for j, x in enumerate(r) if pred(x)]
    if not pts:
        return None
    rs = [p[0] for p in pts]
    cs = [p[1] for p in pts]
    a, b, c, d = min(rs), max(rs), min(cs), max(cs)
    return tuple(tuple(g[i][j] for j in range(c, d + 1)) for i in range(a, b + 1))


def infer_recolor(pairs, pre=lambda x: x):
    m = {}
    for inp, out in pairs:
        x = pre(inp)
        if shape(x) != shape(out):
            return None
        for xr, yr in zip(x, out):
            for a, b in zip(xr, yr):
                if a in m and m[a] != b:
                    return None
                m[a] = b
    return m


def recolor_program(m, pre=lambda x: x):
    return lambda g: tuple(tuple(m.get(x, x) for x in r) for r in pre(g))


def candidate_programs(family, pairs):
    if family == "geom":
        return [(name, fn) for name, fn in GEOMS]

    if family == "recolor":
        m = infer_recolor(pairs)
        return [] if m is None else [("recolor:" + repr(sorted(m.items())), recolor_program(m))]

    if family == "crop_color":
        cs = sorted(set().union(*(colors(inp) for inp, _ in pairs)))
        out = []
        for c in cs:
            def f(g, c=c):
                return bbox(g, lambda x: x == c)
            out.append((f"crop_color:{c}", f))
        return out

    if family == "crop_nonbg":
        cs = sorted(set().union(*(colors(inp) for inp, _ in pairs)))
        out = []
        for c in cs:
            def f(g, c=c):
                return bbox(g, lambda x: x != c)
            out.append((f"crop_nonbg:{c}", f))
        return out

    if family in ("scale_cells", "tile_grid"):
        ratios = []
        for inp, out in pairs:
            hi, wi = shape(inp); ho, wo = shape(out)
            if hi == 0 or wi == 0 or ho % hi or wo % wi:
                return []
            ratios.append((ho // hi, wo // wi))
        if not ratios or len(set(ratios)) != 1:
            return []
        rh, rw = ratios[0]
        if rh < 1 or rw < 1 or (rh, rw) == (1, 1):
            return []
        if family == "scale_cells":
            def f(g, rh=rh, rw=rw):
                rows = []
                for r in g:
                    rr = tuple(x for x in r for _ in range(rw))
                    for _ in range(rh):
                        rows.append(rr)
                return tuple(rows)
            return [(f"scale_cells:{rh}x{rw}", f)]
        else:
            def f(g, rh=rh, rw=rw):
                wide = tuple(tuple(x for _ in range(rw) for x in r) for r in g)
                return tuple(row for _ in range(rh) for row in wide)
            return [(f"tile_grid:{rh}x{rw}", f)]

    if family == "downsample_uniform":
        ratios = []
        for inp, out in pairs:
            hi, wi = shape(inp); ho, wo = shape(out)
            if ho == 0 or wo == 0 or hi % ho or wi % wo:
                return []
            ratios.append((hi // ho, wi // wo))
        if not ratios or len(set(ratios)) != 1:
            return []
        rh, rw = ratios[0]
        if rh < 1 or rw < 1 or (rh, rw) == (1, 1):
            return []
        def f(g, rh=rh, rw=rw):
            h, w = shape(g)
            if h % rh or w % rw:
                return None
            rows = []
            for i in range(0, h, rh):
                row = []
                for j in range(0, w, rw):
                    block = [g[ii][jj] for ii in range(i, i+rh) for jj in range(j, j+rw)]
                    if len(set(block)) != 1:
                        return None
                    row.append(block[0])
                rows.append(tuple(row))
            return tuple(rows)
        return [(f"downsample_uniform:{rh}x{rw}", f)]

    if family == EXTENSION:
        ans = []
        for name, fn in GEOMS[1:]:
            m = infer_recolor(pairs, pre=fn)
            if m is not None:
                ans.append((f"{name}+recolor:{repr(sorted(m.items()))}", recolor_program(m, pre=fn)))
        return ans

    raise KeyError(family)


def exact_on_pairs(prog, pairs):
    try:
        for inp, out in pairs:
            y = prog(inp)
            if y is None or y != out:
                return False
        return True
    except Exception:
        return False


def task_pairs(task):
    return [(T(x["input"]), T(x["output"])) for x in task["train"]]


def test_inputs_outputs(task):
    return [(T(x["input"]), T(x["output"])) for x in task["test"]]


def task_solved(prog, task):
    return exact_on_pairs(prog, test_inputs_outputs(task))


def dim_rel(inp, out):
    a, b = shape(inp), shape(out)
    if a == b: return "same"
    if a == (b[1], b[0]): return "swap"
    if b[0] >= a[0] and b[1] >= a[1]: return "larger"
    if b[0] <= a[0] and b[1] <= a[1]: return "smaller"
    return "mixed"


def color_rel(inp, out):
    a, b = len(colors(inp)), len(colors(out))
    if a == b: return "same"
    return "more" if b > a else "less"


def signature(task):
    pairs = task_pairs(task)
    dr = tuple(sorted(set(dim_rel(i, o) for i, o in pairs)))
    cr = tuple(sorted(set(color_rel(i, o) for i, o in pairs)))
    n = len(pairs)
    nb = "1" if n == 1 else "2" if n == 2 else "3+"
    return (dr, cr, nb)


def load_tasks(path):
    out = {}
    for p in sorted(Path(path).glob("*.json")):
        with open(p) as f:
            out[p.stem] = json.load(f)
    return out


def first_fit_in_family(family, task):
    pairs = task_pairs(task)
    tried = 0
    for name, prog in candidate_programs(family, pairs):
        tried += 1
        if exact_on_pairs(prog, pairs):
            return (name, prog, tried)
    return (None, None, tried)


def family_training_success(task, family):
    name, prog, _ = first_fit_in_family(family, task)
    return bool(prog is not None and task_solved(prog, task))


def train_router(tasks):
    global_ok = collections.Counter()
    global_seen = collections.Counter()
    sig_ok = collections.defaultdict(collections.Counter)
    sig_seen = collections.defaultdict(collections.Counter)
    for _, task in sorted(tasks.items()):
        sig = signature(task)
        for fam in FAMILIES:
            global_seen[fam] += 1
            sig_seen[sig][fam] += 1
            if family_training_success(task, fam):
                global_ok[fam] += 1
                sig_ok[sig][fam] += 1
    def rate(ok, seen, fam):
        return (ok[fam] + 1.0) / (seen[fam] + 2.0)
    global_order = sorted(FAMILIES, key=lambda f: (-rate(global_ok, global_seen, f), FAMILIES.index(f)))
    sig_orders = {}
    for sig in sig_seen:
        # Shrink sparse signature evidence toward the global learned prior.
        def score(f):
            local_n = sig_seen[sig][f]
            local_ok = sig_ok[sig][f]
            g = rate(global_ok, global_seen, f)
            return (local_ok + 4.0*g) / (local_n + 4.0)
        sig_orders[sig] = sorted(FAMILIES, key=lambda f: (-score(f), global_order.index(f)))
    return global_order, sig_orders, dict(global_ok), dict(global_seen)


def solve_with_order(task, order, allow_extension=False):
    pairs = task_pairs(task)
    tried = 0
    for fam in order:
        for name, prog in candidate_programs(fam, pairs):
            tried += 1
            if exact_on_pairs(prog, pairs):
                return {"family": fam, "program": name, "prog": prog, "tried": tried, "extended": False}
    if allow_extension:
        for name, prog in candidate_programs(EXTENSION, pairs):
            tried += 1
            if exact_on_pairs(prog, pairs):
                return {"family": EXTENSION, "program": name, "prog": prog, "tried": tried, "extended": True}
    return {"family": None, "program": None, "prog": None, "tried": tried, "extended": allow_extension}


def score_arm(eval_tasks, order_fn, allow_extension=False):
    rows = []
    for tid, task in sorted(eval_tasks.items()):
        r = solve_with_order(task, order_fn(task), allow_extension=allow_extension)
        solved = bool(r["prog"] is not None and task_solved(r["prog"], task))
        rows.append({
            "task": tid,
            "solved": solved,
            "candidate_evaluations": r["tried"],
            "family": r["family"],
            "program": r["program"],
            "extension_used": r["extended"] and r["family"] == EXTENSION,
            "fit_found": r["prog"] is not None,
        })
    return rows


def summarize(rows):
    costs = [r["candidate_evaluations"] for r in rows]
    return {
        "tasks": len(rows),
        "solved": sum(r["solved"] for r in rows),
        "fit_found": sum(r["fit_found"] for r in rows),
        "total_candidate_evaluations": sum(costs),
        "mean_candidate_evaluations": sum(costs) / len(costs),
        "median_candidate_evaluations": statistics.median(costs),
        "extension_used": sum(r["extension_used"] for r in rows),
        "extension_solved": sum(r["extension_used"] and r["solved"] for r in rows),
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: run.py TRAIN_DIR EVAL_DIR")
    train_tasks = load_tasks(sys.argv[1])
    eval_tasks = load_tasks(sys.argv[2])
    if len(train_tasks) != 1000 or len(eval_tasks) != 120:
        raise SystemExit(f"unexpected ARC-AGI-2 counts train={len(train_tasks)} eval={len(eval_tasks)}")

    global_order, sig_orders, global_ok, global_seen = train_router(train_tasks)
    global_rows = score_arm(eval_tasks, lambda task: global_order, allow_extension=False)
    vdn_base_rows = score_arm(eval_tasks, lambda task: sig_orders.get(signature(task), global_order), allow_extension=False)
    vdn_ext_rows = score_arm(eval_tasks, lambda task: sig_orders.get(signature(task), global_order), allow_extension=True)

    g_by = {r["task"]: r for r in global_rows}
    v_by = {r["task"]: r for r in vdn_base_rows}
    common = [tid for tid in g_by if g_by[tid]["solved"] and v_by[tid]["solved"]]
    common_g = sum(g_by[t]["candidate_evaluations"] for t in common)
    common_v = sum(v_by[t]["candidate_evaluations"] for t in common)

    base_by = {r["task"]: r for r in vdn_base_rows}
    ext_by = {r["task"]: r for r in vdn_ext_rows}
    new_solved = [tid for tid in ext_by if ext_by[tid]["solved"] and not base_by[tid]["solved"]]
    lost_solved = [tid for tid in ext_by if base_by[tid]["solved"] and not ext_by[tid]["solved"]]

    Sg, Sv, Se = summarize(global_rows), summarize(vdn_base_rows), summarize(vdn_ext_rows)
    navigation_advantage = (
        Sv["solved"] >= Sg["solved"]
        and common_v < common_g
    )
    phase_change = bool(new_solved) and not lost_solved

    result = {
        "schema": "verified-developmental-navigation.arc-agi2-live.v1",
        "source": {
            "repository": "arcprize/ARC-AGI-2",
            "commit": "f3283f727488ad98fe575ea6a5ac981e4a188e49",
            "training_tasks": len(train_tasks),
            "evaluation_tasks": len(eval_tasks),
        },
        "candidate_families": FAMILIES,
        "extension_family": EXTENSION,
        "global_learned_order": global_order,
        "training_family_exact_solve_counts": global_ok,
        "training_family_task_counts": global_seen,
        "signature_count": len(sig_orders),
        "global": Sg,
        "vdn_base": Sv,
        "vdn_with_extension": Se,
        "common_solved": {
            "count": len(common),
            "global_total_candidate_evaluations": common_g,
            "vdn_total_candidate_evaluations": common_v,
            "ratio_global_over_vdn": (common_g / common_v) if common_v else None,
        },
        "newly_solved_by_extension": new_solved,
        "lost_by_extension": lost_solved,
        "navigation_advantage": navigation_advantage,
        "developmental_phase_change": phase_change,
        "rows": {
            "global": global_rows,
            "vdn_base": vdn_base_rows,
            "vdn_with_extension": vdn_ext_rows,
        },
    }

    outdir = Path("verified-developmental-navigation/case_studies/arc_agi2_live/results")
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "result.json", "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2, sort_keys=True))
    print("NAVIGATION_ADVANTAGE", navigation_advantage)
    print("DEVELOPMENTAL_PHASE_CHANGE", phase_change)


if __name__ == "__main__":
    main()
