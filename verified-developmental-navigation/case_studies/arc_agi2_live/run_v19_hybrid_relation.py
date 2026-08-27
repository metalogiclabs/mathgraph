import json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v12_scene_graph as v12
import run_v13_symbolic_composition as v13


def hybrid_program(path_color):
    def f(g):
        bg,nodes,succ,indeg,roots=v13.symbolic_graph(g)
        if len(nodes)<2:return None
        _,snodes,adj=v12.graph_scene(g,path_color)
        # v12 and v13 share the same literal 3x3 detector/order.
        if len(snodes)!=len(nodes):return None
        selected={}
        for a,b in succ.items():
            if b in adj[a]: selected[a]=b
        if not selected:return None
        out=[list(r) for r in g]
        for k,o in enumerate(nodes):
            if k in selected:
                b=selected[k];ci,cj=o['center_pt'];out[ci][cj]=nodes[b]['center']
            else:
                for i,j in o['pts']:out[i][j]=bg
        return tuple(tuple(r) for r in out)
    return f


def candidates(task):
    colors=sorted({x for inp,_ in run_v2.v1.task_pairs(task) for r in inp for x in r if x!=0})
    for c in colors:yield f'hybrid:path={c}',hybrid_program(c)


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v19_hybrid_relation.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);fits=[];solves=[];rows=[];total=0
    for tid,t in sorted(tasks.items()):
      found=None;tried=0
      for name,p in candidates(t):
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
    result={'schema':'verified-developmental-navigation.arc-agi2-hybrid-relation.v19','source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{'v12':'Spatial path relation alone: 0 fits.','v13':'Symbolic equality center(A)=border(B) alone: d35bdbdc demonstrations fit, but heldout fails.','v18_train_separator':'On every d35bdbdc demonstration, the gold kept/composed glyphs are a strict subset of symbolic edges. The repeated process suggests two earlier representations may be complementary rather than one replacing the other.','move':'INTERSECT RELATIONS: compose A with B iff center(A)=border(B) AND the two glyphs are connected by the same path-color component. Keep/rewrite exactly selected sources; delete all other glyphs. Search only the path color.'},
      'declared_language':{'nodes':'V13 literal 3x3 glyphs','symbolic_relation':'center(A)==border(B)','spatial_relation':'same path-color component touches A and B','selection':'intersection','action':'source center := target center; delete all unselected glyphs'},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,'strict_heldout_gain_over_v13':bool(solves),'rows':rows}
    out=HERE/'results_v19_hybrid_relation';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
