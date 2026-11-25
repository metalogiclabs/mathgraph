"""Exact range-bounded portable exp arithmetic, no scorer-dependent choices."""
import hashlib,pathlib,re,sys,json
BASE='0b02a1ad26d312dc79aa371b24ad43833c04ebc4371d06e9fcf89ecdfbe83ab7'
REGIONS=[(0xbc000001,0xbe800000,21,-(376<<2),11),(0xbe800000,0xc0000000,18,20-(381<<5),14),(0xc0000000,0xc0800001,17,20-(384<<6)+96,15)]
VARIANTS=['range','nx-limb','nx-narrow','nx-fold','nq-limb','nx-nq','combined']
def one(s,a,b,n=1):
 assert s.count(a)==n,(a[:100],s.count(a),n);return s.replace(a,b)
def nx(s,mode):
 m=re.search(r'(static const struct nxb_r nx_all\[20 \+ 161\] = \{)(.*?)(\};)',s,re.S);assert m
 rows=[[int(x.strip().rstrip('u'),0) for x in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[2])];assert len(rows)==181
 bounds=[];fold={}
 for lo,hi,sh,off,k in REGIONS:
  b1=[];b2=[];bf=[]
  for i in range((lo>>sh)+off,((hi-1)>>sh)+off+1):
   w0=(i-off)<<sh;w1=min(hi-1,w0+(1<<sh)-1);wmin=max(lo,w0)
   c0,c1,c2,d=rows[i]
   l,h=sorted((c2+((d*wmin)>>32),c2+((d*w1)>>32)));b1.extend((l,h));b2.extend((c1+min(0,l),c1+max(0,h)))
   rem=((d*w0)&0xffffffff)>>16;base=c2+((d*w0)>>32);delta=w1-w0
   assert w0%(1<<16)==0
   # Bound each signed intermediate separately (before and after adding unsigned low part and rem).
   assert -(1<<31)<=(d>>16)*delta<1<<31
   assert ((d&65535)*delta>>16)+rem<1<<31
   assert -(1<<31)<=((d*delta)>>16)+rem<1<<31
   assert -(1<<31)<=rem<1<<31
   bf.extend(((d>>16)*delta,((d&65535)*delta>>16)+rem))
   assert -(1<<31)<=base<1<<31 and i not in fold
   fold[i]=[c0,c1,base,d,rem]
  assert max(map(abs,b1))<1<<(2*k-1)
  if k==14: assert max(abs(x+(1<<26)) for x in b2)<1<<(2*k-1)
  if k==15: assert max(map(abs,b2))<1<<(2*k-1)
  bounds.append({'shift':k,'first': [min(b1),max(b1)],'second':[min(b2),max(b2)],'fold_partial':[min(bf),max(bf)]})
 assert len(fold)==181
 # Shared boundary word belongs to the first dispatch; its row origin is identical.
 c0,c1,c2,d=rows[20];w=0xbe800000
 assert fold[20][2]==c2+((d*w)>>32) and (w&((1<<21)-1))==0
 p=c2+((d*w)>>32);assert abs(p)<1<<21

 print(json.dumps({'nx_bounds':bounds},sort_keys=True))
 if mode=='fold':
  s=one(s,'struct nxb_r {\n    uint32_t c0;\n    int32_t c1, c2, w3;\n};','struct nxb_r {\n    uint32_t c0;\n    int32_t c1, c2, w3;\n    uint16_t rem;\n};')
  m=re.search(r'(static const struct nxb_r nx_all\[20 \+ 161\] = \{)(.*?)(\};)',s,re.S);assert m
  table='\n'+',\n'.join('    {'+str(fold[i][0])+'u,'+','.join(map(str,fold[i][1:]))+'}' for i in range(181))+'\n'
  s=s[:m.start()]+m[1]+table+m[3]+s[m.end():]
 a=s.index('static inline uint32_t nx_cell_r(');b=s.index('static const uint32_t nq4_r',a)
 if mode=='limb':
  body='''static inline uint32_t nx_cell_r(const struct nxb_r *r, uint32_t w, uint32_t t) {
    int32_t p = r->c2 + mulhsx_r(r->w3,w);
    p = r->c1 + mulhsx_r(p,t);
    return r->c0 + (uint32_t)mulhsx_r(p,t);
}
'''
 else:
  body=''
  for k in [11,14,15]:
   body+=f'''static inline int32_t nx_shift{k}_r(int32_t a,uint32_t t) {{
    uint32_t x=t>>{k}, lo=((uint32_t)a&{(1<<k)-1}u)*x;
    int32_t hi=(a>>{k})*(int32_t)x+(int32_t)(lo>>{k});
    return hi>>{32-2*k};
}}
'''
  for sh,k in [(21,11),(18,14),(17,15)]:
   body+=f'static inline uint32_t nx_cell{k}_r(const struct nxb_r *r,uint32_t w,uint32_t t) {{\n'
   if mode=='fold':
    body+=f'''    uint32_t delta=w&{(1<<sh)-1}u,l=(uint32_t)r->w3&65535u;
    int32_t h=(r->w3>>16)*(int32_t)delta+(int32_t)(l*(delta>>16)+((l*(delta&65535u))>>16)+r->rem);
    int32_t p=r->c2+(h>>16);
'''
   else: body+='    int32_t p=r->c2+mulhsx_r(r->w3,w);\n'
   body+=f'    p=r->c1+nx_shift{k}_r(p,t);\n'
   final={11:'mulhsx_r(p,t)',14:'nx_shift14_r(p+67108864,t)-(int32_t)(t>>6)',15:'nx_shift15_r(p,t)'}[k]
   body+=f'    return r->c0+(uint32_t)({final});\n}}\n'
 s=s[:a]+body+s[b:]
 if mode!='limb':
  for sh in [11,14,15]:s=one(s,f'nx_cell_r(r, w, w << {sh})',f'nx_cell{sh}_r(r, w, w << {sh})')
 return s

def nq(s):
 for x,y,n in [('(int32_t)(((int64_t)(int32_t)q[4 * 32] * (int64_t)(uint64_t)w) >> 32)','mulhsx_r((int32_t)q[4 * 32],w)',1),('(int32_t)(((int64_t)s * (int64_t)(uint64_t)tt) >> 32)','mulhsx_r(s,tt)',3)]:s=one(s,x,y,n)
 return s

def range_reduce(s):
 # k2=(Y>>15)|1 or (Y>>16)|1 <= 131071 for uint32 Y.
 # 0x17184000 = 23649*2^14; the bounded product fits in 32 bits.
 assert 131071*23649+262143<2**32
 s=one(s,'mulhu_r(k2, 0x17184000u)','((k2 * 23649u) >> 18)',3)
 s=one(s,'mulhs_r((int32_t)k2, (int32_t)0xE8E7C000u)','(-(int32_t)((k2*23649u+262143u)>>18))')
 return s

def make(s,v):
 assert hashlib.sha256(s.encode()).hexdigest()==BASE
 if v=='range':return range_reduce(s)
 if v=='nx-limb':return nx(s,'limb')
 if v=='nx-narrow':return nx(s,'narrow')
 if v=='nx-fold':return nx(s,'fold')
 if v=='nq-limb':return nq(s)
 if v=='nx-nq':return nq(nx(s,'narrow'))
 if v=='combined':return range_reduce(nq(nx(s,'fold')))
 raise ValueError(v)
if __name__=='__main__':
 s=pathlib.Path(sys.argv[1]).read_text();pathlib.Path(sys.argv[2]).write_text(make(s,sys.argv[3]))
