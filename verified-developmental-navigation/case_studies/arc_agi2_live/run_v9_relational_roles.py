import collections, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v2
import run_v8_object_relational as v8


def center(o):
    a,b,c,d=o['box']
    return ((a+b)/2.0, (c+d)/2.0)


def pair_distance(p):
    a,b=p
    ca,cb=center(a),center(b)
    return abs(ca[0]-cb[0]) + abs(ca[1]-cb[1])


def pair_key(p):
    a,b=sorted(p,key=lambda o:o['anchor'])
    return (a['anchor'],b['anchor'])


def unique_extreme(pairs, key, want_max=False):
    if not pairs: return None
    vals=[key(p) for p in pairs]
    target=(max(vals) if want_max else min(vals))
    q=[p for p,v in zip(pairs,vals) if v==target]
    return q[0] if len(q)==1 else None


def choose_pair(os, rule):
    ps=[(os[i],os[j]) for i in range(len(os)) for j in range(i+1,len(os))]
    if not ps: return None
    if rule=='closest': return unique_extreme(ps,pair_distance,False)
    if rule=='farthest': return unique_extreme(ps,pair_distance,True)
    if rule=='unique_same_shape':
        q=[p for p in ps if p[0]['shape']==p[1]['shape']]
        return q[0] if len(q)==1 else None
    if rule=='unique_same_size':
        q=[p for p in ps if p[0]['size']==p[1]['size']]
        return q[0] if len(q)==1 else None
    if rule=='unique_same_colors':
        q=[p for p in ps if p[0]['colors']==p[1]['colors']]
        return q[0] if len(q)==1 else None
    if rule=='unique_same_row':
        q=[p for p in ps if center(p[0])[0]==center(p[1])[0]]
        return q[0] if len(q)==1 else None
    if rule=='unique_same_col':
        q=[p for p in ps if center(p[0])[1]==center(p[1])[1]]
        return q[0] if len(q)==1 else None
    if rule=='largest_pair':
        return unique_extreme(ps,lambda p:p[0]['size']+p[1]['size'],True)
    if rule=='smallest_pair':
        return unique_extreme(ps,lambda p:p[0]['size']+p[1]['size'],False)
    if rule=='most_color_pair':
        return unique_extreme(ps,lambda p:len(set(p[0]['colors'])|set(p[1]['colors'])),True)
    return None

RULES=['closest','farthest','unique_same_shape','unique_same_size','unique_same_colors','unique_same_row','unique_same_col','largest_pair','smallest_pair','most_color_pair']


def role_grid(g, diag, rule):
    bg,os=v8.objects(g,diag)
    p=choose_pair(os,rule)
    if p is None: return None
    a,b=sorted(p,key=lambda o:o['anchor'])
    apt,bpt=a['pts'],b['pts']
    other=set().union(*(o['pts'] for o in os)) - apt - bpt if os else set()
    h,w=run_v2.v1.shape(g)
    roles=[]
    for i in range(h):
        row=[]
        for j in range(w):
            q=(i,j)
            if q in apt: role='A'
            elif q in bpt: role='B'
            elif q in other: role='OTHER'
            else: role='BG'
            row.append(role)
        roles.append(tuple(row))
    return tuple(roles)


def infer_role_map(task, diag, rule, role_only=False):
    m={}
    for inp,out in run_v2.v1.task_pairs(task):
        if run_v2.v1.shape(inp)!=run_v2.v1.shape(out): return None
        roles=role_grid(inp,diag,rule)
        if roles is None: return None
        for i,row in enumerate(inp):
            for j,x in enumerate(row):
                k=roles[i][j] if role_only else (roles[i][j],x)
                y=out[i][j]
                if k in m and m[k]!=y: return None
                m[k]=y
    return m


def program(diag,rule,m,role_only=False):
    def f(g):
        roles=role_grid(g,diag,rule)
        if roles is None: return None
        out=[]
        for i,row in enumerate(g):
            rr=[]
            for j,x in enumerate(row):
                k=roles[i][j] if role_only else (roles[i][j],x)
                if k not in m: return None
                rr.append(m[k])
            out.append(tuple(rr))
        return tuple(out)
    return f


def candidates(task):
    for diag in (False,True):
        for rule in RULES:
            for role_only in (True,False):
                m=infer_role_map(task,diag,rule,role_only)
                if m is not None:
                    name=f'roles:{8 if diag else 4}:{rule}:{"role" if role_only else "role+color"}'
                    yield name,program(diag,rule,m,role_only)


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v9_relational_roles.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; byrule=collections.Counter(); total=0
    for tid,t in sorted(tasks.items()):
        found=None; tried=0
        for name,p in candidates(t):
            tried+=1; total+=1
            try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
            except Exception: fit=False
            if fit:
                try: solved=run_v2.v1.task_solved(p,t)
                except Exception: solved=False
                found=(name,solved); break
        if found:
            name,solved=found; fits.append(tid)
            if solved: solves.append(tid)
            byrule[name.split(':')[2]]+=1
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else:
            rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-relational-roles.v9',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'residual_basis':{'v4_depth2_fits':0,'v7_local_fits':5,'v7_local_heldout_solves':0,'v8_single_object_fits':0,'interpretation':'After depth-2 whole-grid composition, local lookup, and single-object selection fail to transfer, introduce the smallest relational scene interface: select one object pair by a stable relation and infer output colors from pair roles.'},
      'declared_language':{'connectivity':[4,8],'pair_rules':RULES,'role_features':['A','B','OTHER','BG'],'mapping_variants':['role','role+input_color'],'output_shape':'same_as_input'},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'first_fit_pair_rule_counts':dict(byrule),'total_candidate_evaluations_until_first_fit_or_exhaustion':total,
      'strict_reachability_gain_over_v8':bool(fits),'strict_heldout_gain_over_v8':bool(solves),
      'rows':rows,
    }
    out=HERE/'results_v9_relational_roles'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
