"""V23: induce a representation directly from train input/output traces.

No ring/cross/carrier vocabulary is supplied. The learner extracts connected
edit components from shape-preserving training pairs, converts them into
color-equivariant local patch rewrite rules, freezes those rules, and applies
them to held-out inputs.

This is deliberately small: it tests whether the representation generator can
be moved from designer-authored object names to verifier-observed edit traces.
Public ARC evaluation data makes this a retrospective diagnostic, not protected
capability evidence.
"""
import json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v2


def shape(g): return len(g), len(g[0])

def comps(points):
    pts=set(points); out=[]
    while pts:
        s=min(pts); pts.remove(s); q=[s]; c={s}
        while q:
            i,j=q.pop()
            for di in (-1,0,1):
                for dj in (-1,0,1):
                    if di==dj==0: continue
                    p=(i+di,j+dj)
                    if p in pts:
                        pts.remove(p); c.add(p); q.append(p)
        out.append(c)
    return out


def canon_patch(inp, out, comp, pad=1):
    h,w=shape(inp)
    is_=[p[0] for p in comp]; js=[p[1] for p in comp]
    a=max(0,min(is_)-pad); b=min(h-1,max(is_)+pad)
    c=max(0,min(js)-pad); d=min(w-1,max(js)+pad)
    cmap={0:0}; nxt=1
    pin=[]; pout=[]; mask=[]
    for i in range(a,b+1):
        rin=[]; rout=[]; rm=[]
        for j in range(c,d+1):
            x=inp[i][j]
            if x not in cmap:
                cmap[x]=nxt; nxt+=1
            rin.append(cmap[x])
            y=out[i][j]
            if y==0: rout.append(0)
            elif y in cmap: rout.append(cmap[y])
            else:
                cmap[y]=nxt; nxt+=1; rout.append(cmap[y])
            rm.append((i,j) in comp)
        pin.append(tuple(rin)); pout.append(tuple(rout)); mask.append(tuple(rm))
    return {'in':tuple(pin),'out':tuple(pout),'mask':tuple(mask),'h':b-a+1,'w':d-c+1}


def learn_rules(task):
    counts=Counter(); examples={}; usable=0
    for pair in task['train']:
        x,y=pair['input'],pair['output']
        if shape(x)!=shape(y):
            continue
        usable+=1; h,w=shape(x)
        changed=[(i,j) for i in range(h) for j in range(w) if x[i][j]!=y[i][j]]
        for comp in comps(changed):
            r=canon_patch(x,y,comp)
            key=(r['in'],r['out'],r['mask'])
            counts[key]+=1; examples[key]=r
    kept=[k for k,n in counts.items() if n>=2]
    if not kept: kept=list(counts)
    rules=[examples[k] | {'support':counts[k]} for k in sorted(kept,key=lambda k:(-counts[k],str(k)))]
    return rules, usable


def match_color_equivariant(pat, grid, top, left):
    ph,pw=len(pat),len(pat[0]); h,w=shape(grid)
    if top+ph>h or left+pw>w: return None
    p2g={0:0}; g2p={0:0}
    for i in range(ph):
        for j in range(pw):
            p=pat[i][j]; g=grid[top+i][left+j]
            if p in p2g and p2g[p]!=g: return None
            if g in g2p and g2p[g]!=p: return None
            p2g[p]=g; g2p[g]=p
    return p2g


def apply_rule(z, rule):
    h,w=shape(z); ph,pw=rule['h'],rule['w']; hits=[]
    for a in range(h-ph+1):
        for b in range(w-pw+1):
            m=match_color_equivariant(rule['in'],z,a,b)
            if m is not None: hits.append((a,b,m))
    if len(hits)!=1: return False
    a,b,m=hits[0]
    for i in range(ph):
        for j in range(pw):
            if not rule['mask'][i][j]: continue
            q=rule['out'][i][j]
            z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
    return True


def program(rules):
    def f(g):
        z=[list(r) for r in g]
        for _ in range(16):
            changed=False
            for r in rules:
                before=tuple(tuple(x) for x in z)
                if apply_rule(z,r) and tuple(tuple(x) for x in z)!=before:
                    changed=True
            if not changed: break
        return tuple(tuple(r) for r in z)
    return f


def eval_task(tid,t):
    rules,usable=learn_rules(t)
    if usable!=len(t['train']) or not rules:
        return {'task':tid,'eligible':False,'usable_train_pairs':usable,'rule_count':len(rules),
                'supports':[r['support'] for r in rules],'demo_fit':False,'heldout_solved':False}
    p=program(rules)
    try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
    except Exception: fit=False
    solved=False
    try: solved=run_v2.v1.task_solved(p,t)
    except Exception: pass
    return {'task':tid,'eligible':True,'usable_train_pairs':usable,'rule_count':len(rules),
            'supports':[r['support'] for r in rules],'demo_fit':fit,'heldout_solved':solved}


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v23_trace_induced_patch.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1])
    rows=[eval_task(tid,t) for tid,t in sorted(tasks.items())]
    eligible=[r for r in rows if r['eligible']]
    fits=[r['task'] for r in rows if r['demo_fit']]
    solves=[r['task'] for r in rows if r['heldout_solved']]
    target=next(r for r in rows if r['task']=='d35bdbdc')
    result={
      'schema':'verified-developmental-navigation.arc-agi2-trace-induced-patch.v23',
      'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR',
      'meta_move':'INDUCE_REPRESENTATION_FROM_VERIFIER_EDIT_TRACES',
      'generator':'connected edit components -> padded local patches -> color-equivariant rewrite templates; repeated templates preferred; unique-match application',
      'designer_object_vocabulary':[],
      'task_count':len(rows),'eligible_shape_preserving_tasks':len(eligible),
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),
      'fit_ids':fits,'heldout_solved_ids':solves,'target':target,
      'source_distinct_solved_ids':[x for x in solves if x!='d35bdbdc'],
      'claim_boundary':'Rules are induced only from each task training input/output traces. V23 is defined only for tasks whose train pairs preserve grid shape. The ARC evaluation corpus is public and this lineage has inspected held-out outputs, so treat results as retrospective mechanism evidence only.',
      'next_gate':'If this yields source-distinct solves, freeze the generator and transfer it unchanged. If not, classify failure into edit decomposition, equivariant matching, or rewrite composition before introducing any new object vocabulary.',
      'rows':rows}
    out=HERE/'results_v23_trace_induced_patch'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
