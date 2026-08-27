import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13

TID='d35bdbdc'

def glyphs(g):
    q=v13.chains(g)
    if q is None:return {'chain_parse':False}
    bg,nodes,chs=q
    return {'chain_parse':True,'chains':[[{'anchor':nodes[k]['anchor'],'border':nodes[k]['border'],'center':nodes[k]['center']} for k in ch] for ch in chs]}

def diff(a,b):
    h,w=run_v2.v1.shape(a); ds=[]
    for i in range(h):
      for j in range(w):
        if a[i][j]!=b[i][j]: ds.append({'p':[i,j],'pred':a[i][j],'gold':b[i][j]})
    return ds

def main():
    if len(sys.argv)!=2: raise SystemExit('usage diagnose_v13_heldout.py EVAL_DIR')
    t=run_v2.v1.load_tasks(sys.argv[1])[TID]
    rows=[]
    for idx,case in enumerate(t['test']):
        inp=case['input']; gold=case['output']
        item={'test_index':idx,'input_symbolic':glyphs(inp)}
        for tail in ('delete','keep'):
            p=v13.program(tail); pred=p(inp)
            item[tail]={'parse_ok':pred is not None,'diff_count':None if pred is None else len(diff(pred,gold)),'diff':None if pred is None else diff(pred,gold)}
        rows.append(item)
    result={'schema':'verified-developmental-navigation.arc-agi2-v13-heldout-residual.v1','task':TID,'rows':rows,
      'meta_loop':{'question':'V13 fits every demonstration of d35bdbdc but fails heldout. Is the symbolic relation wrong, or is only its chain reduction policy underspecified?','decision_rule':'If the heldout parses into the same symbolic graph and errors are localized to tail/pairing choices, keep the representation and refine action. If parsing fails or errors escape glyphs, reopen representation.'}}
    out=HERE/'results_v13_heldout_diagnostic'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
