"""V51: derive residual-guided separator discovery from the relational core.

Finite exhaustive theorem-census on all binary continuation tables P : X×C -> {0,1}
with |X|=3, |C|=3.

Start from B = ∅. Let E_B identify states agreeing on all retained continuations B;
let E_* = E_C be the full protected continuation equivalence.

A live residual is any pair (x,y) with E_B(x,y) but not E_*(x,y).
A lawful repair chooses ANY continuation c that separates that residual and adds c to B.

We exhaust every table and every possible lawful repair path. We test:
1. progress: every repair strictly refines E_B;
2. safety: no repair separates an E_*-equivalent pair (automatic because c∈C);
3. termination: every maximal repair path reaches E_* in at most |C| additions;
4. path independence of endpoint: all lawful paths end at E_*;
5. non-minimality: residual-guided lawful repair need not find a minimum-cardinality basis;
6. necessity of witness access: if E_B != E_* then at least one residual and separator exist.

This is intentionally an oracle theorem about the update law, not yet an algorithm for
finding residuals without protected feedback. That boundary is reported explicitly.
"""
import itertools, json
from pathlib import Path

N=3; M=3
OUT=Path(__file__).resolve().parent/'results_v51_residual_guided_basis_discovery'
PAIRS=[(i,j) for i in range(N) for j in range(i+1,N)]
ALL_B=[frozenset(i for i in range(M) if mask&(1<<i)) for mask in range(1<<M)]

def eqrel(table,B,x,y):
    return all(table[x][c]==table[y][c] for c in B)

def same_rel(table,B1,B2):
    return all(eqrel(table,B1,x,y)==eqrel(table,B2,x,y) for x,y in PAIRS)

def residuals(table,B):
    C=frozenset(range(M))
    return [(x,y) for x,y in PAIRS if eqrel(table,B,x,y) and not eqrel(table,C,x,y)]

def separators(table,x,y,B):
    return [c for c in range(M) if c not in B and table[x][c]!=table[y][c]]

def min_basis_size(table):
    C=frozenset(range(M))
    return min(len(B) for B in ALL_B if same_rel(table,B,C))

def explore(table,B,path,terminal_paths,failures):
    C=frozenset(range(M))
    rs=residuals(table,B)
    if not rs:
        if not same_rel(table,B,C): failures.append(('no_residual_but_not_target',table,B,path))
        terminal_paths.append(path)
        return
    # Exhaust every residual choice and every separator choice.
    for x,y in rs:
        seps=separators(table,x,y,B)
        if not seps:
            failures.append(('residual_without_separator',table,B,(x,y),path)); return
        for c in seps:
            B2=frozenset(set(B)|{c})
            # Strict progress: the chosen residual is merged before and split after.
            if not eqrel(table,B,x,y) or eqrel(table,B2,x,y):
                failures.append(('no_strict_progress',table,B,(x,y),c)); return
            # Safety: target-equivalent pairs must remain equivalent after any c in C.
            for a,b in PAIRS:
                if eqrel(table,C,a,b) and not eqrel(table,B2,a,b):
                    failures.append(('unsafe_split',table,B2,(a,b),c)); return
            if len(path)+1 > M:
                failures.append(('too_long',table,path+[c])); return
            explore(table,B2,path+[c],terminal_paths,failures)
            if failures:return

def main():
    failures=[]; tables=0; paths=0; max_steps=0; nonminimal_tables=0; multi_endpoint_tables=0
    path_len_hist={}; min_basis_hist={}; worst_gap=0; example_nonminimal=None
    for bits in itertools.product((0,1), repeat=N*M):
        table=tuple(tuple(bits[x*M+c] for c in range(M)) for x in range(N)); tables+=1
        terminals=[]
        explore(table,frozenset(),[],terminals,failures)
        if failures:break
        paths += len(terminals)
        lens=[len(p) for p in terminals]
        for k in lens:path_len_hist[k]=path_len_hist.get(k,0)+1
        max_steps=max(max_steps,max(lens,default=0))
        kmin=min_basis_size(table); min_basis_hist[kmin]=min_basis_hist.get(kmin,0)+1
        if any(k>kmin for k in lens):
            nonminimal_tables+=1
            gap=max(lens)-kmin; worst_gap=max(worst_gap,gap)
            if example_nonminimal is None:
                example_nonminimal={'table':table,'minimum_basis_size':kmin,'path_lengths':sorted(set(lens))}
        # Endpoint is relation, not literal B. All terminals must induce E_C.
        endrels={tuple(eqrel(table,frozenset(p),x,y) for x,y in PAIRS) for p in terminals}
        if len(endrels)>1:multi_endpoint_tables+=1
    result={
      'schema':'verified-developmental-navigation.residual-guided-basis-discovery.v51',
      'all_checks_pass':not failures,'failures':failures,'tables_tested':tables,
      'lawful_terminal_paths_tested':paths,'max_repair_steps':max_steps,
      'path_length_hist':path_len_hist,'minimum_basis_size_hist':min_basis_hist,
      'tables_with_nonminimum_lawful_paths':nonminimal_tables,'worst_extra_probes_over_minimum':worst_gap,
      'tables_with_multiple_extensional_endpoints':multi_endpoint_tables,
      'example_nonminimal':example_nonminimal,
      'mathematical_core':(
        'For a fixed finite protected continuation family C, if a controller is supplied a live residual '
        '(a pair currently merged but separated by the full protected relation) and adds any available '
        'continuation that separates that residual, then each step is safe and strictly progressive, every '
        'lawful path terminates after at most |C| additions, and every endpoint induces the same full protected '
        'equivalence E_C. This does not imply minimum-cardinality discovery, and it assumes access to protected '
        'residual feedback; discovering informative residuals without such feedback remains a separate problem.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
