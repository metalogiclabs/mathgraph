import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v12_scene_graph as v12


def symbolic_graph(g):
    bg,nodes=v12.detect_nodes(g)
    by_border=collections.defaultdict(list)
    for i,o in enumerate(nodes): by_border[o['border']].append(i)
    succ={}; indeg=[0]*len(nodes)
    for i,o in enumerate(nodes):
        q=by_border.get(o['center'],[])
        if len(q)==1 and q[0]!=i:
            succ[i]=q[0]; indeg[q[0]]+=1
    roots=[i for i,d in enumerate(indeg) if d==0]
    return bg,nodes,succ,indeg,roots


def chains(g):
    bg,nodes,succ,indeg,roots=symbolic_graph(g)
    if len(nodes)<2:return None
    seen=set(); out=[]
    for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
        ch=[]; cur=r
        while cur not in seen:
            seen.add(cur); ch.append(cur)
            if cur not in succ: break
            cur=succ[cur]
        out.append(ch)
    # This operator is only admitted when the color relation decomposes the entire glyph set into acyclic chains.
    if len(seen)!=len(nodes): return None
    return bg,nodes,out


def program(tail_policy='delete'):
    def f(g):
        q=chains(g)
        if q is None:return None
        bg,nodes,chs=q; out=[list(r) for r in g]
        for ch in chs:
            k=0
            while k<len(ch):
                a=ch[k]
                if k+1<len(ch):
                    b=ch[k+1]
                    # Compose key->mid and mid->value into key->value.
                    ci,cj=nodes[a]['center_pt']; out[ci][cj]=nodes[b]['center']
                    for i,j in nodes[b]['pts']: out[i][j]=bg
                    k+=2
                else:
                    if tail_policy=='delete':
                        for i,j in nodes[a]['pts']: out[i][j]=bg
                    k+=1
        return tuple(tuple(r) for r in out)
    return f


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v13_symbolic_composition.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; total=0
    variants=[('delete_tail',program('delete')),('keep_tail',program('keep'))]
    for tid,t in sorted(tasks.items()):
        found=None; tried=0
        for name,p in variants:
            tried+=1; total+=1
            try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
            except Exception: fit=False
            if fit:
                try: solved=run_v2.v1.task_solved(p,t)
                except Exception: solved=False
                found=(name,solved); break
        if found:
            name,solved=found; fits.append(tid)
            if solved: solves.append(tid)
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else: rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-symbolic-composition.v13',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{
        'v12_result':'Spatial scene graph: 130,368 candidates, 0 demonstration fits.',
        'diagnostic':'For d35bdbdc, every changed cell in all three training examples lies inside detected 3x3 glyphs. Spatial path edges do not explain the edits. The glyphs themselves encode a symbolic graph: border color is a key and center color is its successor key.',
        'derived_law':'If glyphs encode a->b and b->c, replace the first by a->c and delete the second. Traverse each root chain in adjacent pairs; delete an unpaired tail.',
        'decision':'REORGANIZE RELATION: replace spatial adjacency with verifier-supported symbolic equality center(A)=border(B). This is a relation-language change, not deeper search.'
      },
      'declared_language':{'node':'3x3 uniform-border glyph with center payload','symbolic_edge':'center(A) == border(B), unique successor','chain_start':'indegree zero','action':'pairwise function composition','tail_variants':['delete','keep']},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,
      'strict_reachability_gain_over_v12':bool(fits),'strict_heldout_gain_over_v12':bool(solves),'rows':rows,
    }
    out=HERE/'results_v13_symbolic_composition'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
