import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8


def detect_nodes(g):
    """Future-relevant local symbol quotient.
    Payload p has four equal non-background orthogonal neighbours b.
    Footprint is only the local 3x3 neighbourhood cells equal to b plus p,
    avoiding V14's false merge of a symbol border with distant same-color structure."""
    h,w=run_v2.v1.shape(g); bg=v8.mode_color(g); raw=[]
    for i in range(1,h-1):
      for j in range(1,w-1):
        ortho=[g[i-1][j],g[i+1][j],g[i][j-1],g[i][j+1]]
        if len(set(ortho))!=1: continue
        b=ortho[0]; p=g[i][j]
        if b==bg or p==b: continue
        pts={(i,j)} | {(r,c) for r in range(i-1,i+2) for c in range(j-1,j+2) if g[r][c]==b}
        raw.append({'anchor':min(pts),'pts':pts,'border':b,'center':p,'center_pt':(i,j)})
    raw.sort(key=lambda o:(o['anchor'],len(o['pts'])))
    out=[]; centers=set()
    for o in raw:
        if o['center_pt'] not in centers:
            out.append(o); centers.add(o['center_pt'])
    return bg,out


def graph(g):
    bg,nodes=detect_nodes(g); by={}
    for i,o in enumerate(nodes):by.setdefault(o['border'],[]).append(i)
    succ={}; indeg=[0]*len(nodes)
    for i,o in enumerate(nodes):
        q=by.get(o['center'],[])
        if len(q)==1 and q[0]!=i:succ[i]=q[0];indeg[q[0]]+=1
    roots=[i for i,d in enumerate(indeg) if d==0]
    return bg,nodes,succ,indeg,roots


def chains(g):
    bg,nodes,succ,indeg,roots=graph(g)
    if len(nodes)<2:return None
    seen=set(); out=[]
    for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
        ch=[];cur=r
        while cur not in seen:
            seen.add(cur);ch.append(cur)
            if cur not in succ:break
            cur=succ[cur]
        out.append(ch)
    if len(seen)!=len(nodes):return None
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
    if len(sys.argv)!=2:raise SystemExit('usage run_v15_local_symbol_quotient.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);fits=[];solves=[];rows=[];total=0
    for tid,t in sorted(tasks.items()):
      found=None;tried=0
      for name,p in [('delete_tail',program('delete')),('keep_tail',program('keep'))]:
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
      else:rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={'schema':'verified-developmental-navigation.arc-agi2-local-symbol-quotient.v15','source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{'v14':'Global 8-connected border footprint destroyed the known d35bdbdc demonstration fit (1 -> 0).','update':'REVOKE V14 footprint generalization. Preserve only the invariant supported by both train and heldout: payload center + local equal-colored surround. The failed extension identified over-merging, so shrink representation rather than add operators.','test':'Same V13 relation/action, only node identity changed.'},
      'declared_language':{'node':'payload with four equal orthogonal neighbours; footprint = same-border cells inside local 3x3 plus payload','edge':'center(A)==border(B), unique successor','action':'V13 pairwise composition','tail':['delete','keep']},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,'restores_v13_demo_capability':'d35bdbdc' in fits,'strict_heldout_gain_over_v13':bool(solves),'rows':rows}
    out=HERE/'results_v15_local_symbol_quotient';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
