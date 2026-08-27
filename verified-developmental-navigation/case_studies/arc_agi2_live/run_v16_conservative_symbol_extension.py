import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13
import run_v15_local_symbol_quotient as v15


def detect_nodes(g):
    """Conservative parser extension.
    1. Preserve every literal V13 3x3 glyph exactly.
    2. Add a V15 local-symbol candidate only when its payload and footprint do not
       overlap an already admitted literal glyph.
    Thus the old parser is embedded rather than replaced."""
    bg,base=v13.v12.detect_nodes(g)
    _,extra=v15.detect_nodes(g)
    used=set().union(*(o['pts'] for o in base)) if base else set()
    centers={o['center_pt'] for o in base}
    out=[dict(o) for o in base]
    for o in extra:
        if o['center_pt'] in centers: continue
        if o['pts'] & used: continue
        out.append(dict(o)); used |= o['pts']; centers.add(o['center_pt'])
    out.sort(key=lambda o:o['anchor'])
    return bg,out


def graph(g):
    bg,nodes=detect_nodes(g); by={}
    for i,o in enumerate(nodes): by.setdefault(o['border'],[]).append(i)
    succ={}; indeg=[0]*len(nodes)
    for i,o in enumerate(nodes):
        q=by.get(o['center'],[])
        if len(q)==1 and q[0]!=i: succ[i]=q[0]; indeg[q[0]]+=1
    roots=[i for i,d in enumerate(indeg) if d==0]
    return bg,nodes,succ,indeg,roots


def chains(g):
    bg,nodes,succ,indeg,roots=graph(g)
    if len(nodes)<2:return None
    seen=set(); out=[]
    for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
        ch=[]; cur=r
        while cur not in seen:
            seen.add(cur); ch.append(cur)
            if cur not in succ: break
            cur=succ[cur]
        out.append(ch)
    if len(seen)!=len(nodes): return None
    return bg,nodes,out


def program(tail='delete'):
    def f(g):
        q=chains(g)
        if q is None:return None
        bg,nodes,chs=q;out=[list(r) for r in g]
        for ch in chs:
            k=0
            while k<len(ch):
                a=ch[k]
                if k+1<len(ch):
                    b=ch[k+1];ci,cj=nodes[a]['center_pt'];out[ci][cj]=nodes[b]['center']
                    for i,j in nodes[b]['pts']:out[i][j]=bg
                    k+=2
                else:
                    if tail=='delete':
                        for i,j in nodes[a]['pts']:out[i][j]=bg
                    k+=1
        return tuple(tuple(r) for r in out)
    return f


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v16_conservative_symbol_extension.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); fits=[];solves=[];rows=[];total=0
    variants=[('delete_tail',program('delete')),('keep_tail',program('keep'))]
    for tid,t in sorted(tasks.items()):
        found=None;tried=0
        for name,p in variants:
            tried+=1;total+=1
            try:fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
            except Exception:fit=False
            if fit:
                try:solved=run_v2.v1.task_solved(p,t)
                except Exception:solved=False
                found=(name,solved);break
        if found:
            name,solved=found;fits.append(tid)
            if solved:solves.append(tid)
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else: rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={'schema':'verified-developmental-navigation.arc-agi2-conservative-symbol-extension.v16',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{
        'v13':'Literal 3x3 parser + symbolic composition gives 1 demonstration fit, 0 heldout.',
        'v14_v15':'Replacing node identity with broader parsers destroys the known demonstration capability (1->0).',
        'meta_residual':'The loop violated its own conservative-extension law: representation expansion replaced an admitted parser instead of embedding it.',
        'repair':'EXTEND, do not replace. Preserve all V13 nodes exactly and admit only non-overlapping extra local-symbol nodes. Keep relation and action frozen.',
        'success_condition':'At minimum retain d35bdbdc demonstration fit; any heldout gain then isolates value of conservative parser extension.'
      },
      'declared_language':{'base_parser':'V13 literal 3x3 glyph','extension_parser':'V15 local payload+orthogonal surround','admission':'extra node must not overlap any base glyph','edge':'center(A)==border(B), unique successor','action':'V13 pairwise composition','tail':['delete','keep']},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,
      'retains_v13_demo_capability':'d35bdbdc' in fits,'strict_heldout_gain_over_v13':bool(solves),'rows':rows}
    out=HERE/'results_v16_conservative_symbol_extension';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
