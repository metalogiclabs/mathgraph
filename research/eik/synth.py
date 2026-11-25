"""Offline rounding-slab synthesis using every output in a chosen cell.
The LP is a search heuristic; acceptance requires exact integer Horner replay.
"""
import argparse, ctypes as C, json, math, pathlib, itertools
import numpy as np
from scipy.optimize import linprog

def oracle(path, fn):
    lib=C.CDLL(str(pathlib.Path(path).resolve()));f=getattr(lib,'er_'+fn);f.argtypes=[C.c_uint32];f.restype=C.c_uint32
    return f

def exact_eval(c,t):
    p=np.full(t.shape,c[-1],dtype=np.int64)
    for a in c[-2::-1]:
        p=a+((p*t)>>32)
    return p

def synth(y,k,d,max_rounds=15,scale_bits=None):
    n=len(y); assert n==1<<k
    t=(np.arange(n,dtype=np.int64)-(n//2))<<(32-k)
    x=t.astype(np.float64)/2**31
    base=int(y[n//2]); y=y-base
    slope=(int(y[-1])-int(y[0]))/(x[-1]-x[0]); offset=(int(y[-1])+int(y[0])-slope*(x[-1]+x[0]))/2
    residual=y-(offset+slope*x)
    A=np.stack([x**j for j in range(d+1)],axis=1)
    inds=np.unique(np.linspace(0,n-1,min(65,n)).astype(int))
    s=max(0,min(28,int(math.floor(math.log2((2**30-1)/max(1,2*abs(slope),abs(offset)+abs(slope)))))))
    if scale_bits is not None:s=scale_bits
    scale=1<<s
    best=None; trials=0
    for it in range(max_rounds):
        sub=A[inds]; b=residual[inds]
        r=linprog(np.r_[np.zeros(d+1),-1.],A_ub=np.vstack([np.c_[sub,np.ones(len(inds))],np.c_[-sub,np.ones(len(inds))]]),b_ub=np.r_[b+1,-b],bounds=[(None,None)]*(d+2),method='highs')
        if not r.success:return {'status':'solver-unknown','scale':s,'iterations':it+1}
        if r.x[-1]<-1e-7:return {'status':'negative-real-subset','upper':float(r.x[-1]),'scale':s,'iterations':it+1}
        poly=r.x[:-1].copy();poly[0]+=offset;poly[1]+=slope
        ideal=A@r.x[:-1];slack=np.minimum(ideal-residual,residual+1-ideal)
        coeff=np.rint(poly*scale*2**np.arange(d+1)).astype(np.int64)
        if np.max(np.abs(coeff))>=2**31:return {'status':'coefficient-range','scale':s}
        if slack.min()>=-1e-8 or it==max_rounds-1:
            ds=[(0,)*d]+[tuple(delta if i==j else 0 for i in range(d)) for j in range(d) for delta in (-2,-1,1,2)]
            if d<=3:ds+=list(itertools.product((-1,0,1),repeat=d))
            for delta in ds:
                c=coeff.copy();c[1:]+=delta;c[0]=0
                bound=abs(int(c[-1]));ok=True
                for a in c[-2::-1]:
                    bound=abs(int(a))+(bound+1)//2
                    if bound>=2**31:ok=False;break
                if not ok:continue
                v=exact_eval(c,t);trials+=1
                lower=y*scale-v;lo=int(lower.max());hi=int(lower.min())+scale-1;gap=lo-hi
                if best is None or gap<best['gap']:
                    best={'gap':gap,'scale':s,'base':base,'iterations':it+1,'trials':trials,'ideal_margin':float(slack.min()),'coeff':list(map(int,c))}
                if lo<=hi:
                    c[0]=(lo+hi)//2
                    if abs(int(c[0]))+bound>=2**31:continue
                    assert np.array_equal(exact_eval(c,t)>>s,y)
                    return {'status':'exact','scale':s,'base':base,'coeff':list(map(int,c)), 'margin_lsb':hi-lo,'iterations':it+1,'trials':trials}
            if slack.min()>=-1e-8:break
        new=np.argpartition(slack,min(32,n-1))[:32];nxt=np.unique(np.r_[inds,new])
        if len(nxt)==len(inds):break
        inds=nxt
    return {'status':'integer-search-unknown',**(best or {'scale':s,'iterations':it+1,'trials':trials,'ideal_margin':float(slack.min())})}

def main():
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('--cells',default='16,64,112');p.add_argument('--ks',default='18,17,16,15,14');p.add_argument('--degrees',default='2,3');p.add_argument('--out',required=True);args=p.parse_args()
    f=oracle(args.reference,'sigmoid');res=[]
    for cell in map(int,args.cells.split(',')):
        start=(cell+0xf9c)<<18;n=1<<18
        y=np.fromiter((f(start+i) for i in range(n)),dtype=np.int64,count=n)
        for k in map(int,args.ks.split(',')):
            for d in map(int,args.degrees.split(',')):
                rows=[synth(y[j<<k:(j+1)<<k],k,d) for j in range(1<<(18-k))]
                record={'cell':cell,'start':start,'k':k,'degree':d,'total':len(rows),'exact':sum(r['status']=='exact' for r in rows),'rows':rows}
                res.append(record);pathlib.Path(args.out).write_text(json.dumps(res,indent=2));print(cell,k,d,record['exact'],record['total'],flush=True)
if __name__=='__main__':main()
