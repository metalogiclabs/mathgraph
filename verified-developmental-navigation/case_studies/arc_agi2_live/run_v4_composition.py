import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v2

# Guard task-dependent transforms exactly as in run_v2_safe.
_original = run_v2.v1.infer_recolor
def safe_infer_recolor(pairs, pre=lambda x: x):
    for inp, _ in pairs:
        try:
            x = pre(inp)
        except Exception:
            return None
        if x is None:
            return None
    return _original(pairs, pre=pre)
run_v2.v1.infer_recolor = safe_infer_recolor

BASE = run_v2.NEW_BASE
MAX_CANDIDATES_PER_TASK = 25000


def all_programs(pairs):
    for fam in BASE:
        for name, p in run_v2.programs(fam, pairs):
            yield fam, name, p


def safe_apply(p, g):
    try:
        return p(g)
    except Exception:
        return None


def exact_pairs(p, pairs):
    try:
        return run_v2.v1.exact_on_pairs(p, pairs)
    except Exception:
        return False


def solve_base(task):
    pairs = run_v2.v1.task_pairs(task)
    tried = 0
    for fam, name, p in all_programs(pairs):
        tried += 1
        if exact_pairs(p, pairs):
            return {"fit": True, "family": fam, "program": name, "p": p, "tried": tried}
    return {"fit": False, "family": None, "program": None, "p": None, "tried": tried}


def solve_depth2(task):
    pairs = run_v2.v1.task_pairs(task)
    tried = 0
    # Search only genuine compositions p2(p1(x)); base is checked separately.
    firsts = list(all_programs(pairs))
    for fam1, name1, p1 in firsts:
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
        for fam2, name2, p2 in all_programs(transformed):
            tried += 1
            if tried > MAX_CANDIDATES_PER_TASK:
                return {"fit": False, "family": None, "program": None, "p": None, "tried": tried-1, "truncated": True}
            def comp(g, p1=p1, p2=p2):
                z = safe_apply(p1, g)
                return None if z is None else safe_apply(p2, z)
            if exact_pairs(comp, pairs):
                return {"fit": True, "family": f"{fam1}->{fam2}", "program": f"{name1} THEN {name2}", "p": comp, "tried": tried, "truncated": False}
    return {"fit": False, "family": None, "program": None, "p": None, "tried": tried, "truncated": False}


def heldout_solved(p, task):
    return bool(p is not None and run_v2.v1.task_solved(p, task))


def run_dataset(train_dir, eval_dir, label, source_commit):
    # Training data are not used to choose per-task programs here. This is a pure
    # closure test: can bounded depth-2 composition enlarge the task-local DSL?
    train = run_v2.v1.load_tasks(train_dir)
    ev = run_v2.v1.load_tasks(eval_dir)
    rows = []
    base_fit = base_solved = d2_fit = d2_solved = 0
    new_fit = []
    new_solved = []
    truncated = []
    total_base = total_d2 = 0
    for tid, task in sorted(ev.items()):
        b = solve_base(task)
        total_base += b["tried"]
        bs = heldout_solved(b["p"], task)
        base_fit += int(b["fit"]); base_solved += int(bs)
        if b["fit"]:
            d = {"fit": b["fit"], "family": b["family"], "program": b["program"], "p": b["p"], "tried": 0, "truncated": False, "inherited_base": True}
        else:
            d = solve_depth2(task)
            d["inherited_base"] = False
        total_d2 += d["tried"]
        ds = heldout_solved(d["p"], task)
        d2_fit += int(d["fit"]); d2_solved += int(ds)
        if d["fit"] and not b["fit"]: new_fit.append(tid)
        if ds and not bs: new_solved.append(tid)
        if d.get("truncated"): truncated.append(tid)
        rows.append({
            "task": tid,
            "base_fit": b["fit"], "base_solved": bs, "base_family": b["family"], "base_program": b["program"], "base_tried": b["tried"],
            "depth2_fit": d["fit"], "depth2_solved": ds, "depth2_family": d["family"], "depth2_program": d["program"], "depth2_tried": d["tried"], "truncated": d.get("truncated", False)
        })
    return {
        "dataset": label,
        "source_commit": source_commit,
        "training_tasks": len(train), "evaluation_tasks": len(ev),
        "base_families": BASE,
        "depth2_boundary": {"max_candidates_per_failed_task": MAX_CANDIDATES_PER_TASK, "composition": "p2(p1(x)) with p1,p2 generated from NEW_BASE; p2 generated on transformed demonstrations"},
        "base": {"fit": base_fit, "heldout_solved": base_solved, "candidate_evaluations": total_base},
        "depth2_union_base": {"fit": d2_fit, "heldout_solved": d2_solved, "depth2_candidate_evaluations_on_base_failures": total_d2},
        "new_demonstration_fits": new_fit,
        "new_heldout_solves": new_solved,
        "truncated_tasks": truncated,
        "strict_reachability_gain": bool(new_fit),
        "strict_heldout_capability_gain": bool(new_solved),
        "rows": rows,
    }


def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: run_v4_composition.py ARC2_TRAIN ARC2_EVAL ARC1_TRAIN ARC1_EVAL")
    arc2 = run_dataset(sys.argv[1], sys.argv[2], "ARC-AGI-2", "f3283f727488ad98fe575ea6a5ac981e4a188e49")
    arc1 = run_dataset(sys.argv[3], sys.argv[4], "ARC-AGI-1", "399030444e0ab0cc8b4e199870fb20b863846f34")
    result = {
        "schema": "verified-developmental-navigation.arc-depth2-composition.v4",
        "question": "Before inventing a new representation, does bounded lawful depth-2 composition of the existing V2 language enlarge verified reach?",
        "arc_agi2": arc2,
        "arc_agi1": arc1,
    }
    out = HERE / "results_v4_composition"
    out.mkdir(exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    compact = {}
    for k in ("arc_agi2", "arc_agi1"):
        r = result[k]
        compact[k] = {x:r[x] for x in ("dataset","evaluation_tasks","base","depth2_union_base","new_demonstration_fits","new_heldout_solves","truncated_tasks","strict_reachability_gain","strict_heldout_capability_gain")}
    print(json.dumps(compact, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
