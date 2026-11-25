"""Numerical feasibility probe; run offline, not part of submitted code.
Usage: python rounding_feasibility.py path/to/rrr.so
Requires NumPy and SciPy. Baseline source SHA256:
3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4.
Source archived in run 45545248898, artifact 14990707573.
Model is ideal real polynomial, not bit-exact integer Horner.
"""
import ctypes as C
import sys, json
import numpy as np
import scipy.optimize as so
lib=C.CDLL(sys.argv[1])
f=lib.eik_sigmoid
f.argtypes=[C.c_uint32]; f.restype=C.c_uint32
results=[]
for cell in [16,64,112]:
    lo=(cell+0xf9c)<<18; N=1<<18
    w=np.arange(lo,lo+N,dtype=np.uint32)
    y=np.fromiter((f(int(v))-0x3f000000 for v in w),dtype=np.int64,count=N)
    x=np.linspace(-1.,1.,N)
    line=(y[-1]+y[0])/2+(y[-1]-y[0])*x/2
    a=y-line
    for d in [2,3,4]:
        A=np.stack([x**j for j in range(d+1)],axis=1)
        inds=np.unique(np.linspace(0,N-1,129).astype(int))
        margin=None; upper=None
        for it in range(60):
            sub=A[inds]; b=a[inds]
            r=so.linprog(np.r_[np.zeros(d+1),-1.],
              A_ub=np.vstack([np.c_[sub,np.ones(len(inds))],np.c_[-sub,np.ones(len(inds))]]),
              b_ub=np.r_[b+1,-b],bounds=[(None,None)]*(d+2),method='highs')
            if not r.success: break
            v=A@r.x[:-1]; slack=np.minimum(v-a,a+1-v)
            margin=float(slack.min()); upper=float(r.x[-1])
            if upper < -1e-7 or margin>=-1e-8:break
            new=np.argpartition(slack, min(64,N-1))[:64]
            ids=np.unique(np.r_[inds,new])
            if len(ids)==len(inds):break
            inds=ids
        res={'cell':cell,'degree':d,'words':N,'solver_success':bool(r.success),
             'iterations':it+1,'constraints':len(inds),
             'full_cell_margin_output_ulps':margin,'sample_optimum_upper_bound':upper,
             'status':'numerically feasible real polynomial' if r.success and margin>=-1e-8
             else ('negative subset optimum' if r.success and upper < -1e-7 else 'unknown')}
        results.append(res); print(json.dumps(res),flush=True)
# Observed 2026-11-25 (NumPy 2.3.5, SciPy 1.17.0):
# cell    degree 2             degree 3             degree 4
# 16      negative            feasible             feasible
# 64      negative            feasible             feasible
# 112     negative            negative             feasible
# positive full-cell margins in output ULPs:
# 16 d3 1.9700993680871193e-6; d4 3.904470247562131e-6
# 64 d3 2.659254136005984e-6; d4 1.4556705700385919e-5
# 112 d4 9.368827278422032e-6
# subset optimum negative margins (numerical, not rational certificates):
# 16 d2 -0.004174691508157302
# 64 d2 -0.0011727687280398413
# 112 d2 -0.6741363711278439; d3 -0.0002788690916872838
# All 786432 distinct baseline outputs independently compared to the
# kit's vendored exact-c er_sigmoid, zero discrepancies.
# No integer polynomial generated, no speed result or global impossibility claim.
