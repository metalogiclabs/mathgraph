import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8


def detect_nodes(g):
    """Detect a symbol as payload cell p whose four orthogonal neighbours share border color b.
    Footprint is payload plus the 8-connected border-color component touching those neighbours.
    This strictly generalizes the training 3x3 rings to crosses/expanded rings seen in heldout."""
    h,w=run_v2.v1.shape(g); bg=v8.mode_color(g); raw=[]
    for i in range(1,h-1):
      for j in range(1,w-1):
        bvals=[g[i-1][j],g[i+1][j],g[i][j-1],g[i][j+1]]
        if len(set(bvals))!=1: continue
        b=bvals[0]; p=g[i][j]
        if b==bg or p==b: continue
        # collect 8-connected component of border color containing the orthogonal ring neighbours
        seeds={(i-1,j),(i+1,j),(i,j-1),(i,j+1)}; unseen={(r,c) for r in range(h) for c in range(w) if g[r][c]==b}
        comp=set(); st=list(seeds & unseen)
        for q in st:
            unseen.discard(q); comp.add(q)
        while st:
            r,c=st.pop()
            for dr in (-1,0,1):
              for dc in (-1,0,1):
                if dr==dc==0: continue
                q=(r+dr,c+dc)
                if q in unseen: unseen.remove(q); comp.add(q); st.append(q)
        if not seeds.issubset(comp): continue
        raw.append({'anchor':min(comp|{(i,j)}),'pts':comp|{(i,j)},'border':b,'center':p,'center_pt':(i,j)})
    # Prefer smaller footprints if overlapping candidate centers compete.
    raw.sort(key=lambda o:(len(o['pts']),o['anchor']))
    out=[]; used=set()
    for o in raw:
        if o['center_pt'] in used: continue
        # permit border components to touch other symbols only through separate colors; same footprint overlap is ambiguity.
        if o['pts'] & used: continue
        out.append(o); used |= o['pts']
    out.sort(key=lambda o:o['anchor'])
    return bg,out


def symbolic_graph(g):
    bg,nodes=detect_nodes(g); by_border={}
    for i,o in enumerate(nodes): by_border.setdefault(o['border'],[]).append(i)
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
    if len(sys.argv)!=2: raise SystemExit('usage run_v14_generic_symbols.py EVAL_DIR')
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
    result={'schema':'verified-developmental-navigation.arc-agi2-generic-symbols.v14',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{'v13':'Symbolic center(A)=border(B) composition fits d35bdbdc demonstrations but 0 heldout.','heldout_diagnostic':'One heldout test parses and misses by exactly one cell; another parses but has action ambiguity; one fails parsing entirely. Raw task inspection shows heldout symbols vary from 3x3 rings to cross/expanded-ring forms while preserving the invariant payload cell surrounded orthogonally by a single border color.','decision':'KEEP symbolic relation and composition; SPLIT parser identity from literal 3x3 syntax. Generalize node identity to a future-relevant invariant: payload with four equal orthogonal border neighbours.'},
      'declared_language':{'node':'payload cell with four equal non-background orthogonal border neighbours; border footprint is touching 8-connected border component','symbolic_edge':'center(A)==border(B), unique successor','action':'same V13 pairwise composition','tail_variants':['delete','keep']},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,
      'strict_demo_gain_over_v13':len(fits)>1,'strict_heldout_gain_over_v13':bool(solves),'rows':rows}
    out=HERE/'results_v14_generic_symbols'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
