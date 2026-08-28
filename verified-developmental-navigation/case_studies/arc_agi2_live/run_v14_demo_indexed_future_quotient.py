import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v13',HERE/'run_v13_groundup_future_quotient.py')
v13=importlib.util.module_from_spec(spec);spec.loader.exec_module(v13)

# V14 is the smallest extension licensed by V13 exhaustion:
# same raw first-stage states, same continuation language, same verifier, same
# primitive predicates. The ONLY change is retaining the predicate pattern for
# each demonstration instead of collapsing it with all(...).

def demo_indexed_obs(tp):
    out={}
    for di,(x,y) in enumerate(tp):
        hx,wx=v13.shape(x);hy,wy=v13.shape(y)
        cx,cy=v13.colors(x),v13.colors(y)
        ax=max(1,hx*wx);ay=max(1,hy*wy)
        row={
            'h_eq':hx==hy,'w_eq':wx==wy,'shape_eq':(hx,wx)==(hy,wy),
            'shape_swap':(hx,wx)==(wy,hy),
            'h_le':hx<=hy,'w_le':wx<=wy,'h_ge':hx>=hy,'w_ge':wx>=wy,
            'area_eq':ax==ay,'area_divides':(max(ax,ay)%min(ax,ay)==0),
            'colors_eq':cx==cy,'xcolors_subset':cx<=cy,'ycolors_subset':cy<=cx,
            'ncolors_eq':len(cx)==len(cy),
            'height_parity_eq':(hx%2)==(hy%2),'width_parity_eq':(wx%2)==(wy%2),
        }
        for k,v in row.items():out[f'd{di}:{k}']=v
    return out

def states_for(task):
    states=v13.first_stage_states(task)
    for s in states:s['obs']=demo_indexed_obs(s['tp'])
    return states

def minimal_basis(states,label,max_k=6):
    keys=sorted(states[0]['obs']) if states else []
    def sufficient(sub):
        b=defaultdict(set)
        for s in states:b[tuple(s['obs'][k] for k in sub)].add(bool(s[label]))
        return all(len(v)==1 for v in b.values())
    if sufficient(()):return []
    for k in range(1,min(max_k,len(keys))+1):
        for sub in itertools.combinations(keys,k):
            if sufficient(sub):return list(sub)
    return None

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v14_demo_indexed_future_quotient.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in v13.TARGETS:
        t=ev[tid];states=states_for(t)
        for s in states:
            df,hs,w,tr,trunc=v13.future_audit(t,s)
            s['demo_future_success']=df;s['heldout_success']=hs;s['witness']=w;s['truncated']=trunc
        bd=minimal_basis(states,'demo_future_success')
        bh=minimal_basis(states,'heldout_success')
        rows.append({
            'task':tid,'states':len(states),
            'demo_future_positive':sum(s['demo_future_success'] for s in states),
            'heldout_future_positive':sum(s['heldout_success'] for s in states),
            'minimal_demo_indexed_basis':bd,
            'minimal_heldout_indexed_basis':bh,
            'any_truncation':any(s['truncated'] for s in states),
        })
    result={
      'schema':'verified-developmental-navigation.arc-demo-indexed-future-quotient.v14',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'frozen_targets':v13.TARGETS,
      'licensed_by':'V13 exhausted every <=5 subset of the aggregated low-level vocabulary on each protected task, and no common <=6 basis existed.',
      'change_from_v13':'Retain the same primitive predicate separately per demonstration; add no new predicate type or constructor label.',
      'tasks':rows,
      'decision':'DEMO_PATTERN_SUFFICIENT' if all(r['minimal_demo_indexed_basis'] is not None for r in rows) else 'DEMO_PATTERN_EXHAUSTED_ON_AT_LEAST_ONE_TASK'
    }
    out=HERE/'results_v14_demo_indexed_future_quotient';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
