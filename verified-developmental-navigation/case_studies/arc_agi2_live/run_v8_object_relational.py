import json, collections, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2


def mode_color(g):
    c=collections.Counter(x for r in g for x in r)
    return c.most_common(1)[0][0]

def objects(g,diag=False):
    bg=mode_color(g); h,w=run_v2.v1.shape(g)
    unseen={(i,j) for i in range(h) for j in range(w) if g[i][j]!=bg}
    dirs=[(-1,0),(1,0),(0,-1),(0,1)]
    if diag: dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
    out=[]
    while unseen:
        s=min(unseen); unseen.remove(s); st=[s]; cc={s}
        while st:
            i,j=st.pop()
            for di,dj in dirs:
                q=(i+di,j+dj)
                if q in unseen: unseen.remove(q); cc.add(q); st.append(q)
        rs=[i for i,j in cc]; cs=[j for i,j in cc]
        box=(min(rs),max(rs),min(cs),max(cs)); bh=box[1]-box[0]+1; bw=box[3]-box[2]+1
        cols=tuple(sorted({g[i][j] for i,j in cc}))
        out.append({'pts':cc,'box':box,'size':len(cc),'shape':(bh,bw),'colors':cols,'anchor':min(cc)})
    return bg,out

def render(g,o,mask=False):
    a,b,c,d=o['box']; bg=mode_color(g); pts=o['pts']; rows=[]
    for i in range(a,b+1):
        row=[]
        for j in range(c,d+1): row.append(g[i][j] if (not mask or (i,j) in pts) else bg)
        rows.append(tuple(row))
    return tuple(rows)

def select(os,rule):
    if not os:return None
    if rule=='largest': return max(os,key=lambda o:(o['size'],-o['anchor'][0],-o['anchor'][1]))
    if rule=='smallest': return min(os,key=lambda o:(o['size'],o['anchor']))
    if rule=='first': return min(os,key=lambda o:o['anchor'])
    if rule=='last': return max(os,key=lambda o:o['anchor'])
    if rule=='most_colors': return max(os,key=lambda o:(len(o['colors']),o['size']))
    if rule=='least_colors': return min(os,key=lambda o:(len(o['colors']),o['size']))
    if rule=='unique_size':
        cnt=collections.Counter(o['size'] for o in os); q=[o for o in os if cnt[o['size']]==1]
        return q[0] if len(q)==1 else None
    if rule=='unique_shape':
        cnt=collections.Counter(o['shape'] for o in os); q=[o for o in os if cnt[o['shape']]==1]
        return q[0] if len(q)==1 else None
    return None

RULES=['largest','smallest','first','last','most_colors','least_colors','unique_size','unique_shape']

def candidates(task):
    pairs=run_v2.v1.task_pairs(task); ans=[]
    for diag in (False,True):
      for rule in RULES:
       for mask in (False,True):
        for gname,gfn in run_v2.v1.GEOMS:
          def base(g,diag=diag,rule=rule,mask=mask,gfn=gfn):
              _,os=objects(g,diag); o=select(os,rule)
              return None if o is None else gfn(render(g,o,mask))
          ans.append((f'obj:{8 if diag else 4}:{rule}:{"mask" if mask else "bbox"}:{gname}',base))
          # Same structural program with demonstration-inferred recolor.
          try: m=run_v2.v1.infer_recolor(pairs,pre=base)
          except Exception: m=None
          if m is not None:
              ans.append((f'obj:{8 if diag else 4}:{rule}:{"mask" if mask else "bbox"}:{gname}+recolor',run_v2.v1.recolor_program(m,pre=base)))
    return ans

def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v8_object_relational.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; fam=collections.Counter(); total=0
    for tid,t in sorted(tasks.items()):
        pairs=run_v2.v1.task_pairs(t); found=None; tried=0
        for name,p in candidates(t):
            tried+=1; total+=1
            try: fit=run_v2.v1.exact_on_pairs(p,pairs)
            except Exception: fit=False
            if fit:
                try: solved=run_v2.v1.task_solved(p,t)
                except Exception: solved=False
                found=(name,solved); break
        if found:
            name,solved=found; fits.append(tid); solves += [tid] if solved else []; fam[name.split(':')[2]]+=1
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else: rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-object-relational.v8',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'residual_basis':{'v4_depth2_fits':0,'v7_local_fits':5,'v7_local_heldout_solves':0,'v6_input_multiobject_tasks':100,'interpretation':'Local cell rules increased demonstration reach but did not transfer; introduce multicolor connected objects with stable selection predicates, crop/mask, geometry and optional inferred recolor.'},
      'declared_language':{'connectivity':[4,8],'selection_rules':RULES,'render':['bbox','mask'],'geometry':[n for n,_ in run_v2.v1.GEOMS],'optional_recolor':True},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'selection_rule_first_fit_counts':dict(fam),'total_candidate_evaluations_until_first_fit_or_exhaustion':total,
      'strict_reachability_gain_over_v7':len(fits)>5,'strict_heldout_gain_over_v7':bool(solves),
      'rows':rows,
    }
    out=HERE/'results_v8_object_relational'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
