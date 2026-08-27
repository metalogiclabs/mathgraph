import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v2

# Three literal macros extracted from the four strict held-out gains in V4.
# They are frozen here: no task-specific parameters are fit.
def hcat(a,b):
    if a is None or b is None or len(a) != len(b): return None
    return tuple(tuple(x for x in ra)+tuple(x for x in rb) for ra,rb in zip(a,b))

def vcat(a,b):
    if a is None or b is None: return None
    if a and b and len(a[0]) != len(b[0]): return None
    return tuple(a)+tuple(b)

def macro_quad_sym(g):
    # V4 schema: concat:h_rl:flip_h THEN concat:v_bt:rot180
    z = hcat(run_v2.v1.flip_h(g), g)
    return None if z is None else vcat(run_v2.v1.rot180(z), z)

def macro_double_mirror(g):
    # V4 schema: concat:h_rl:flip_h THEN tile_grid:1x2
    z = hcat(run_v2.v1.flip_h(g), g)
    return None if z is None else tuple(tuple(x for _ in range(2) for x in r) for r in z)

def macro_rot90_first_tile(g):
    # V4 schema: geom:rot90 THEN separator_tile:0
    z = run_v2.v1.rot90(g)
    ts = run_v2.split_tiles(z)
    return ts[0] if ts else None

MACROS = [
    ("quad_sym", macro_quad_sym),
    ("double_mirror", macro_double_mirror),
    ("rot90_first_tile", macro_rot90_first_tile),
]

DISCOVERY = {
    "quad_sym": ["0c786b71", "833dafe3"],
    "double_mirror": ["59341089"],
    "rot90_first_tile": ["be03b35f"],
}


def safe_exact(p, pairs):
    try: return run_v2.v1.exact_on_pairs(p, pairs)
    except Exception: return False

def safe_solved(p, task):
    try: return run_v2.v1.task_solved(p, task)
    except Exception: return False


def scan(tasks):
    rows=[]; fit_ids={n:[] for n,_ in MACROS}; solved_ids={n:[] for n,_ in MACROS}
    for tid,task in sorted(tasks.items()):
        pairs=run_v2.v1.task_pairs(task)
        for idx,(name,p) in enumerate(MACROS, start=1):
            fit=safe_exact(p,pairs)
            solved=bool(fit and safe_solved(p,task))
            if fit: fit_ids[name].append(tid)
            if solved: solved_ids[name].append(tid)
            rows.append({"task":tid,"macro":name,"candidate_position":idx,"demonstration_fit":fit,"heldout_solved":solved})
    return {"fit_ids":fit_ids,"solved_ids":solved_ids,"rows":rows}


def main():
    if len(sys.argv)!=5:
        raise SystemExit("usage: run_v5_retention.py ARC2_TRAIN ARC2_EVAL ARC1_TRAIN ARC1_EVAL")
    datasets={
      "arc2_train":run_v2.v1.load_tasks(sys.argv[1]),
      "arc2_eval":run_v2.v1.load_tasks(sys.argv[2]),
      "arc1_train":run_v2.v1.load_tasks(sys.argv[3]),
      "arc1_eval":run_v2.v1.load_tasks(sys.argv[4]),
    }
    scans={k:scan(v) for k,v in datasets.items()}
    # The repeated V4 macro is the cleanest retained-capability witness:
    # after discovery on 0c786b71, 833dafe3 needs one macro verification instead
    # of 4769 depth-2 candidate verifications in V4.
    transfer_target="833dafe3"
    target_row=next(r for r in scans["arc1_eval"]["rows"] if r["task"]==transfer_target and r["macro"]=="quad_sym")
    result={
      "schema":"verified-developmental-navigation.arc-retained-macros.v5",
      "source_v4":{"run_id":33038153009,"artifact_id":9632884567},
      "frozen_macros":[n for n,_ in MACROS],
      "discovery_tasks_from_v4":DISCOVERY,
      "retrospective_reuse_witness":{
        "source_task":"0c786b71","retained_macro":"quad_sym","transfer_task":transfer_target,
        "transfer_demonstration_fit":target_row["demonstration_fit"],"transfer_heldout_solved":target_row["heldout_solved"],
        "cold_depth2_candidate_verifications_v4":4769,"warm_retained_macro_verifications":1,
        "verification_reduction":4769.0 if target_row["heldout_solved"] else None
      },
      "datasets":{k:{"tasks":len(datasets[k]),"fit_ids":scans[k]["fit_ids"],"solved_ids":scans[k]["solved_ids"]} for k in datasets},
      "new_transfer_outside_v4_discovery":{},
    }
    discovery_all=set(sum(DISCOVERY.values(),[]))
    for ds in datasets:
        extras={}
        for name,_ in MACROS:
            extras[name]=[t for t in scans[ds]["solved_ids"][name] if t not in discovery_all]
        result["new_transfer_outside_v4_discovery"][ds]=extras
    out=HERE/'results_v5_retention'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
