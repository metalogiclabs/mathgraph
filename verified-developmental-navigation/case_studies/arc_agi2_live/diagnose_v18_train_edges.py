import json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13
TID='d35bdbdc'

def one(inp,out):
    bg,nodes,succ,indeg,roots=v13.symbolic_graph(inp)
    rows=[]
    for a,b in sorted(succ.items()):
        oa,ob=nodes[a],nodes[b]
        ca=oa['center_pt']; kept=not all(out[i][j]==bg for i,j in oa['pts'])
        newc=out[ca[0]][ca[1]] if kept else None
        composed=kept and newc==ob['center']
        rows.append({'a':a,'b':b,'a_anchor':oa['anchor'],'b_anchor':ob['anchor'],'dr':ob['anchor'][0]-oa['anchor'][0],'dc':ob['anchor'][1]-oa['anchor'][1],'dist':abs(ob['anchor'][0]-oa['anchor'][0])+abs(ob['anchor'][1]-oa['anchor'][1]),'a_indeg':indeg[a],'b_indeg':indeg[b],'a_root':a in roots,'composed':composed})
    return rows

def main():
    t=run_v2.v1.load_tasks(sys.argv[1])[TID]
    result={'task':TID,'train_edges':[one(x['input'],x['output']) for x in t['train']]}
    out=HERE/'results_v18_train_edges';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
