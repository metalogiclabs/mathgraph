import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v9_relational_roles as v9

DRAW_ACTIONS=['connect_centers','pair_bbox_border','pair_bbox_fill']
COPY_ACTIONS=['copy_a_beyond_b','copy_b_before_a','move_a_beyond_b','move_b_before_a']


def selected(g,seg,diag,rule):
    _,os=v9.scene_objects(g,seg,diag); p=v9.choose_pair(os,rule)
    if p is None:return None
    return tuple(sorted(p,key=lambda o:o['anchor']))

def setcell(rows,i,j,c):
    if 0<=i<len(rows) and 0<=j<len(rows[0]):rows[i][j]=c

def line_points(a,b):
    ai,aj=a; bi,bj=b; di=bi-ai; dj=bj-aj
    if di==0: return [(ai,j) for j in range(min(aj,bj),max(aj,bj)+1)]
    if dj==0: return [(i,aj) for i in range(min(ai,bi),max(ai,bi)+1)]
    if abs(di)==abs(dj):
        si=1 if di>0 else -1; sj=1 if dj>0 else -1
        return [(ai+k*si,aj+k*sj) for k in range(abs(di)+1)]
    return None

def int_center(o):
    x,y=v9.center(o)
    if int(x)!=x or int(y)!=y:return None
    return (int(x),int(y))

def draw_program(seg,diag,rule,action,color):
    def f(g):
        p=selected(g,seg,diag,rule)
        if p is None:return None
        a,b=p; rows=[list(r) for r in g]
        if action=='connect_centers':
            ca,cb=int_center(a),int_center(b)
            if ca is None or cb is None:return None
            pts=line_points(ca,cb)
            if pts is None:return None
            for i,j in pts:setcell(rows,i,j,color)
        else:
            aa,ab,ac,ad=a['box']; ba,bb,bc,bd=b['box']
            r0,r1,c0,c1=min(aa,ba),max(ab,bb),min(ac,bc),max(ad,bd)
            if action=='pair_bbox_fill':
                for i in range(r0,r1+1):
                    for j in range(c0,c1+1):setcell(rows,i,j,color)
            elif action=='pair_bbox_border':
                for j in range(c0,c1+1):setcell(rows,r0,j,color); setcell(rows,r1,j,color)
                for i in range(r0,r1+1):setcell(rows,i,c0,color); setcell(rows,i,c1,color)
        return tuple(tuple(r) for r in rows)
    return f

def copy_program(seg,diag,rule,action):
    def f(g):
        p=selected(g,seg,diag,rule)
        if p is None:return None
        a,b=p; rows=[list(r) for r in g]
        va=(b['anchor'][0]-a['anchor'][0],b['anchor'][1]-a['anchor'][1])
        if action in ('copy_a_beyond_b','move_a_beyond_b'):
            src=a; dr,dc=va; clear=action.startswith('move')
        else:
            src=b; dr,dc=-va[0],-va[1]; clear=action.startswith('move')
        targets=[(i+dr,j+dc,g[i][j]) for i,j in src['pts']]
        if any(not (0<=i<len(g) and 0<=j<len(g[0])) for i,j,_ in targets):return None
        if clear:
            bg=v9.v8.mode_color(g)
            for i,j in src['pts']:rows[i][j]=bg
        for i,j,c in targets:rows[i][j]=c
        return tuple(tuple(r) for r in rows)
    return f

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v10_relational_actions.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; fam=collections.Counter(); total=0
    for tid,t in sorted(tasks.items()):
        found=None; tried=0
        pairs=run_v2.v1.task_pairs(t)
        # This interaction language is intentionally same-shape only.
        if all(run_v2.v1.shape(i)==run_v2.v1.shape(o) for i,o in pairs):
          for seg in v9.SEGS:
           for diag in (False,True):
            for rule in v9.RULES:
             for action in DRAW_ACTIONS:
              for color in range(10):
                tried+=1; total+=1; p=draw_program(seg,diag,rule,action,color)
                try:fit=run_v2.v1.exact_on_pairs(p,pairs)
                except Exception:fit=False
                if fit:
                    try:solved=run_v2.v1.task_solved(p,t)
                    except Exception:solved=False
                    found=(f'interact:{seg}:{8 if diag else 4}:{rule}:{action}:{color}',solved); break
              if found:break
             if found:break
             for action in COPY_ACTIONS:
                tried+=1; total+=1; p=copy_program(seg,diag,rule,action)
                try:fit=run_v2.v1.exact_on_pairs(p,pairs)
                except Exception:fit=False
                if fit:
                    try:solved=run_v2.v1.task_solved(p,t)
                    except Exception:solved=False
                    found=(f'interact:{seg}:{8 if diag else 4}:{rule}:{action}',solved); break
             if found:break
            if found:break
           if found:break
        if found:
            name,solved=found; fits.append(tid); solves += [tid] if solved else []; fam[name.split(':')[4]]+=1
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else:rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={'schema':'verified-developmental-navigation.arc-agi2-relational-actions.v10','source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},'residual_basis':{'v9b_hypotheses':9600,'v9b_valid_role_maps':0,'interpretation':'Pair roles alone are insufficient: no global role/role+color map fits any task. Keep the relational scene and add only explicit pair interactions that can change spatial structure.'},'declared_language':{'segmentation':v9.SEGS,'connectivity':[4,8],'pair_rules':v9.RULES,'draw_actions':DRAW_ACTIONS,'draw_colors':list(range(10)),'copy_actions':COPY_ACTIONS,'output_shape':'same_as_input'},'candidate_evaluations':total,'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'first_fit_action_counts':dict(fam),'strict_reachability_gain_over_v9':bool(fits),'strict_heldout_gain_over_v9':bool(solves),'rows':rows}
    out=HERE/'results_v10_relational_actions'; out.mkdir(exist_ok=True); (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)); print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__':main()
