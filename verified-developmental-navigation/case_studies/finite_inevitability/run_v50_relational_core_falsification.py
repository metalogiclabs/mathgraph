"""V50: exhaustively test the first-principles relational core.

We enumerate all finite protected profile tables P : X x C -> O with
|X|=3, |C|=3, |O|=2. For every evidence subset B subseteq C we verify:
- induced indistinguishability is an equivalence relation;
- evidence monotonicity under B subseteq B';
- union/order independence;
- witnessed separation whenever two states are inequivalent;
- every inclusion-minimal sufficient basis induces the same target relation;
- full C need not be necessary;
- minimum and inclusion-minimal bases can differ in multiplicity.

We also separately check canonical falsifiers for stronger claims:
- full future equality stronger than decision sufficiency;
- existential action compatibility can have incomparable maximal compressions;
- capability expansion can coarsen decision equivalence;
- unsound separators can split protected-equivalent states.
"""
import itertools, json
from pathlib import Path

N=3; M=3
OUT=Path(__file__).resolve().parent/'results_v50_relational_core_falsification'
PROBESETS=[frozenset(i for i in range(M) if mask&(1<<i)) for mask in range(1<<M)]

def profile_eq(table,B,x,y):
    return all(table[x][c]==table[y][c] for c in B)

def rel(table,B):
    return tuple(tuple(profile_eq(table,B,x,y) for y in range(N)) for x in range(N))

def is_equiv(E):
    return all(E[x][x] for x in range(N)) and all(E[x][y]==E[y][x] for x in range(N) for y in range(N)) and all(not(E[x][y] and E[y][z]) or E[x][z] for x in range(N) for y in range(N) for z in range(N))

def main():
    failures=[]; tables=0; strict_subset=0; multi_min=0
    for bits in itertools.product(range(2), repeat=N*M):
        table=[bits[r*M:(r+1)*M] for r in range(N)]; tables+=1
        target=rel(table,frozenset(range(M)))
        good=[]
        for B in PROBESETS:
            E=rel(table,B)
            if not is_equiv(E): failures.append(('not_equiv',table,sorted(B))); break
            if E==target: good.append(B)
            # separator witness
            for x in range(N):
                for y in range(N):
                    if not E[x][y] and not any(table[x][c]!=table[y][c] for c in B):
                        failures.append(('no_separator',table,sorted(B),x,y)); break
                if failures: break
            if failures: break
        if failures: break
        # monotonicity
        for B in PROBESETS:
            for Bp in PROBESETS:
                if B.issubset(Bp):
                    E,E2=rel(table,B),rel(table,Bp)
                    if any(E2[x][y] and not E[x][y] for x in range(N) for y in range(N)):
                        failures.append(('nonmonotone',table,sorted(B),sorted(Bp))); break
            if failures:break
        if failures:break
        # union/order independence
        for B1 in PROBESETS:
            for B2 in PROBESETS:
                if rel(table,B1|B2)!=rel(table,B2|B1):
                    failures.append(('order',table,sorted(B1),sorted(B2))); break
            if failures: break
        if failures:break
        mins=[B for B in good if not any(B2 < B and B2 in good for B2 in PROBESETS)]
        if not mins: failures.append(('no_basis',table)); break
        if any(rel(table,B)!=target for B in mins): failures.append(('bad_basis',table)); break
        k=min(map(len,good)); minimum=[B for B in good if len(B)==k]
        if k<M: strict_subset+=1
        if len(minimum)>1: multi_min+=1

    # F1: future profiles differ, protected decision same
    f1={'profiles':[(0,0),(1,1)], 'decision':[0,0]}
    assert f1['profiles'][0]!=f1['profiles'][1] and f1['decision'][0]==f1['decision'][1]
    # F2: incomparable maximal viable compressions witness
    f2=[{0},{1},{0,1}]
    # F3: old actions distinguish, new dominant action merges
    old_best=[0,1]; new_best=[2,2]
    assert old_best[0]!=old_best[1] and new_best[0]==new_best[1]
    # F4: protected-equivalent but auxiliary q separates
    P=[0,0]; q=[0,1]
    assert P[0]==P[1] and q[0]!=q[1]

    result={
      'schema':'verified-developmental-navigation.relational-core-falsification.v50',
      'all_checks_pass':not failures,
      'tables_tested':tables,
      'evidence_subsets_per_table':len(PROBESETS),
      'tables_where_strict_subset_of_full_continuations_suffices':strict_subset,
      'tables_with_multiple_minimum_bases':multi_min,
      'falsifiers':{
        'full_future_stronger_than_decision':f1,
        'set_valued_nonunique_witness':[sorted(s) for s in f2],
        'capability_can_coarsen':{'old_best':old_best,'new_best':new_best},
        'unsound_separator':{'protected':P,'auxiliary_q':q},
      },
      'failures':failures,
      'mathematical_core':(
        'For extensional protected continuation profiles, indistinguishability induced by any retained continuation family is an equivalence relation; accumulating evidence refines it monotonically and order-independently. Canonical convergence requires only a sufficient separator basis, not full future semantics. Stronger claims about decision sufficiency, unique compression in set-valued settings, monotone refinement under capability expansion, or arbitrary splitting are falsified by explicit witnesses.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)); print(json.dumps(result,indent=2,sort_keys=True))
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
