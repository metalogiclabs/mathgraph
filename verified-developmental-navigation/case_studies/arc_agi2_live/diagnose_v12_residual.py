import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v12_scene_graph as v12

TARGETS=['d35bdbdc','97d7923e']

def classify_node(inp,out,o,bg):
    vals=[out[i][j] for i,j in sorted(o['pts'])]
    if all(x==bg for x in vals): return 'deleted'
    same_border=all(out[i][j]==inp[i][j] for i,j in o['pts'] if (i,j)!=o['center_pt'])
    ci,cj=o['center_pt']
    if same_border and out[ci][cj]==inp[ci][cj]: return 'unchanged'
    if same_border: return f'center:{inp[ci][cj]}->{out[ci][cj]}'
    return 'structural_edit'

def analyze_pair(inp,out):
    bg,nodes=v12.detect_nodes(inp)
    changed={(i,j) for i,row in enumerate(inp) for j,x in enumerate(row) if out[i][j]!=x}
    covered=set().union(*(o['pts'] for o in nodes)) if nodes else set()
    outside=changed-covered
    colors=sorted({x for r in inp for x in r if x!=bg})
    path_summaries=[]
    for pc in colors:
        _,ns,adj=v12.graph_scene(inp,pc)
        if len(ns)!=len(nodes): continue
        edges=sorted((i,j) for i,a in enumerate(adj) for j in a if i<j)
        path_summaries.append({'path_color':pc,'edges':edges,'degrees':[len(a) for a in adj]})
    node_rows=[]
    for k,o in enumerate(nodes):
        node_rows.append({'k':k,'anchor':o['anchor'],'border':o['border'],'center':o['center'],'transition':classify_node(inp,out,o,bg)})
    return {'node_count':len(nodes),'changed_cells':len(changed),'changed_inside_nodes':len(changed & covered),'changed_outside_nodes':len(outside),'outside_changed_sample':sorted(outside)[:20],'nodes':node_rows,'path_summaries':path_summaries}

def main():
    if len(sys.argv)!=2: raise SystemExit('usage diagnose_v12_residual.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); result={'schema':'verified-developmental-navigation.arc-agi2-v12-residual-diagnostic.v1','tasks':{}}
    for tid in TARGETS:
        t=tasks[tid]; result['tasks'][tid]={'train':[analyze_pair(p['input'],p['output']) for p in t['train']]}
    out=HERE/'results_v12_residual_diagnostic'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()
