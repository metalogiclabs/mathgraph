"""Adversarial qualified-lineage benchmark: independent SCC agenda versus compiler.

Same admitted graph, same update traces, canonical state and active-route oracle.
Soft deadlines are diagnostic only; Python timings are not hard WCET bounds.
"""
import argparse,csv,random,statistics,time,tracemalloc
from mathgraph_check.warrant_resolution import Claim,Receipt,Route,QualifiedRelation,resolve_graph
from mathgraph_check.qualified_consequence_closure import QualifiedConsequenceClosure
from experiments.capability_lineage_scc_agenda import SCCAgenda

def make(kind,n):
    claims=[Claim(f"c{i}","formal","s") for i in range(n)]
    receipts=[Receipt(f"e{i}","formal","s") for i in range(12)]
    routes=[Route("c0",("e0",))]
    for i in range(1,n):
        if kind=="chain":
            routes.append(Route(f"c{i}",("e1",),(f"c{i-1}",)))
        elif kind=="fanout":
            routes.append(Route(f"c{i}",("e1",),("c0",)))
        elif kind=="dense_cycle":
            routes.append(Route(f"c{i}",("e1",),(f"c{(i+1)%n}",)))
            routes.append(Route(f"c{i}",("e2",),(f"c{(i+2)%n}",)))
        elif kind in ("alternatives","qualification"):
            routes.append(Route(f"c{i}",("e1",),(f"c{i-1}",)))
            routes.append(Route(f"c{i}",("e2",)))
    relations=()
    if kind=="qualification":
        claims.append(Claim("source","documentary","external"))
        receipts.extend([Receipt("external","documentary","external"),
                         Receipt("verifier","formal","s"),
                         Receipt("qual","formal","s")])
        routes.append(Route("source",("external",)))
        br=Route(f"c{n-1}",("external",),("source",),"bridge")
        routes.append(br)
        relations=(QualifiedRelation("bridge","documentary","external","formal","s","verifier",("qual",),br),)
    return claims,receipts,routes,relations

def run(kind,n,seed,steps):
    c,e,r,relations=make(kind,n)
    rng=random.Random(seed)
    ids=["e0","e1","e2"] if kind!="qualification" else ["e0","e1","e2","verifier","qual","external"]
    seq=ids*6+[rng.choice(ids) for _ in range(max(0,steps-len(ids)*6))]
    seq=seq[:steps]
    methods={"compiled":QualifiedConsequenceClosure,"scc_agenda":SCCAgenda}
    objects={}
    peaks={}
    for name,cls in methods.items():
        tracemalloc.start()
        objects[name]=cls(c,r,e,relations=relations)
        peaks[name]=tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    times={k:[] for k in methods}
    withdrawn=set()
    for idx,key in enumerate(seq):
        live=key in withdrawn
        if live:withdrawn.remove(key)
        else:withdrawn.add(key)
        names=list(methods)
        if idx%2:names.reverse()
        for name in names:
            t=time.perf_counter_ns()
            objects[name].update(key,live)
            times[name].append((time.perf_counter_ns()-t)/1000)
        oracle=resolve_graph(c,r,e,withdrawn=frozenset(withdrawn),relations=relations)
        for name in methods:
            assert objects[name].states()==dict(oracle.states),(kind,name,idx,"states")
            assert objects[name].active_routes()==oracle.active_routes,(kind,name,idx,"routes")
    rows=[]
    for name in methods:
        a=sorted(times[name])
        rows.append(dict(graph=kind,claims=n,seed=seed,method=name,updates=len(a),
                         mean_us=round(statistics.mean(a),2),
                         p99_us=round(a[min(len(a)-1,int(.99*len(a)))],2),
                         worst_observed_us=round(a[-1],2),
                         over_1000us=sum(v>1000 for v in a),
                         over_5000us=sum(v>5000 for v in a),
                         constructor_peak_bytes=peaks[name]))
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--steps",type=int,default=100)
    a=p.parse_args()
    rows=[]
    for kind in ("chain","fanout","dense_cycle","alternatives","qualification"):
        for n in (64,256):
            for seed in (0,1):
                rows.extend(run(kind,n,seed,a.steps))
    with open(a.out,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    for row in rows:print(row)

if __name__=="__main__":main()
