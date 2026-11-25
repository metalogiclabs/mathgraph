"""Shared integer rounding slabs for sigma(2x) and tanh(x), x in [1,1.25).
Units are a quarter of one positive sigmoid output ULP. Search uses all
reference outputs in contiguous cells; numerical LP is a heuristic only.
"""
from synth import oracle,exact_eval
import numpy as np
from scipy.optimize import linprog
import itertools,json,pathlib,sys

def fit(low4,high4,t,k,d,s):
    n=len(t); assert n==1<<k and s>=2
    x=t.astype(np.float64)/2**31
    low=low4/4; high=high4/4
    assert np.all(low4<high4)
    y=(low+high)/2
    slope=(y[-1]-y[0])/(x[-1]-x[0]);offset=(y[0]+y[-1]-slope*(x[0]+x[-1]))/2
    line=offset+slope*x;lo=low-line;hi=high-line
    A=np.stack([x**j for j in range(d+1)],axis=1)
    inds=np.unique(np.linspace(0,n-1,65).astype(int));scale=1<<s
    for it in range(20):
        sub=A[inds]; r=linprog(np.r_[np.zeros(d+1),-1.],A_ub=np.vstack([np.c_[sub,np.ones(len(inds))],np.c_[-sub,np.ones(len(inds))]]),b_ub=np.r_[hi[inds],-lo[inds]],bounds=[(None,None)]*(d+2),method='highs')
        if not r.success:return {'status':'solver-unknown'}
        if r.x[-1]<-1e-7:return {'status':'negative-real-subset','margin':float(r.x[-1])}
        v=A@r.x[:-1];slack=np.minimum(v-lo,hi-v)
        poly=r.x[:-1].copy();poly[0]+=offset;poly[1]+=slope
        coeff=np.rint(poly*scale*2**np.arange(d+1)).astype(np.int64)
        if np.max(np.abs(coeff))>=2**31:return {'status':'coefficient-range'}
        if slack.min()>=-1e-8 or it==19:
            ds=[(0,)*d]+[tuple(delta if i==j else 0 for i in range(d)) for j in range(d) for delta in (-2,-1,1,2)]+list(itertools.product((-1,0,1),repeat=d))
            for delta in ds:
                c=coeff.copy();c[1:]+=delta;c[0]=0
                bound=abs(int(c[-1]));ok=True
                for a in c[-2::-1]:
                    bound=abs(int(a))+(bound+1)//2
                    if bound>=2**31:ok=False;break
                if not ok:continue
                p=exact_eval(c,t);ll=int((low4*(scale//4)-p).max());hh=int((high4*(scale//4)-1-p).min())
                if ll<=hh:
                    c[0]=(ll+hh)//2
                    if abs(int(c[0]))+bound>=2**31:continue
                    p=exact_eval(c,t);assert np.all(p>=low4*(scale//4)) and np.all(p<high4*(scale//4))
                    return {'status':'exact','coeff':list(map(int,c)),'margin_lsb':hh-ll}
            if slack.min()>=-1e-8:break
        nxt=np.unique(np.r_[inds,np.argpartition(slack,32)[:32]])
        if len(nxt)==len(inds):break
        inds=nxt
    return {'status':'integer-search-unknown'}

def main():
 f=oracle(sys.argv[1],'sigmoid');g=oracle(sys.argv[1],'tanh');results=[]
 for start in [0x3f800000,0x3f900000,0x3f9c0000]:
  n=1<<18;y=np.fromiter((f(w+0x800000) for w in range(start,start+n)),dtype=np.int64,count=n);z=np.fromiter((g(w) for w in range(start,start+n)),dtype=np.int64,count=n)
  assert np.all((y>=0x3f000000)&(y<0x3f800000)) and np.all((z>=0x3f000000)&(z<0x3f800000))
  for k,d,s in [(16,3,16),(15,3,17),(14,2,18),(13,2,19)]:
   rows=[];q=1<<k; t=(np.arange(q,dtype=np.int64)-q//2)<<(32-k)
   for i in range(0,n,q):
    a=y[i:i+q];b=z[i:i+q];base=int(a[q//2]);ys=a-base;yt=b-(2*base-0x3f800000)
    low4=np.maximum(4*ys,2*yt+1);high4=np.minimum(4*(ys+1),2*(yt+1)+1)
    r=fit(low4,high4,t,k,d,s);r['base']=base;rows.append(r)
    if r['status']=='exact':
     p=exact_eval(r['coeff'],t);assert np.array_equal(base+(p>>s),a);assert np.array_equal(2*base-0x3f800000+((p-(1<<(s-2)))>>(s-1)),b)
   rec={'start':start,'k':k,'degree':d,'scale':s,'exact':sum(r['status']=='exact' for r in rows),'total':len(rows),'rows':rows};results.append(rec);print(hex(start),k,d,s,rec['exact'],rec['total'],flush=True)
   pathlib.Path(sys.argv[2]).write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
