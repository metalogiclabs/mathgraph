"""V34: can the missing ARC effect support be induced from raw cell traces?

V33 showed the frozen V23+V26 continuation language is support-incomplete on all
nine held-out diagnostics (6 EFFECT_SUPPORT_MISSING, 3 NO_ACTIONS). Before adding
named ARC objects, test a lower-level adequacy mechanism: synthesize a small
conjunction of anonymous, translation-invariant per-cell predicates whose truth
set exactly equals the changed-cell support on every training pair.

The selector is learned from TRAIN input/output deltas only. Held-out outputs are
used only after freezing, for retrospective support evaluation. This tests support
adequacy, not value generation or full ARC solving.
"""
import itertools,json,sys
from collections import Counter,deque
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2
TARGET_IDS={'332f06d7','36a08778','53fb4810','7b80bb43','88bcf3b4','b9e38dc0','d59b0160'}
MAX_LITS=4

def shape(g): return len(g),len(g[0])
def changed(x,y):
    if shape(x)!=shape(y): return set()
    h,w=shape(x); return {(i,j) for i in range(h) for j in range(w) if x[i][j]!=y[i][j]}

def comp_features(g):
    h,w=shape(g); seen=set(); comp={}
    for i in range(h):
      for j in range(w):
        if (i,j) in seen: continue
        val=g[i][j]; q=[(i,j)]; seen.add((i,j)); cells=[]
        while q:
          a,b=q.pop(); cells.append((a,b))
          for da,db in ((1,0),(-1,0),(0,1),(0,-1)):
            u,v=a+da,b+db
            if 0<=u<h and 0<=v<w and (u,v) not in seen and g[u][v]==val:
              seen.add((u,v)); q.append((u,v))
        n=len(cells); rs=[a for a,b in cells]; cs=[b for a,b in cells]
        rh=max(rs)-min(rs)+1; cw=max(cs)-min(cs)+1
        for p in cells: comp[p]=(n,rh,cw)
    return comp

def atoms(g):
    """Return anonymous boolean atoms per cell. No task/output semantics."""
    h,w=shape(g); cnt=Counter(v for r in g for v in r); mode=max(cnt,key=lambda v:(cnt[v],-v)); cf=comp_features(g)
    out={}
    for i in range(h):
      for j in range(w):
        v=g[i][j]; n,rh,cw=cf[(i,j)]
        eq=[]
        for di,dj in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
          a,b=i+di,j+dj; eq.append(0<=a<h and 0<=b<w and g[a][b]==v)
        out[(i,j)] = (
          v==mode, v!=mode, v==0, v!=0,
          i==0 or i==h-1 or j==0 or j==w-1,
          i>0 and i<h-1 and j>0 and j<w-1,
          n==1,n<=2,n<=4,n>=5,
          rh==1,cw==1,rh==cw,
          sum(eq[:4])==0,sum(eq[:4])==1,sum(eq[:4])>=2,
          eq[0],eq[1],eq[2],eq[3],
          sum(eq)>=1,sum(eq)>=3,
          cnt[v]==1,cnt[v]<=3,cnt[v]>=5,
        )
    return out

def lit_truth(vec,lit):
    k,pol=lit; return vec[k] if pol else not vec[k]

def predict(g,rule):
    aa=atoms(g); return {p for p,v in aa.items() if all(lit_truth(v,L) for L in rule)}

def learn(t):
    train=[]
    for p in t['train']:
      if shape(p['input'])!=shape(p['output']): return None
      aa=atoms(p['input']); yy=changed(p['input'],p['output']); train.append((p['input'],aa,yy))
    if not train:return None
    m=len(next(iter(train[0][1].values())))
    lits=[(k,pol) for k in range(m) for pol in (True,False)]
    # exact support first; smallest conjunction wins, syntax order deterministic.
    for d in range(1,MAX_LITS+1):
      for rule in itertools.combinations(lits,d):
        # reject contradictory same atom +/- pairs
        ks=[k for k,p in rule]
        if len(set(ks))<len(ks): continue
        ok=True
        for g,aa,yy in train:
          pp={pos for pos,v in aa.items() if all(lit_truth(v,L) for L in rule)}
          if pp!=yy: ok=False; break
        if ok:return list(rule)
    return None

def main():
    if len(sys.argv)!=2: raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]
    for tid in sorted(TARGET_IDS):
      t=tasks[tid]; rule=learn(t)
      for qi,p in enumerate(t['test']):
        if 'output' not in p:continue
        yy=changed(p['input'],p['output']) if shape(p['input'])==shape(p['output']) else set()
        if rule is None:
          r={'task':tid,'test_index':qi,'status':'NO_EXACT_TRAIN_SUPPORT_RULE','target':len(yy)}
        else:
          pp=predict(p['input'],rule); inter=len(pp&yy); prec=inter/len(pp) if pp else (1.0 if not yy else 0.0); rec=inter/len(yy) if yy else 1.0
          r={'task':tid,'test_index':qi,'status':'RULE','rule':rule,'predicted':len(pp),'target':len(yy),'intersection':inter,'precision':prec,'recall':rec,'exact_support':pp==yy}
        rows.append(r); print(json.dumps(r,sort_keys=True),flush=True)
    ruled=[r for r in rows if r['status']=='RULE']
    result={'schema':'verified-developmental-navigation.arc-agi2-raw-support-induction.v34','evidence_label':'TRAIN_ONLY_SUPPORT_RULE_THEN_KNOWN_WORLD_EVAL',
      'tests':len(rows),'tests_with_exact_train_rule':len(ruled),'exact_heldout_support':sum(r.get('exact_support',False) for r in ruled),
      'mean_recall':sum(r['recall'] for r in ruled)/len(ruled) if ruled else None,'mean_precision':sum(r['precision'] for r in ruled)/len(ruled) if ruled else None,
      'principle':'Test whether a minimal anonymous raw-trace predicate basis can recover the missing effect support before introducing named object ontologies.','rows':rows}
    out=HERE/'results_v34_raw_support_induction';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
