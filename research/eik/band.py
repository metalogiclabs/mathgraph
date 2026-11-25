import argparse,ctypes as C, json, pathlib,hashlib,sys
import numpy as np
from synth import synth,oracle
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('baseline');p.add_argument('output');p.add_argument('--start',type=lambda s:int(s,0),default=0x3f800000);p.add_argument('--end',type=lambda s:int(s,0),default=0x40000000);p.add_argument('--k',type=int,default=15);p.add_argument('--d',type=int,default=2);p.add_argument('--scale',type=int,default=17);a=p.parse_args()
s=pathlib.Path(a.baseline).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
f=oracle(a.reference,'sigmoid'); rows=[];fail=[]; n=1<<a.k; assert a.start%n==a.end%n==0
for lo in range(a.start,a.end,n):
    y=np.fromiter((f(lo+i) for i in range(n)),dtype=np.int64,count=n)
    r=synth(y,a.k,a.d,scale_bits=a.scale);r['start']=lo;rows.append(r)
    if r['status']!='exact':fail.append(lo)
    if len(rows)%32==0:print('rows',len(rows),'exact',len(rows)-len(fail),flush=True)
pathlib.Path(a.output+'.json').write_text(json.dumps({'start':a.start,'end':a.end,'degree':a.d,'k':a.k,'scale':a.scale,'rows':rows,'failed':fail},indent=2))
print('summary',len(rows)-len(fail),len(rows),'exact; failed',list(map(hex,fail)),flush=True)
if fail:sys.exit(3)
# No fallback, one uniform table, no special hard inputs.
struct='struct isyn_row { uint32_t base; int32_t '+','.join('c'+str(i) for i in range(a.d+1))+'; };\n'
table=f'static const struct isyn_row isyn[{len(rows)}]={{\n'+',\n'.join('{'+str(r['base'])+'u,'+','.join(map(str,r['coeff']))+'}' for r in rows)+'\n};\n'
body=f'''static inline uint32_t isyn_sigmoid(uint32_t w) {{
    const struct isyn_row *r=&isyn[(w>>{a.k})-{a.start>>a.k}u];
    int32_t t=(int32_t)((w<<{32-a.k})^0x80000000u);
    int32_t p=r->c{a.d};
'''+''.join(f'    p=r->c{i}+mulhs_r(p,t);\n' for i in range(a.d-1,-1,-1))+f'    return r->base+(uint32_t)(p>>{a.scale});\n}}\n'
marker='static inline uint32_t eik_sigmoid_r(uint32_t w)\n{';assert s.count(marker)==1
s=s.replace(marker,struct+table+body+marker+f'\n    if(w>=0x{a.start:08x}u && w<0x{a.end:08x}u) return isyn_sigmoid(w);')
pathlib.Path(a.output).write_text(s);print('source',hashlib.sha256(s.encode()).hexdigest(),len(s))
