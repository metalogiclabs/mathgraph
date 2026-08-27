import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2

SENT=99
ORTH=[(-1,0),(1,0),(0,-1),(0,1)]
DIAG=[(-1,-1),(-1,1),(1,-1),(1,1)]
ALL8=ORTH+DIAG


def get(g,i,j):
    h,w=run_v2.v1.shape(g)
    return SENT if i<0 or j<0 or i>=h or j>=w else g[i][j]

def feats():
    return [
      ('center',lambda g,i,j:(g[i][j],)),
      ('center_same4',lambda g,i,j:(g[i][j],sum(get(g,i+di,j+dj)==g[i][j] for di,dj in ORTH))),
      ('center_same8',lambda g,i,j:(g[i][j],sum(get(g,i+di,j+dj)==g[i][j] for di,dj in ALL8))),
      ('cross_ordered',lambda g,i,j:(g[i][j],)+tuple(get(g,i+di,j+dj) for di,dj in ORTH)),
      ('neighbors4_multiset',lambda g,i,j:(g[i][j],)+tuple(sorted(get(g,i+di,j+dj) for di,dj in ORTH))),
      ('neighbors8_multiset',lambda g,i,j:(g[i][j],)+tuple(sorted(get(g,i+di,j+dj) for di,dj in ALL8))),
      ('patch3_ordered',lambda g,i,j:tuple(get(g,i+di,j+dj) for di in (-1,0,1) for dj in (-1,0,1))),
      ('rowcol_counts',lambda g,i,j:(g[i][j],tuple(sorted(r.count(g[i][j]) for r in g)),sum(g[r][j]==g[i][j] for r in range(len(g))))),
    ]

def infer(task,encoder):
    mapping={}
    for ex in task['train']:
        inp=tuple(map(tuple,ex['input'])); out=tuple(map(tuple,ex['output']))
        if run_v2.v1.shape(inp)!=run_v2.v1.shape(out): return None
        h,w=run_v2.v1.shape(inp)
        for i in range(h):
            for j in range(w):
                f=encoder(inp,i,j); y=out[i][j]
                if f in mapping and mapping[f]!=y: return None
                mapping[f]=y
    def p(g):
        h,w=run_v2.v1.shape(g); rows=[]
        for i in range(h):
            row=[]
            for j in range(w):
                f=encoder(g,i,j)
                row.append(mapping.get(f,g[i][j]))
            rows.append(tuple(row))
        return tuple(rows)
    pairs=run_v2.v1.task_pairs(task)
    try:
        if not run_v2.v1.exact_on_pairs(p,pairs): return None
    except Exception: return None
    return p,len(mapping)

def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v7_local_observation.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]
    feature_stats={name:{'fit':0,'solved':0} for name,_ in feats()}
    for tid,t in sorted(tasks.items()):
        chosen=None
        for pos,(name,enc) in enumerate(feats(),start=1):
            z=infer(t,enc)
            if z is None: continue
            p,nrules=z
            solved=False
            try: solved=run_v2.v1.task_solved(p,t)
            except Exception: solved=False
            feature_stats[name]['fit']+=1; feature_stats[name]['solved']+=int(solved)
            if chosen is None: chosen=(name,p,nrules,pos,solved)
        if chosen:
            name,p,nrules,pos,solved=chosen
            fits.append(tid)
            if solved: solves.append(tid)
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'chosen_feature':name,'rule_count':nrules,'feature_position':pos})
        else:
            rows.append({'task':tid,'fit':False,'heldout_solved':False,'chosen_feature':None})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-local-observation.v7',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'residual_basis':{'v4_depth2_demonstration_fits':0,'v6_same_shape_tasks':81,'v6_input_multiobject_tasks':100,'interpretation':'After bounded whole-grid composition failed, change only the observation interface: infer deterministic local cell-update rules on same-shaped demonstrations.'},
      'feature_order':[n for n,_ in feats()],
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),
      'fit_ids':fits,'heldout_solved_ids':solves,'feature_stats':feature_stats,
      'strict_reachability_gain_over_v4':bool(fits),'strict_heldout_gain_over_v4':bool(solves),
      'rows':rows,
    }
    out=HERE/'results_v7_local_observation'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
