"""V35: is V34's anonymous per-cell observation map adequate in principle?

V34 found no <=4-literal conjunction that exactly predicts training edit support on
any of the seven diagnostics. That could be a weak classifier, or a deeper
representation failure. Test the stronger question: using the FULL V34 anonymous
atom vector as a cell signature, do identical signatures ever require different
edit-support labels within a task's training set?

If yes, no classifier over this unary observation map can be exact. The residual
then forces a relational/contextual observation lift rather than more classifier
search over the same coordinates.
"""
import json,sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v34_raw_support_induction as v34
TARGET_IDS=sorted(v34.TARGET_IDS)

def analyse(t):
    bysig=defaultdict(lambda:{'changed':0,'unchanged':0,'examples':[]})
    for pi,p in enumerate(t['train']):
        if v34.shape(p['input'])!=v34.shape(p['output']):
            return {'status':'SHAPE_CHANGE_TRAIN'}
        yy=v34.changed(p['input'],p['output']); aa=v34.atoms(p['input'])
        for pos,sig in aa.items():
            k=tuple(bool(x) for x in sig); lab=pos in yy
            z=bysig[k]; z['changed']+=int(lab); z['unchanged']+=int(not lab)
            if len(z['examples'])<4:z['examples'].append([pi,pos[0],pos[1],int(lab)])
    collisions=[]
    for sig,z in bysig.items():
        if z['changed'] and z['unchanged']:
            collisions.append({'signature':[int(x) for x in sig],'changed':z['changed'],'unchanged':z['unchanged'],'examples':z['examples']})
    total=sum(z['changed']+z['unchanged'] for z in bysig.values())
    ambiguous=sum(z['changed']+z['unchanged'] for z in bysig.values() if z['changed'] and z['unchanged'])
    return {'status':'UNARY_INADEQUATE' if collisions else 'UNARY_SEPARABLE',
            'unique_signatures':len(bysig),'collision_signatures':len(collisions),
            'cells':total,'cells_in_collision_signatures':ambiguous,
            'collision_fraction':ambiguous/total if total else 0.0,
            'collision_examples':collisions[:8]}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; totals={}
    for tid in TARGET_IDS:
        r=analyse(tasks[tid]);r['task']=tid;rows.append(r);totals[r['status']]=totals.get(r['status'],0)+1
        print(json.dumps({k:v for k,v in r.items() if k!='collision_examples'},sort_keys=True),flush=True)
    result={'schema':'verified-developmental-navigation.arc-agi2-unary-adequacy-collision.v35',
      'evidence_label':'TRAIN_ONLY_REPRESENTATION_ADEQUACY_TEST','totals':totals,'rows':rows,
      'decision_law':'A label collision inside an identical full observation signature proves the unary V34 map insufficient for exact support induction, independent of classifier power.',
      'routing':'If collisions exist broadly, lift observation from unary cell properties to relations/contexts. If no collisions, improve the classifier only.'}
    out=HERE/'results_v35_unary_adequacy_collision';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({'totals':totals},indent=2,sort_keys=True))
if __name__=='__main__':main()
