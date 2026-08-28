import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v2',HERE/'run_v2.py')
v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)

# Preserve safe guard for partial programs.
_orig=v2.v1.infer_recolor
def safe_infer_recolor(pairs,pre=lambda x:x):
    for inp,_ in pairs:
        try:z=pre(inp)
        except Exception:return None
        if z is None:return None
    return _orig(pairs,pre=pre)
v2.v1.infer_recolor=safe_infer_recolor

TARGETS=['0c786b71','59341089','833dafe3','be03b35f']
FAMS=list(v2.NEW_BASE)
MAX_SECOND=25000


def apply(p,g):
    try:return p(g)
    except Exception:return None

def exact(p,pairs):
    try:return v2.v1.exact_on_pairs(p,pairs)
    except Exception:return False

def shape(g):return v2.v1.shape(g)
def colors(g):return v2.v1.colors(g)

# Deliberately low-level observation vocabulary. No family name, constructor name,
# depth label, or successful family-pair identity appears here. Each predicate is
# mechanically computed from transformed demonstrations and their required outputs.
def primitive_observations(tp):
    rows=[]
    for x,y in tp:
        hx,wx=shape(x);hy,wy=shape(y)
        cx,cy=colors(x),colors(y)
        ax=max(1,hx*wx);ay=max(1,hy*wy)
        rows.append({
            'h_eq':hx==hy,'w_eq':wx==wy,'shape_eq':(hx,wx)==(hy,wy),
            'shape_swap':(hx,wx)==(wy,hy),
            'h_le':hx<=hy,'w_le':wx<=wy,'h_ge':hx>=hy,'w_ge':wx>=wy,
            'area_eq':ax==ay,'area_divides':(max(ax,ay)%min(ax,ay)==0),
            'colors_eq':cx==cy,'xcolors_subset':cx<=cy,'ycolors_subset':cy<=cx,
            'ncolors_eq':len(cx)==len(cy),
            'height_parity_eq':(hx%2)==(hy%2),'width_parity_eq':(wx%2)==(wy%2),
        })
    keys=sorted(rows[0]) if rows else []
    # A task-level observation is whether the primitive relation holds on ALL demos.
    return {k:all(r[k] for r in rows) for k in keys}


def first_stage_states(task):
    pairs=v2.v1.task_pairs(task);out=[]
    for fam in FAMS:
        for name,p in v2.programs(fam,pairs):
            tp=[];ok=True
            for i,o in pairs:
                z=apply(p,i)
                if z is None:ok=False;break
                tp.append((z,o))
            if ok:
                out.append({'family_audit':fam,'program_audit':name,'p':p,'tp':tp,
                            'obs':primitive_observations(tp)})
    return out


def future_audit(task,state):
    # Future language is exactly one further lawful base continuation generated on
    # the transformed demonstrations. The quotient label is induced only by verifier
    # success, not by supplied family identities.
    pairs=v2.v1.task_pairs(task);tried=0;demo_fit=False;heldout=False;witness=None
    for fam in FAMS:
        for n2,p2 in v2.programs(fam,state['tp']):
            tried+=1
            if tried>MAX_SECOND:return demo_fit,heldout,witness,tried-1,True
            def comp(g,p1=state['p'],p2=p2):
                z=apply(p1,g);return None if z is None else apply(p2,z)
            if exact(comp,pairs):
                demo_fit=True
                solved=bool(v2.v1.task_solved(comp,task))
                if solved:
                    heldout=True;witness=(fam,n2);return demo_fit,heldout,witness,tried,False
                if witness is None:witness=(fam,n2)
    return demo_fit,heldout,witness,tried,False


def minimal_basis(states,label_key,max_k=5):
    if not states:return None
    keys=sorted(states[0]['obs'])
    def sufficient(sub):
        buckets=defaultdict(set)
        for s in states:
            sig=tuple(s['obs'][k] for k in sub)
            buckets[sig].add(bool(s[label_key]))
        return all(len(v)==1 for v in buckets.values())
    if sufficient(()):return []
    for k in range(1,min(max_k,len(keys))+1):
        for sub in itertools.combinations(keys,k):
            if sufficient(sub):return list(sub)
    return None


def quotient(states,label_key,basis):
    buckets=defaultdict(lambda:{'n':0,'labels':set(),'heldout_success':0})
    for s in states:
        sig=tuple(s['obs'][k] for k in basis) if basis is not None else ('UNRESOLVED',)
        b=buckets[str(sig)];b['n']+=1;b['labels'].add(bool(s[label_key]));b['heldout_success']+=int(s['heldout_success'])
    return {k:{**v,'labels':sorted(v['labels'])} for k,v in buckets.items()}


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v13_groundup_future_quotient.py EVAL')
    ev=v2.v1.load_tasks(sys.argv[1]);all_results=[]
    for tid in TARGETS:
        t=ev[tid];states=first_stage_states(t)
        for s in states:
            df,hs,w,tr,trunc=future_audit(t,s)
            s['demo_future_success']=df;s['heldout_success']=hs;s['future_witness_audit']=w;s['future_checks']=tr;s['truncated']=trunc
        basis_demo=minimal_basis(states,'demo_future_success')
        basis_held=minimal_basis(states,'heldout_success')
        # Certified collision for the old empty quotient if both labels occur.
        pos=[s for s in states if s['demo_future_success']];neg=[s for s in states if not s['demo_future_success']]
        collision=None
        if pos and neg:
            collision={
                'same_old_signature':[],
                'state_a_audit':pos[0]['program_audit'],'state_a_has_future':True,
                'state_b_audit':neg[0]['program_audit'],'state_b_has_future':False,
            }
        all_results.append({
            'task':tid,'first_stage_states':len(states),
            'demo_future_positive':sum(s['demo_future_success'] for s in states),
            'heldout_future_positive':sum(s['heldout_success'] for s in states),
            'any_truncation':any(s['truncated'] for s in states),
            'old_empty_quotient_collision':collision,
            'minimal_lowlevel_basis_demo_future':basis_demo,
            'minimal_lowlevel_basis_heldout_future':basis_held,
            'demo_quotient':quotient(states,'demo_future_success',basis_demo),
            'heldout_quotient':quotient(states,'heldout_success',basis_held),
        })
    # Cross-task forced basis: smallest common subset sufficient for demo-future labels
    # on every task, searched from the same primitive vocabulary.
    # Recompute compact states to avoid serializing programs.
    per=[];keys=None
    for tid in TARGETS:
        t=ev[tid];states=first_stage_states(t)
        for s in states:
            df,hs,_,_,_=future_audit(t,s);s['demo_future_success']=df;s['heldout_success']=hs
        per.append(states);keys=sorted(states[0]['obs']) if states else keys
    common=None
    def suff(states,sub,label):
        b=defaultdict(set)
        for s in states:b[tuple(s['obs'][k] for k in sub)].add(bool(s[label]))
        return all(len(v)==1 for v in b.values())
    for k in range(0,min(6,len(keys))+1):
        for sub in itertools.combinations(keys,k):
            if all(suff(st,sub,'demo_future_success') for st in per):common=list(sub);break
        if common is not None:break
    result={
        'schema':'verified-developmental-navigation.arc-groundup-future-quotient.v13',
        'question':'Starting below constructor labels, what low-level distinctions are forced by verified second-step futures?',
        'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
        'frozen_targets':TARGETS,'continuation_boundary':{'one further base-program continuation':True,'max_second_candidates_per_first_state':MAX_SECOND},
        'primitive_observation_vocabulary':keys,
        'tasks':all_results,'minimal_common_demo_future_basis_up_to_6':common,
        'interpretation_rule':{
            'emergence':'A nonempty minimal basis is admitted only because the empty/old quotient contains a verified future collision.',
            'obstruction':'If no basis <=6 exists, do not invent a higher concept; record LOWLEVEL_BASIS_EXHAUSTED and expand only after that exhaustion.'
        }
    }
    out=HERE/'results_v13_groundup_future_quotient';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
