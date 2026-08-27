import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2


def mode(xs):
    c=collections.Counter(xs)
    return c.most_common(1)[0][0] if c else None

def comps(g,bg=None):
    if bg is None: bg=mode([x for r in g for x in r])
    pts={(i,j) for i,r in enumerate(g) for j,x in enumerate(r) if x!=bg}
    out=[]
    while pts:
        seed=min(pts); stack=[seed]; pts.remove(seed); cc={seed}
        while stack:
            i,j=stack.pop()
            for q in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if q in pts: pts.remove(q); cc.add(q); stack.append(q)
        out.append(cc)
    return out

def bbox_shape(cc):
    if not cc: return (0,0)
    rs=[i for i,j in cc]; cs=[j for i,j in cc]
    return (max(rs)-min(rs)+1,max(cs)-min(cs)+1)

def pair_features(inp,out):
    hi,wi=run_v2.v1.shape(inp); ho,wo=run_v2.v1.shape(out)
    ci=run_v2.v1.colors(inp); co=run_v2.v1.colors(out)
    bgi=mode([x for r in inp for x in r]); bgo=mode([x for r in out for x in r])
    ici=comps(inp,bgi); oci=comps(out,bgo)
    return {
      'same_shape':(hi,wi)==(ho,wo),
      'smaller':ho<=hi and wo<=wi and (ho,wo)!=(hi,wi),
      'larger':ho>=hi and wo>=wi and (ho,wo)!=(hi,wi),
      'mixed_shape':not ((hi,wi)==(ho,wo) or (ho<=hi and wo<=wi) or (ho>=hi and wo>=wi)),
      'same_colors':ci==co,
      'output_colors_subset':co<=ci,
      'new_output_color':bool(co-ci),
      'input_colors_subset':ci<=co,
      'same_ncolors':len(ci)==len(co),
      'same_nonbg_components':len(ici)==len(oci),
      'input_multiobject':len(ici)>=2,
      'output_multiobject':len(oci)>=2,
      'output_shape_matches_input_component_bbox':(ho,wo) in {bbox_shape(c) for c in ici},
      'output_area_ratio_integer': (hi*wi>0 and ho*wo>0 and ((ho*wo)%(hi*wi)==0 or (hi*wi)%(ho*wo)==0)),
    }

def task_signature(task):
    fs=[pair_features(tuple(map(tuple,x['input'])),tuple(map(tuple,x['output']))) for x in task['train']]
    keys=fs[0].keys()
    alltrue={k:all(f[k] for f in fs) for k in keys}
    return tuple(sorted(k for k,v in alltrue.items() if v)), alltrue

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: run_v6_arc2_residual_census.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1])
    counts=collections.Counter(); sigs=collections.Counter(); examples=collections.defaultdict(list)
    rows=[]
    for tid,t in sorted(tasks.items()):
        sig,feat=task_signature(t); sigs[sig]+=1
        for k,v in feat.items(): counts[k]+=int(v)
        examples[sig].append(tid)
        rows.append({'task':tid,'all_demo_features':[k for k,v in feat.items() if v]})
    result={
      'schema':'verified-developmental-navigation.arc-agi2-residual-census.v6',
      'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'context':'V4 exhaustively found zero demonstration fits in 876,264 bounded depth-2 candidates with no truncation; this census localizes the representation residual using only demonstration pairs.',
      'feature_task_counts':dict(counts),
      'signature_count':len(sigs),
      'top_signatures':[{'count':n,'features':list(sig),'examples':examples[sig][:8]} for sig,n in sigs.most_common(20)],
      'rows':rows,
    }
    out=HERE/'results_v6_residual_census'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))

if __name__=='__main__': main()
