import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8


def mono_objects(g,diag=False):
    bg=v8.mode_color(g); h,w=run_v2.v1.shape(g)
    unseen={(i,j) for i in range(h) for j in range(w) if g[i][j]!=bg}
    dirs=[(-1,0),(1,0),(0,-1),(0,1)]
    if diag: dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
    out=[]
    while unseen:
        s=min(unseen); color=g[s[0]][s[1]]; unseen.remove(s); st=[s]; cc={s}
        while st:
            i,j=st.pop()
            for di,dj in dirs:
                q=(i+di,j+dj)
                if q in unseen and g[q[0]][q[1]]==color:
                    unseen.remove(q); cc.add(q); st.append(q)
        rs=[i for i,j in cc]; cs=[j for i,j in cc]
        box=(min(rs),max(rs),min(cs),max(cs))
        out.append({'pts':cc,'box':box,'size':len(cc),'shape':(box[1]-box[0]+1,box[3]-box[2]+1),'colors':(color,),'anchor':min(cc)})
    return bg,out


def scene_objects(g,seg,diag):
    return mono_objects(g,diag) if seg=='mono' else v8.objects(g,diag)


def center(o):
    a,b,c,d=o['box']; return ((a+b)/2.0,(c+d)/2.0)

def dist(p):
    a,b=p; x,y=center(a),center(b); return abs(x[0]-y[0])+abs(x[1]-y[1])

def unique_extreme(ps,key,want_max=False):
    if not ps:return None
    vals=[key(p) for p in ps]; target=max(vals) if want_max else min(vals)
    q=[p for p,v in zip(ps,vals) if v==target]
    return q[0] if len(q)==1 else None

def choose_pair(os,rule):
    ps=[(os[i],os[j]) for i in range(len(os)) for j in range(i+1,len(os))]
    if not ps:return None
    if rule=='closest':return unique_extreme(ps,dist)
    if rule=='farthest':return unique_extreme(ps,dist,True)
    if rule=='unique_same_shape':
        q=[p for p in ps if p[0]['shape']==p[1]['shape']]; return q[0] if len(q)==1 else None
    if rule=='unique_same_size':
        q=[p for p in ps if p[0]['size']==p[1]['size']]; return q[0] if len(q)==1 else None
    if rule=='unique_same_colors':
        q=[p for p in ps if p[0]['colors']==p[1]['colors']]; return q[0] if len(q)==1 else None
    if rule=='unique_same_row':
        q=[p for p in ps if center(p[0])[0]==center(p[1])[0]]; return q[0] if len(q)==1 else None
    if rule=='unique_same_col':
        q=[p for p in ps if center(p[0])[1]==center(p[1])[1]]; return q[0] if len(q)==1 else None
    if rule=='largest_pair':return unique_extreme(ps,lambda p:p[0]['size']+p[1]['size'],True)
    if rule=='smallest_pair':return unique_extreme(ps,lambda p:p[0]['size']+p[1]['size'])
    if rule=='most_color_pair':return unique_extreme(ps,lambda p:len(set(p[0]['colors'])|set(p[1]['colors'])),True)
    return None

RULES=['closest','farthest','unique_same_shape','unique_same_size','unique_same_colors','unique_same_row','unique_same_col','largest_pair','smallest_pair','most_color_pair']
SEGS=['mono','multicolor']


def role_grid(g,seg,diag,rule):
    _,os=scene_objects(g,seg,diag); p=choose_pair(os,rule)
    if p is None:return None
    a,b=sorted(p,key=lambda o:o['anchor']); apt,bpt=a['pts'],b['pts']
    allpts=set().union(*(o['pts'] for o in os)) if os else set(); other=allpts-apt-bpt
    h,w=run_v2.v1.shape(g); rows=[]
    for i in range(h):
        rr=[]
        for j in range(w):
            q=(i,j); rr.append('A' if q in apt else 'B' if q in bpt else 'OTHER' if q in other else 'BG')
        rows.append(tuple(rr))
    return tuple(rows)


def infer_map(task,seg,diag,rule,role_only):
    m={}
    for inp,out in run_v2.v1.task_pairs(task):
        if run_v2.v1.shape(inp)!=run_v2.v1.shape(out):return None
        roles=role_grid(inp,seg,diag,rule)
        if roles is None:return None
        for i,row in enumerate(inp):
            for j,x in enumerate(row):
                k=roles[i][j] if role_only else (roles[i][j],x); y=out[i][j]
                if k in m and m[k]!=y:return None
                m[k]=y
    return m

def make_program(seg,diag,rule,m,role_only):
    def f(g):
        roles=role_grid(g,seg,diag,rule)
        if roles is None:return None
        out=[]
        for i,row in enumerate(g):
            rr=[]
            for j,x in enumerate(row):
                k=roles[i][j] if role_only else (roles[i][j],x)
                if k not in m:return None
                rr.append(m[k])
            out.append(tuple(rr))
        return tuple(out)
    return f


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v9_relational_roles.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; byrule=collections.Counter(); valid=0; hypotheses=0
    for tid,t in sorted(tasks.items()):
        found=None; task_valid=0; task_hyp=0
        for seg in SEGS:
          for diag in (False,True):
           for rule in RULES:
            for role_only in (True,False):
                hypotheses+=1; task_hyp+=1
                m=infer_map(t,seg,diag,rule,role_only)
                if m is None:continue
                valid+=1; task_valid+=1
                p=make_program(seg,diag,rule,m,role_only)
                try:fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
                except Exception:fit=False
                if fit:
                    try:solved=run_v2.v1.task_solved(p,t)
                    except Exception:solved=False
                    found=(f'roles:{seg}:{8 if diag else 4}:{rule}:{"role" if role_only else "role+color"}',solved); break
            if found:break
           if found:break
          if found:break
        if found:
            name,solved=found; fits.append(tid); solves += [tid] if solved else []; byrule[name.split(':')[3]]+=1
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'hypotheses_attempted':task_hyp,'valid_candidate_evaluations':task_valid})
        else:rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'hypotheses_attempted':task_hyp,'valid_candidate_evaluations':task_valid})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-relational-roles.v9b',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'residual_basis':{'v4_depth2_fits':0,'v7_local_fits':5,'v7_local_heldout_solves':0,'v8_single_object_fits':0,'v9a_valid_candidates':0,'interpretation':'V9a showed that multicolor connectivity often failed even to expose a stable pair-role program. Add monochrome connected components as a segmentation portal while keeping pair rules and role mapping fixed.'},
      'declared_language':{'segmentation':SEGS,'connectivity':[4,8],'pair_rules':RULES,'role_features':['A','B','OTHER','BG'],'mapping_variants':['role','role+input_color'],'output_shape':'same_as_input'},
      'hypotheses_attempted':hypotheses,'valid_candidate_evaluations':valid,'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'first_fit_pair_rule_counts':dict(byrule),
      'strict_reachability_gain_over_v8':bool(fits),'strict_heldout_gain_over_v8':bool(solves),'rows':rows}
    out=HERE/'results_v9_relational_roles'; out.mkdir(exist_ok=True); (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__':main()
