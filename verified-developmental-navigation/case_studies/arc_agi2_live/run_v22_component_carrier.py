import collections, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8

# Meta-loop response to V18-V21: literal shape unions and hand-composed spatial
# relations did not preserve the training semantics. Move one level toward an
# induced object criterion: a payload is a cell surrounded in all four cardinal
# directions by one carrier color whose entire 8-connected carrier component is
# local and bounded. This defines the object by support topology, not ring/cross name.

def component(g,start,color):
  h,w=run_v2.v1.shape(g);seen={start};st=[start]
  while st:
    i,j=st.pop()
    for di in (-1,0,1):
      for dj in (-1,0,1):
        if di==0 and dj==0:continue
        q=(i+di,j+dj)
        if 0<=q[0]<h and 0<=q[1]<w and q not in seen and g[q[0]][q[1]]==color:
          seen.add(q);st.append(q)
  return seen

def detect(g):
  bg=v8.mode_color(g);h,w=run_v2.v1.shape(g);cand=[]
  for i in range(1,h-1):
    for j in range(1,w-1):
      card=[g[i-1][j],g[i+1][j],g[i][j-1],g[i][j+1]];c=g[i][j]
      if len(set(card))!=1 or card[0]==bg or c==card[0]:continue
      b=card[0]; comp=component(g,(i-1,j),b)
      # Carrier must be a small self-contained support around payload.
      if not (4<=len(comp)<=8):continue
      if not all(abs(a-i)<=1 and abs(q-j)<=1 for a,q in comp):continue
      if not {(i-1,j),(i+1,j),(i,j-1),(i,j+1)} <= comp:continue
      pts=set(comp)|{(i,j)}
      cand.append({'center_pt':(i,j),'anchor':min(pts),'pts':pts,'border':b,'center':c,'carrier_size':len(comp)})
  cand.sort(key=lambda o:o['anchor']);out=[];used=set()
  for o in cand:
    if not(o['pts']&used):out.append(o);used|=o['pts']
  return bg,out

def chains(g):
  bg,nodes=detect(g);by=collections.defaultdict(list)
  for k,o in enumerate(nodes):by[o['border']].append(k)
  succ={};indeg=[0]*len(nodes)
  for k,o in enumerate(nodes):
    qs=[q for q in by.get(o['center'],[]) if q!=k]
    if len(qs)==1:succ[k]=qs[0];indeg[qs[0]]+=1
  roots=[k for k,d in enumerate(indeg) if d==0];seen=set();chs=[]
  for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
    ch=[];cur=r
    while cur not in seen:
      seen.add(cur);ch.append(cur)
      if cur not in succ:break
      cur=succ[cur]
    chs.append(ch)
  if len(nodes)<2 or len(seen)!=len(nodes):return None
  return bg,nodes,chs

def program(tail='delete'):
  def f(g):
    q=chains(g)
    if q is None:return None
    bg,nodes,chs=q;z=[list(r) for r in g]
    for ch in chs:
      k=0
      while k<len(ch):
        a=ch[k]
        if k+1<len(ch):
          b=ch[k+1];ci,cj=nodes[a]['center_pt'];z[ci][cj]=nodes[b]['center']
          for p,r in nodes[b]['pts']:z[p][r]=bg
          k+=2
        else:
          if tail=='delete':
            for p,r in nodes[a]['pts']:z[p][r]=bg
          k+=1
    return tuple(tuple(r) for r in z)
  return f

def main():
  if len(sys.argv)!=2:raise SystemExit('usage run_v22_component_carrier.py EVAL_DIR')
  tasks=run_v2.v1.load_tasks(sys.argv[1]);V=[('component-delete',program('delete')),('component-keep',program('keep'))]
  fits=[];solves=[];rows=[]
  for tid,t in sorted(tasks.items()):
    fp=[];sp=[]
    for n,p in V:
      try:fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
      except Exception:fit=False
      if fit:
        fp.append(n)
        try:
          if run_v2.v1.task_solved(p,t):sp.append(n)
        except Exception:pass
    if fp:fits.append(tid)
    if sp:solves.append(tid)
    rows.append({'task':tid,'fit_programs':fp,'heldout_solved_programs':sp})
  result={'schema':'verified-developmental-navigation.arc-agi2-component-carrier.v22','evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR',
   'meta_move':'REDEFINE_OBJECT_BY_SUPPORT_TOPOLOGY: payload + bounded local carrier component, rather than named ring/cross shapes',
   'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,
   'trigger_task_solved':'d35bdbdc' in solves,'source_distinct_solved_ids':[x for x in solves if x!='d35bdbdc'],'rows':rows,
   'claim_boundary':'Known-world diagnostic. Protected source-distinct transfer is required for capability evidence.'}
  out=HERE/'results_v22_component_carrier';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
  print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
