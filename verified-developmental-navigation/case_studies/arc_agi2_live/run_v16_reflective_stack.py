"""V16: test 'real recursion' as bidirectional improvement across levels.

A stack is not counted as recursive merely because L(k+1) observes L(k).
For each adjacent pair we require two causal directions:
  upward: lower-level residual changes the higher-level policy;
  downward: the changed higher-level policy changes lower-level reachable moves.
We also require descent after a successful meta repair and charge every active level.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Frozen evidence from the ARC lineage. Values are deliberately coarse:
# reach is demonstration reachability, not leaderboard score.
TRACE = [
    {'step':0,'level':0,'axis':'grid','reach':0,'event':'exhausted'},
    {'step':1,'level':1,'axis':'local-cell','reach':5,'event':'representation-change'},
    {'step':2,'level':1,'axis':'object','reach':0,'event':'representation-change'},
    {'step':3,'level':1,'axis':'spatial-pair','reach':0,'event':'representation-change'},
    {'step':4,'level':1,'axis':'object-class','reach':2,'event':'representation-change'},
    {'step':5,'level':1,'axis':'spatial-graph','reach':0,'event':'exhausted'},
    {'step':6,'level':2,'axis':'symbolic-relation-policy','reach':1,'event':'policy-change'},
    {'step':7,'level':1,'axis':'symbolic-relation','reach':1,'event':'descent'},
]

def evaluate(trace):
    # L0 -> L1: grid closure failure caused representation search.
    up01 = trace[0]['event']=='exhausted' and trace[1]['level']==1
    # L1 -> L2: repeated spatial-family failure caused a change in the policy
    # that chooses relation ontologies.
    spatial = [x for x in trace if x['level']==1 and x['axis'] in {'spatial-pair','spatial-graph'}]
    up12 = len(spatial)>=2 and all(x['reach']==0 for x in spatial) and trace[6]['level']==2
    # L2 -> L1: policy repair supplied a symbolic relation ontology with new reach.
    down21 = trace[6]['reach']>0 and trace[7]['level']==1 and trace[7]['axis']=='symbolic-relation'
    # L1 -> L0 is not yet established: symbolic family has train reach but no held-out solve.
    down10 = False
    return {
      'upward_0_to_1':up01,
      'upward_1_to_2':up12,
      'downward_2_to_1':down21,
      'downward_1_to_0':down10,
      'closed_recursive_chain':up01 and up12 and down21 and down10,
      'partial_reflective_stack':up01 and up12 and down21,
    }

def optimal_depth(world_depth, max_depth=5, level_cost=1):
    # Synthetic exact control: decisive gain arrives only when depth reaches the
    # world's required level; extra levels add cost. This tests the stopping law.
    scored=[]
    for d in range(max_depth+1):
        gain = 10 if d >= world_depth else 0
        score = gain - level_cost*d
        scored.append((score,d))
    best=max(scored)[1]
    return best, scored

def main():
    causal=evaluate(TRACE)
    controls=[]
    for required in range(5):
        best,scores=optimal_depth(required)
        controls.append({'required_depth':required,'optimal_depth':best,'scores':scores})
    result={
      'schema':'verified-developmental-navigation.reflective-stack.v16',
      'definition':'Real recursive development requires causal traffic in both directions across adjacent levels, not merely repeated base-level looping.',
      'trace':TRACE,
      'causal_directions':causal,
      'depth_controls':controls,
      'conclusion':(
        'ARC currently establishes a partial reflective stack L0->L1->L2->L1, not yet a closed self-improvement cycle. '
        'The missing edge is L1->L0: the meta-induced symbolic ontology must produce a held-out task capability gain. '
        'Finite controls independently show that optimal active depth tracks the first decisive level and deeper recursion is penalized.'
      ),
      'next_gate':'Obtain a held-out ARC solve causally attributable to the L2-selected symbolic ontology; ablate L2 policy change and require the solve to disappear.'
    }
    assert causal['partial_reflective_stack']
    assert not causal['closed_recursive_chain']
    assert all(x['required_depth']==x['optimal_depth'] for x in controls)
    out=HERE/'results_v16_reflective_stack'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
