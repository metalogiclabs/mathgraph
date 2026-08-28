import collections
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2", HERE / "run_v2.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

_original = v2.v1.infer_recolor
def safe_infer_recolor(pairs, pre=lambda x:x):
    for inp,_ in pairs:
        try: z=pre(inp)
        except Exception: return None
        if z is None: return None
    return _original(pairs, pre=pre)
v2.v1.infer_recolor=safe_infer_recolor

TARGETS=["0c786b71","59341089","833dafe3","be03b35f"]
PRIMARY_BUDGET=1000
BUDGETS=[100,250,500,1000,2500,5000]
TRAIN_DISCOVERY_BUDGET=5000
FAMS=list(v2.NEW_BASE)
PAIRS=[(a,b) for a in FAMS for b in FAMS]


def safe_apply(p,g):
    try:return p(g)
    except Exception:return None

def exact(p,pairs):
    try:return v2.v1.exact_on_pairs(p,pairs)
    except Exception:return False

def base_fit(task):
    pairs=v2.v1.task_pairs(task)
    for f in FAMS:
        for _,p in v2.programs(f,pairs):
            if exact(p,pairs): return True
    return False


def search_pairs(task,pair_order,max_candidates,require_heldout=True):
    pairs=v2.v1.task_pairs(task); tried=0
    # Cache first-stage program lists and transformed demonstrations.
    first_cache={}
    for f1,f2 in pair_order:
        if f1 not in first_cache:
            arr=[]
            for n1,p1 in v2.programs(f1,pairs):
                tp=[]; ok=True
                for i,o in pairs:
                    z=safe_apply(p1,i)
                    if z is None:ok=False;break
                    tp.append((z,o))
                if ok:arr.append((n1,p1,tp))
            first_cache[f1]=arr
        for n1,p1,tp in first_cache[f1]:
            for n2,p2 in v2.programs(f2,tp):
                tried+=1
                if tried>max_candidates:
                    return {"fit":False,"rank":None,"tried":max_candidates,"truncated":True}
                def comp(g,p1=p1,p2=p2):
                    z=safe_apply(p1,g)
                    return None if z is None else safe_apply(p2,z)
                if exact(comp,pairs):
                    solved=bool(v2.v1.task_solved(comp,task))
                    if (not require_heldout) or solved:
                        return {"fit":True,"heldout_solved":solved,"rank":tried,"tried":tried,
                                "pair":[f1,f2],"program":f"{n1} THEN {n2}","truncated":False}
    return {"fit":False,"rank":None,"tried":tried,"truncated":False}


def train_constructor_interface(train):
    # Discovery order is fixed lexicographic family-pair order. We exclude tasks
    # already representable at depth 1, so retained evidence concerns genuine
    # constructor composition rather than identity wrappers.
    global_ok=collections.Counter(); global_seen=collections.Counter()
    sig_ok=collections.defaultdict(collections.Counter); sig_seen=collections.defaultdict(collections.Counter)
    discoveries=[]; eligible=0
    for tid,t in sorted(train.items()):
        if base_fit(t):
            continue
        eligible+=1
        sig=v2.v1.signature(t)
        # One bounded developmental episode: find the first held-out-valid depth2
        # constructor under a frozen 5000-candidate boundary.
        r=search_pairs(t,PAIRS,TRAIN_DISCOVERY_BUDGET,require_heldout=True)
        for pair in PAIRS:
            global_seen[pair]+=1; sig_seen[sig][pair]+=1
        if r.get("heldout_solved"):
            pair=tuple(r["pair"])
            global_ok[pair]+=1; sig_ok[sig][pair]+=1
            discoveries.append({"task":tid,"signature":repr(sig),"pair":list(pair),"rank":r["rank"]})
    def grate(p):return (global_ok[p]+1)/(global_seen[p]+2)
    global_order=sorted(PAIRS,key=lambda p:(-grate(p),PAIRS.index(p)))
    orders={}
    for sig in sig_seen:
        def score(p):
            g=grate(p); return (sig_ok[sig][p]+4*g)/(sig_seen[sig][p]+4)
        orders[sig]=sorted(PAIRS,key=lambda p:(-score(p),global_order.index(p)))
    return global_order,orders,discoveries,eligible


def main():
    if len(sys.argv)!=3:raise SystemExit("usage run_v12_constructor_relative_pi.py TRAIN EVAL")
    train=v2.v1.load_tasks(sys.argv[1]); ev=v2.v1.load_tasks(sys.argv[2])
    if len(train)!=400 or len(ev)!=400:raise SystemExit("unexpected ARC counts")

    pair_global,pair_orders,discoveries,eligible=train_constructor_interface(train)

    # Original V11 baseline: single-step global family ordering nested by stage.
    global_fam,_,_,_,_=v2.train_router(train)
    cold_pairs=[(a,b) for a in global_fam for b in global_fam]

    def warm_order(task):return pair_orders.get(v2.v1.signature(task),pair_global)
    def sham_order(task):return list(reversed(warm_order(task)))

    rows=[]
    for tid in TARGETS:
        t=ev[tid]
        for arm,order in [
            ("WARM_CONSTRUCTOR_PI",warm_order(t)),
            ("COLD_SINGLESTEP_PRIOR",cold_pairs),
            ("GLOBAL_CONSTRUCTOR_PRIOR",pair_global),
            ("SHAM_REVERSED_CONSTRUCTOR_PI",sham_order(t)),
        ]:
            r=search_pairs(t,order,25000,require_heldout=True)
            rows.append({"task":tid,"arm":arm,**r})

    by_arm={}
    for arm in sorted({r['arm'] for r in rows}):
        rr=[r for r in rows if r['arm']==arm]
        ranks=[r['rank'] for r in rr if r.get('heldout_solved') and r.get('rank') is not None]
        by_arm[arm]={
            "heldout_solved":sum(bool(r.get('heldout_solved')) for r in rr),
            "ranks":ranks,
            "mean_rank":sum(ranks)/len(ranks) if ranks else None,
            "budget_success":{str(b):sum(bool(r.get('heldout_solved')) and r.get('rank') is not None and r['rank']<=b for r in rr) for b in BUDGETS},
        }
    primary={a:d['budget_success'][str(PRIMARY_BUDGET)] for a,d in by_arm.items()}
    strict=(primary['WARM_CONSTRUCTOR_PI']>primary['COLD_SINGLESTEP_PRIOR'] and
            primary['WARM_CONSTRUCTOR_PI']>primary['SHAM_REVERSED_CONSTRUCTOR_PI'])
    result={
        "schema":"verified-developmental-navigation.arc-constructor-relative-pi.v12",
        "source":{"repository":"fchollet/ARC-AGI","commit":"399030444e0ab0cc8b4e199870fb20b863846f34"},
        "question":"Does an interface learned over constructor futures, rather than single-step success, move K discovery inside a fixed verifier budget?",
        "training_boundary":{"base_failed_eligible_tasks":eligible,"depth2_discovery_budget":TRAIN_DISCOVERY_BUDGET,"successful_constructor_episodes":len(discoveries)},
        "frozen_targets":TARGETS,"primary_budget":PRIMARY_BUDGET,"secondary_budgets":BUDGETS,
        "by_arm":by_arm,"primary_budget_successes":primary,"strict_constructor_relative_pi_gate":strict,
        "discoveries":discoveries,"rows":rows,
    }
    out=HERE/'results_v12_constructor_relative_pi';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','discoveries')},indent=2,sort_keys=True))
    print("TRAIN_CONSTRUCTOR_EPISODES",len(discoveries),"/",eligible)
    print("STRICT_CONSTRUCTOR_RELATIVE_PI_GATE",strict)

if __name__=='__main__':main()
