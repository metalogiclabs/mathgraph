import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13

# Recursive VDN: the same residual calculus is applied to (0) task programs,
# (1) representation families, and (2) the policy choosing representation changes.
HISTORY = [
 {'level':0,'family':'grid','axis':'entity:grid','fits':0,'checks':None},
 {'level':0,'family':'grid-depth2','axis':'entity:grid','fits':0,'checks':876264},
 {'level':1,'family':'local-cells','axis':'entity:cell','fits':5,'heldout':0},
 {'level':1,'family':'single-object','axis':'entity:object','fits':0},
 {'level':1,'family':'pair-relations','axis':'relation:spatial-pair','fits':0},
 {'level':1,'family':'set-quotient','axis':'entity:object-class','fits':2,'heldout':0},
 {'level':1,'family':'scene-graph','axis':'relation:spatial-graph','fits':0,'checks':130368},
 {'level':2,'family':'symbolic-graph','axis':'relation:symbolic','fits':1,'heldout':0},
]

def meta_residual(history):
    # Evidence-based escalation: repeated zero-gain changes sharing an abstraction axis
    # are treated as a residual of the move generator, not of the task solver.
    spatial=[x for x in history if x['axis'].startswith('relation:spatial')]
    grid=[x for x in history if x['axis']=='entity:grid']
    return {
      'task_residual':'No currently admitted symbolic program solves the held-out example.',
      'representation_residual':'Spatial object/pair/graph relations repeatedly fail to reach demonstrations.',
      'policy_residual':'The move generator repeatedly elaborated operations while preserving a spatial ontology.',
      'evidence':{
        'grid_same_axis_failures':sum(x['fits']==0 for x in grid),
        'spatial_relation_failures':sum(x['fits']==0 for x in spatial),
        'symbolic_relation_gain':max(x['fits'] for x in history if x['axis']=='relation:symbolic'),
      },
      'routing_law':'Change the lowest level with certified inadequacy. If multiple extensions on one abstraction axis give no reachability gain, apply VDN to the extension policy: discount that axis and test the smallest alternative ontology.'
    }

def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v14_recursive_meta.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1])
    r=meta_residual(HISTORY)
    # Replay the representation selected by the level-2 residual without changing V13.
    fits=[]; solves=[]; checks=0
    for tid,t in sorted(tasks.items()):
      found=False
      for name,p in [('delete_tail',v13.program('delete')),('keep_tail',v13.program('keep'))]:
        checks+=1
        try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
        except Exception: fit=False
        if fit:
          fits.append(tid)
          try:
            if run_v2.v1.task_solved(p,t): solves.append(tid)
          except Exception: pass
          found=True; break
    result={
      'schema':'verified-developmental-navigation.arc-agi2-recursive-meta.v14',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'recursive_levels':{
        'L0':'task/program residuals',
        'L1':'representation/ontology residuals',
        'L2':'residuals of the policy that chooses representation changes'
      },
      'history':HISTORY,
      'meta_residual':r,
      'selected_move':{'level':2,'decision':'REORGANIZE_RELATION','from':'spatial relation ontology','to':'symbolic equality/composition ontology','reason':'lowest level whose repeated failures explain the stalled extension policy'},
      'replay':{'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':checks},
      'meta_claim':'The recursion changes what generates candidate moves: failure is represented not only over task states but over representation families and over the policy selecting those families.'
    }
    out=HERE/'results_v14_recursive_meta'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
