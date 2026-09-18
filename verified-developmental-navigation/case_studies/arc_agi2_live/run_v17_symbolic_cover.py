import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13

# Frozen action family inside the symbolic ontology selected by L2.
# Candidate selection uses demonstrations only; held-out outputs are scored only after fit.

def delete_node(out,node,bg):
    for i,j in node['pts']: out[i][j]=bg

def variants():
    out=[]
    # Original pairwise reduction, both tail policies.
    out += [('pairwise-delete-tail', v13.program('delete')), ('pairwise-keep-tail', v13.program('keep'))]

    # Pairwise with one-node offset. Useful when chains have a protected root marker.
    for offset in (1,):
      for tail in ('delete','keep'):
        def make(offset=offset,tail=tail):
          def f(g):
            q=v13.chains(g)
            if q is None:return None
            bg,nodes,chs=q; z=[list(r) for r in g]
            for ch in chs:
              # Prefix before offset is preserved.
              k=offset
              while k<len(ch):
                a=ch[k]
                if k+1<len(ch):
                  b=ch[k+1]; ci,cj=nodes[a]['center_pt']; z[ci][cj]=nodes[b]['center']; delete_node(z,nodes[b],bg); k+=2
                else:
                  if tail=='delete': delete_node(z,nodes[a],bg)
                  k+=1
            return tuple(tuple(r) for r in z)
          return f
        out.append((f'pairwise-offset{offset}-{tail}-tail',make()))

    # Collapse each chain to its root, composing all successors at once.
    for tailvalue in ('last-center','last-border'):
      def make(tailvalue=tailvalue):
        def f(g):
          q=v13.chains(g)
          if q is None:return None
          bg,nodes,chs=q; z=[list(r) for r in g]
          for ch in chs:
            if len(ch)<2: continue
            root=ch[0]; last=ch[-1]
            ci,cj=nodes[root]['center_pt']
            z[ci][cj]=nodes[last]['center'] if tailvalue=='last-center' else nodes[last]['border']
            for k in ch[1:]: delete_node(z,nodes[k],bg)
          return tuple(tuple(r) for r in z)
        return f
      out.append((f'collapse-root-{tailvalue}',make()))

    # Synchronous one-hop composition: each nonterminal node takes successor payload;
    # terminal nodes can be deleted or retained. Uses the same symbolic edge relation.
    for terminal in ('delete','keep'):
      def make(terminal=terminal):
        def f(g):
          bg,nodes,succ,indeg,roots=v13.symbolic_graph(g)
          if len(nodes)<2:return None
          z=[list(r) for r in g]
          for k,o in enumerate(nodes):
            if k in succ:
              s=succ[k]; ci,cj=o['center_pt']; z[ci][cj]=nodes[s]['center']
            elif terminal=='delete': delete_node(z,o,bg)
          return tuple(tuple(r) for r in z)
        return f
      out.append((f'synchronous-hop-{terminal}-terminal',make()))
    return out


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v17_symbolic_cover.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); V=variants(); rows=[]; fits=[]; solves=[]; total=0
    for tid,t in sorted(tasks.items()):
      fitting=[]
      for name,p in V:
        total+=1
        try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
        except Exception: fit=False
        if fit: fitting.append((name,p))
      solved=[]
      for name,p in fitting:
        try:
          if run_v2.v1.task_solved(p,t): solved.append(name)
        except Exception: pass
      if fitting: fits.append(tid)
      if solved: solves.append(tid)
      rows.append({'task':tid,'fit_programs':[n for n,_ in fitting],'heldout_solved_programs':solved})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-symbolic-cover.v17',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'declared_symbolic_action_family':[n for n,_ in V],
      'candidate_count_per_task':len(V),'candidate_evaluations':total,
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,
      'closed_L1_to_L0_edge':bool(solves),
      'decision':('CLOSE_RECURSIVE_EDGE_AND_ABLATE' if solves else 'SYMBOLIC_ACTION_FAMILY_EXHAUSTED_WITHOUT_HELDOUT_GAIN'),
      'rows':rows,
      'claim_boundary':'Complete only for this explicitly frozen finite action family inside the V13 symbolic ontology; not complete for symbolic programs generally.'
    }
    out=HERE/'results_v17_symbolic_cover'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__':main()
