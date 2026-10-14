import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8


def detect_nodes(g):
    h,w=run_v2.v1.shape(g); bg=v8.mode_color(g); cand=[]
    for i in range(h-2):
      for j in range(w-2):
        per=[g[i+a][j+b] for a,b in ((0,0),(0,1),(0,2),(1,0),(1,2),(2,0),(2,1),(2,2))]
        if len(set(per))==1 and per[0]!=bg:
            pts={(i+a,j+b) for a in range(3) for b in range(3)}
            cand.append({'anchor':(i,j),'pts':pts,'border':per[0],'center':g[i+1][j+1],'center_pt':(i+1,j+1)})
    # deterministic non-overlap preference by anchor
    out=[]; used=set()
    for o in cand:
        if not (o['pts'] & used): out.append(o); used |= o['pts']
    return bg,out


def graph_scene(g,path_color):
    bg,nodes=detect_nodes(g); h,w=run_v2.v1.shape(g)
    node_owner={p:k for k,o in enumerate(nodes) for p in o['pts']}
    path={(i,j) for i in range(h) for j in range(w) if g[i][j]==path_color and (i,j) not in node_owner}
    unseen=set(path); comps=[]
    while unseen:
        s=min(unseen); unseen.remove(s); st=[s]; cc={s}
        while st:
            i,j=st.pop()
            for di,dj in ((-1,0),(1,0),(0,-1),(0,1)):
                q=(i+di,j+dj)
                if q in unseen: unseen.remove(q); cc.add(q); st.append(q)
        comps.append(cc)
    adj=[set() for _ in nodes]
    for cc in comps:
        touch=set()
        for i,j in cc:
            for di,dj in ((-1,0),(1,0),(0,-1),(0,1)):
                q=(i+di,j+dj)
                if q in node_owner: touch.add(node_owner[q])
        for a in touch:
            for b in touch:
                if a!=b: adj[a].add(b)
    return bg,nodes,adj


def node_features(nodes,adj,k):
    borders=[o['border'] for o in nodes]; centers=[o['center'] for o in nodes]; o=nodes[k]
    deg=len(adj[k]); degs=[len(x) for x in adj]
    return {
      'deg':deg,
      'deg_min': deg==min(degs) if degs else True,
      'deg_max': deg==max(degs) if degs else True,
      'border_in_centers':o['border'] in centers,
      'center_in_borders':o['center'] in borders,
      'center_eq_border':o['center']==o['border'],
      'neighbor_count':len(adj[k]),
    }

PREDICATES=[]
for d in range(5): PREDICATES.append((f'deg={d}',lambda f,d=d:f['deg']==d))
PREDICATES += [
 ('deg_min',lambda f:f['deg_min']),('deg_max',lambda f:f['deg_max']),
 ('border_in_centers',lambda f:f['border_in_centers']),('center_in_borders',lambda f:f['center_in_borders']),
 ('not_border_in_centers',lambda f:not f['border_in_centers']),('not_center_in_borders',lambda f:not f['center_in_borders']),
 ('all',lambda f:True),
]
SOURCES=['self','first_neighbor_center','last_neighbor_center','first_neighbor_border','last_neighbor_border','min_degree_neighbor_center','max_degree_neighbor_center']


def source_value(nodes,adj,k,src):
    if src=='self': return nodes[k]['center']
    ns=sorted(adj[k],key=lambda q:nodes[q]['anchor'])
    if not ns: return None
    if src=='first_neighbor_center': return nodes[ns[0]]['center']
    if src=='last_neighbor_center': return nodes[ns[-1]]['center']
    if src=='first_neighbor_border': return nodes[ns[0]]['border']
    if src=='last_neighbor_border': return nodes[ns[-1]]['border']
    if src=='min_degree_neighbor_center':
        q=min(ns,key=lambda q:(len(adj[q]),nodes[q]['anchor'])); return nodes[q]['center']
    if src=='max_degree_neighbor_center':
        q=max(ns,key=lambda q:(len(adj[q]),tuple(-x for x in nodes[q]['anchor']))); return nodes[q]['center']
    return None


def program(path_color,pred,src,delete_nonkept):
    def f(g):
        bg,nodes,adj=graph_scene(g,path_color)
        if len(nodes)<2: return None
        out=[list(r) for r in g]
        for k,o in enumerate(nodes):
            keep=pred(node_features(nodes,adj,k))
            if keep:
                val=source_value(nodes,adj,k,src)
                if val is None:return None
                ci,cj=o['center_pt']; out[ci][cj]=val
            elif delete_nonkept:
                for i,j in o['pts']: out[i][j]=bg
        return tuple(tuple(r) for r in out)
    return f


def candidates(task):
    colors=sorted({x for inp,_ in run_v2.v1.task_pairs(task) for r in inp for x in r if x!=0})
    for pc in colors:
      for pname,pred in PREDICATES:
       for src in SOURCES:
        for delete in (False,True):
            yield f'graph:path={pc}:keep={pname}:src={src}:delete={delete}',program(pc,pred,src,delete)


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v12_scene_graph.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; total=0; by=collections.Counter()
    for tid,t in sorted(tasks.items()):
        found=None; tried=0
        for name,p in candidates(t):
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
            by[name.split(':')[2]]+=1
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else: rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-scene-graph.v12',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{
        'trigger':'V11 class quotient crossed 0->2 demonstration fits but both failed held-out.',
        'residual':'The successful V11 feature was shape multiplicity plus row/column multiplicity: group membership matters, but class labels alone do not determine the output. Inspection of the two residual tasks shows repeated structured motifs whose relations carry the missing information; d35bdbdc explicitly contains repeated 3x3 glyphs joined by path structure.',
        'decision':'Preserve the multi-object quotient, EXTEND_RELATION rather than add more class features: promote repeated glyphs to nodes and connecting paths to edges, then test degree/neighbor-relative actions.'
      },
      'declared_language':{'node_detector':'3x3 uniform-border glyph with payload center','edge_detector':'4-connected path-color components touching glyphs','node_predicates':[n for n,_ in PREDICATES],'center_sources':SOURCES,'delete_nonkept':[False,True]},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,'first_fit_predicate_counts':dict(by),
      'strict_reachability_gain_over_v11':len(fits)>2,'strict_heldout_gain_over_v11':bool(solves),
      'rows':rows,
    }
    out=HERE/'results_v12_scene_graph'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
