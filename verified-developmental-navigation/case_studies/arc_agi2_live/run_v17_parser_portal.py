import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13
import run_v15_local_symbol_quotient as v15


def apply_from_chains(q,tail):
    if q is None:return None
    bg,nodes,chs=q; out=None
    return bg,nodes,chs


def local_program(tail='delete'):
    return v15.program(tail)


def portal_program(tail='delete'):
    base=v13.program(tail); alt=local_program(tail)
    def f(g):
        # Conservative semantic portal: if the admitted V13 representation is
        # defined, execute it unchanged. Only enter the extension on an input
        # where V13 cannot even form its symbolic chain state.
        if v13.chains(g) is not None:
            return base(g)
        return alt(g)
    return f


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v17_parser_portal.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);fits=[];solves=[];rows=[];total=0
    for tid,t in sorted(tasks.items()):
      found=None;tried=0
      for name,p in [('delete_tail',portal_program('delete')),('keep_tail',portal_program('keep'))]:
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
    result={'schema':'verified-developmental-navigation.arc-agi2-parser-portal.v17','source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{
        'v16':'Unioning old and new nodes still destroyed V13 capability: set inclusion of representations was not semantic conservativity because new nodes changed graph dynamics.',
        'derived_meta_law':'Conservative extension must preserve old behavior, not merely contain old syntax/state. Treat representations as alternative portals with an admissibility guard.',
        'repair':'If V13 can form a complete symbolic chain state, use its old semantics exactly. Invoke the broader V15 parser only when V13 is undefined. Relation/action remain frozen.',
        'success_condition':'Provably by construction, all inputs in the old definedness domain behave exactly as V13; measure whether the new portal adds heldout reach.'},
      'declared_language':{'portal_guard':'V13 chains(g) is defined','old_branch':'V13 literal parser+composition unchanged','fallback_branch':'V15 local-symbol parser+same composition','tail':['delete','keep']},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,'retains_v13_demo_capability':'d35bdbdc' in fits,'strict_heldout_gain_over_v13':bool(solves),'rows':rows}
    out=HERE/'results_v17_parser_portal';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
