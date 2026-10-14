import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8


def mono_objects(g,diag=False):
    bg=v8.mode_color(g); h,w=run_v2.v1.shape(g)
    dirs=[(-1,0),(1,0),(0,-1),(0,1)]
    if diag: dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
    unseen={(i,j) for i in range(h) for j in range(w) if g[i][j]!=bg}
    out=[]
    while unseen:
        seed=min(unseen); color=g[seed[0]][seed[1]]; unseen.remove(seed); st=[seed]; cc={seed}
        while st:
            i,j=st.pop()
            for di,dj in dirs:
                q=(i+di,j+dj)
                if q in unseen and g[q[0]][q[1]]==color:
                    unseen.remove(q); cc.add(q); st.append(q)
        rs=[i for i,j in cc]; cs=[j for i,j in cc]
        box=(min(rs),max(rs),min(cs),max(cs)); a,b,c,d=box
        rel=tuple(sorted((i-a,j-c) for i,j in cc))
        out.append({'pts':cc,'box':box,'size':len(cc),'shape':(b-a+1,d-c+1),'colors':(color,), 'anchor':min(cc),'norm_shape':rel})
    return bg,out


def multi_objects(g,diag=False):
    bg,os=v8.objects(g,diag)
    out=[]
    for o in os:
        a,b,c,d=o['box']
        rel=tuple(sorted((i-a,j-c) for i,j in o['pts']))
        q=dict(o); q['norm_shape']=rel; out.append(q)
    return bg,out


def object_scene(g,diag,seg):
    bg,os=(mono_objects(g,diag) if seg=='mono' else multi_objects(g,diag))
    shape_counts=collections.Counter(o['norm_shape'] for o in os)
    size_counts=collections.Counter(o['size'] for o in os)
    color_counts=collections.Counter(o['colors'] for o in os)
    row_counts=collections.Counter((o['box'][0]+o['box'][1])/2 for o in os)
    col_counts=collections.Counter((o['box'][2]+o['box'][3])/2 for o in os)
    rank_size={id(o):r for r,o in enumerate(sorted(os,key=lambda z:(z['size'],z['anchor'])))}
    feat={}
    for o in os:
        cr=(o['box'][0]+o['box'][1])/2; cc=(o['box'][2]+o['box'][3])/2
        feat[id(o)]={
          'shape_mult':shape_counts[o['norm_shape']],
          'size_mult':size_counts[o['size']],
          'color_mult':color_counts[o['colors']],
          'row_mult':row_counts[cr],
          'col_mult':col_counts[cc],
          'size_rank':rank_size[id(o)],
          'is_shape_unique':shape_counts[o['norm_shape']]==1,
          'is_shape_repeated':shape_counts[o['norm_shape']]>1,
          'is_size_unique':size_counts[o['size']]==1,
          'is_size_repeated':size_counts[o['size']]>1,
        }
    owner={p:o for o in os for p in o['pts']}
    return bg,os,owner,feat

SCHEMES=[
 ('shape_mult',),('size_mult',),('color_mult',),('row_mult',),('col_mult',),
 ('is_shape_unique',),('is_shape_repeated',),('is_size_unique',),('is_size_repeated',),
 ('shape_mult','size_mult'),('shape_mult','color_mult'),('shape_mult','row_mult','col_mult'),
 ('size_mult','row_mult','col_mult'),('shape_mult','size_mult','color_mult'),
]


def feature_grid(g,diag,seg,scheme,with_color):
    bg,os,owner,feat=object_scene(g,diag,seg); h,w=run_v2.v1.shape(g); rows=[]
    for i in range(h):
        row=[]
        for j in range(w):
            o=owner.get((i,j))
            if o is None: key=('BG',)
            else: key=('OBJ',)+tuple(feat[id(o)][x] for x in scheme)
            if with_color: key=key+(g[i][j],)
            row.append(key)
        rows.append(tuple(row))
    return tuple(rows)


def infer_map(task,diag,seg,scheme,with_color,background_passthrough):
    m={}
    for inp,out in run_v2.v1.task_pairs(task):
        if run_v2.v1.shape(inp)!=run_v2.v1.shape(out): return None
        fg=feature_grid(inp,diag,seg,scheme,with_color)
        for i,row in enumerate(inp):
            for j,x in enumerate(row):
                key=fg[i][j]
                if background_passthrough and key[0]=='BG':
                    if out[i][j]!=x: return None
                    continue
                y=out[i][j]
                if key in m and m[key]!=y: return None
                m[key]=y
    return m


def make_program(diag,seg,scheme,with_color,background_passthrough,m):
    def f(g):
        fg=feature_grid(g,diag,seg,scheme,with_color); out=[]
        for i,row in enumerate(g):
            rr=[]
            for j,x in enumerate(row):
                key=fg[i][j]
                if background_passthrough and key[0]=='BG': rr.append(x)
                elif key in m: rr.append(m[key])
                else: return None
            out.append(tuple(rr))
        return tuple(out)
    return f


def candidates(task):
    for diag in (False,True):
      for seg in ('mono','multicolor'):
       for scheme in SCHEMES:
        for with_color in (False,True):
         for bgpass in (False,True):
          m=infer_map(task,diag,seg,scheme,with_color,bgpass)
          if m is not None:
            name=f'class:{seg}:{8 if diag else 4}:{"+".join(scheme)}:{"color" if with_color else "nocolor"}:{"bgpass" if bgpass else "bgmap"}'
            yield name,make_program(diag,seg,scheme,with_color,bgpass,m)


def main():
    if len(sys.argv)!=2: raise SystemExit('usage run_v11_multiobject_classes.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; fits=[]; solves=[]; total=0; valid=0; fam=collections.Counter()
    for tid,t in sorted(tasks.items()):
        found=None; tried=0
        for name,p in candidates(t):
            valid+=1; tried+=1; total+=1
            try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
            except Exception: fit=False
            if fit:
                try: solved=run_v2.v1.task_solved(p,t)
                except Exception: solved=False
                found=(name,solved); break
        if found:
            name,solved=found; fits.append(tid)
            if solved: solves.append(tid)
            fam[name.split(':')[3]]+=1
            rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
        else: rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-multiobject-classes.v11',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{
        'prior_residuals':[
          'depth2 whole-grid closure: 0/120 demonstration fits',
          'local observation: 5/120 demonstration fits but 0 held-out solves',
          'single selected object: 0/120 fits',
          'selected object pair roles/interactions: 0/120 fits'
        ],
        'diagnosis':'The loop itself has repeatedly selected a single locus (grid, cell, object, pair). Preserve the evidence that representation matters, but change the abstraction axis from selecting one locus to quotienting the whole object set into repeated/unique equivalence classes.',
        'next_move':'EXTEND_OBSERVATION: multi-object equivalence-class roles; do not add search depth or another pair action.'
      },
      'declared_language':{'segmentation':['mono','multicolor'],'connectivity':[4,8],'class_features':[list(x) for x in SCHEMES],'mapping_variants':['class','class+input_color'],'background':['mapped','passthrough'],'output_shape':'same_as_input'},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,
      'valid_candidate_programs':valid,'candidate_evaluations':total,'first_fit_scheme_counts':dict(fam),
      'strict_reachability_gain_over_v10':bool(fits),'strict_heldout_gain_over_v10':bool(solves),
      'rows':rows,
    }
    out=HERE/'results_v11_multiobject_classes'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
