import importlib.util
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2", HERE / "run_v2.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

# Preserve the v2 guard for partial structural programs.
_original = v2.v1.infer_recolor

def safe_infer_recolor(pairs, pre=lambda x: x):
    for inp, _ in pairs:
        try:
            x = pre(inp)
        except Exception:
            return None
        if x is None:
            return None
    return _original(pairs, pre=pre)

v2.v1.infer_recolor = safe_infer_recolor


def summary(rows):
    c=[r["candidate_evaluations"] for r in rows]
    return {"tasks":len(rows),"solved":sum(r["solved"] for r in rows),"fit_found":sum(r["fit_found"] for r in rows),"total_candidate_evaluations":sum(c),"mean_candidate_evaluations":sum(c)/len(c),"median_candidate_evaluations":statistics.median(c),"extension_used":sum(r["extension_used"] for r in rows),"extension_solved":sum(r["extension_used"] and r["solved"] for r in rows)}


def main():
    if len(sys.argv)!=3: raise SystemExit("usage run_v3_arc1.py TRAIN_DIR EVAL_DIR")
    train=v2.v1.load_tasks(sys.argv[1]); ev=v2.v1.load_tasks(sys.argv[2])
    if len(train)!=400 or len(ev)!=400:
        raise SystemExit(f"unexpected ARC-AGI-1 counts train={len(train)} eval={len(ev)}")
    order,orders,gok,gseen,train_solved=v2.train_router(train)
    G=v2.arm(ev,lambda t:order,False)
    V=v2.arm(ev,lambda t:orders.get(v2.v1.signature(t),order),False)
    E=v2.arm(ev,lambda t:orders.get(v2.v1.signature(t),order),True)
    gb={r['task']:r for r in G}; vb={r['task']:r for r in V}; eb={r['task']:r for r in E}
    common=[t for t in gb if gb[t]['solved'] and vb[t]['solved']]
    cg=sum(gb[t]['candidate_evaluations'] for t in common); cv=sum(vb[t]['candidate_evaluations'] for t in common)
    new=[t for t in eb if eb[t]['solved'] and not vb[t]['solved']]
    lost=[t for t in eb if vb[t]['solved'] and not eb[t]['solved']]
    SG,SV,SE=summary(G),summary(V),summary(E)
    result={
      "schema":"verified-developmental-navigation.arc-agi1-transfer.v3",
      "source":{"repository":"fchollet/ARC-AGI","commit":"399030444e0ab0cc8b4e199870fb20b863846f34","training_tasks":len(train),"evaluation_tasks":len(ev)},
      "reason_for_transfer":"ARC-AGI-2 V1/V2 had zero demonstration-consistent candidates on 120 public evaluation tasks, making routing comparison vacuous.",
      "base_families":v2.NEW_BASE,"extension_family":v2.EXTENSION,"global_learned_order":order,"signature_count":len(orders),
      "training_family_exact_solve_counts":gok,"training_solved_task_ids":train_solved,
      "global":SG,"vdn_base":SV,"vdn_with_extension":SE,
      "common_solved":{"count":len(common),"global_total_candidate_evaluations":cg,"vdn_total_candidate_evaluations":cv,"ratio_global_over_vdn":cg/cv if cv else None},
      "newly_solved_by_extension":new,"lost_by_extension":lost,
      "navigation_advantage":SV['solved']>=SG['solved'] and cv<cg,
      "developmental_phase_change":bool(new) and not lost,
      "rows":{"global":G,"vdn_base":V,"vdn_with_extension":E}
    }
    out=HERE/'results_v3_arc1'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','training_solved_task_ids')},indent=2,sort_keys=True))
    print('NAVIGATION_ADVANTAGE',result['navigation_advantage'])
    print('DEVELOPMENTAL_PHASE_CHANGE',result['developmental_phase_change'])

if __name__=='__main__': main()
