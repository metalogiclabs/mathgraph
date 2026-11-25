"""A single integer polynomial for two independent rounding decisions.
Full sigmoid(2x) and tanh(x) slabs over the same complete interval.
"""
from synth import oracle,exact_eval
from joint import fit
import argparse,numpy as np, pathlib,json,hashlib,sys
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('baseline');p.add_argument('outdir');a=p.parse_args()
out=pathlib.Path(a.outdir);out.mkdir(exist_ok=True,parents=True)
src=pathlib.Path(a.baseline).read_text();assert hashlib.sha256(src.encode()).hexdigest()==BASE
f=oracle(a.reference,'sigmoid');g=oracle(a.reference,'tanh');start,end=0x3f800000,0x3fa00000;k,d,s=15,3,17;n=1<<k; t=(np.arange(n,dtype=np.int64)-n//2)<<(32-k)
rows=[];failed=[]
for lo in range(start,end,n):
 y=np.fromiter((f(w+0x800000) for w in range(lo,lo+n)),dtype=np.int64,count=n);z=np.fromiter((g(w) for w in range(lo,lo+n)),dtype=np.int64,count=n)
 assert np.all((y>=0x3f000000)&(y<0x3f800000)) and np.all((z>=0x3f000000)&(z<0x3f800000))
 base=int(y[n//2]);ys=y-base;yt=z-(2*base-0x3f800000)
 low4=np.maximum(4*ys,2*yt+1);high4=np.minimum(4*(ys+1),2*(yt+1)+1)
 r=fit(low4,high4,t,k,d,s);r['base']=base;r['start']=lo;rows.append(r)
 if r['status']!='exact':failed.append(lo)
 else:
  v=exact_eval(r['coeff'],t)
  assert np.array_equal(base+(v>>s),y)
  assert np.array_equal(2*base-0x3f800000+((v-(1<<(s-2)))>>(s-1)),z)
 if len(rows)%16==0:print('rows',len(rows),'exact',len(rows)-len(failed),flush=True)
(out/'joint-band.json').write_text(json.dumps({'rows':rows,'failed':failed,'k':k,'s':s,'start':start,'end':end},indent=2))
if failed:print('failed',list(map(hex,failed)));sys.exit(3)
for mode in ['unpacked','packed']:
 if mode=='unpacked':
  data='struct js_row { uint32_t base; int32_t c0,c1,c2,c3; };\n'
  vals=['{'+str(r['base'])+'u,'+','.join(map(str,r['coeff']))+'}' for r in rows]
  evalp='int32_t p=r->c2+mulhs_r(r->c3,t); p=r->c1+mulhs_r(p,t); return r->c0+mulhs_r(p,t);'
 else:
  data='struct js_row { uint32_t base; int32_t c1,c2; uint32_t aux; };\n';vals=[]
  for r in rows:
   c0,c1,c2,c3=r['coeff'];assert 0<=c0<2**17 and -2**14<=c3<2**14
   aux=((c3&0x7fff)<<17)|c0
   vals.append('{'+str(r['base'])+'u,'+str(c1)+','+str(c2)+','+str(aux)+'u}')
  evalp='uint32_t a=r->aux; int32_t c3=(int32_t)a>>17; int32_t p=r->c2+mulhs_r(c3,t); p=r->c1+mulhs_r(p,t); return (int32_t)(a&131071u)+mulhs_r(p,t);'
 data+='static const struct js_row js_rows[64]={\n'+',\n'.join(vals)+'\n};\n'
 data+='static inline int32_t js_value(const struct js_row *r,uint32_t w) { int32_t t=(int32_t)((w<<17)^0x80000000u); '+evalp+' }\n'
 marker='static inline uint32_t eik_tanh_r(uint32_t w)\n{';assert src.count(marker)==1
 cand=src.replace(marker,data+marker+'''\n    if ((w<<1)>>22==508u) { const struct js_row *r=&js_rows[(w>>15)&63u]; int32_t p=js_value(r,w); uint32_t a=2u*r->base-0x3f800000u+(uint32_t)((p-32768)>>16); return a|(w&0x80000000u); }''')
 # For the tanh word interval, w<<1 is [0x7f000000,0x7f400000),
 # whose top ten bits are 508. The test discards only the sign bit.
 marker='static inline uint32_t eik_sigmoid_r(uint32_t w)\n{';assert cand.count(marker)==1
 cand=cand.replace(marker,marker+'''\n    if ((w>>21)==512u) { const struct js_row *r=&js_rows[(w>>15)&63u]; int32_t p=js_value(r,w); return r->base+(uint32_t)(p>>17); }''')
 # 0x40000000 >> 21 == 512; interval ends at 0x40200000.
 (out/(mode+'.c')).write_text(cand);print(mode,hashlib.sha256(cand.encode()).hexdigest(),len(cand),flush=True)
