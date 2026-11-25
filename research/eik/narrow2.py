"""Source-bounded arithmetic on qualified ARM 97.065 control. All arithmetic portable."""
import pathlib,sys,re,hashlib,json
BASE='832b81faf97490295a743292627aeab0cd9b9d8f0abf1eedd7d7d1d1c9119ca3'
VARIANTS=['tl-last','rt-second','rb-second','sq-first','nq-first','nx-packed','joint']
def rep(s,a,b,n=1):
 assert s.count(a)==n,(a[:120],s.count(a),n);return s.replace(a,b)
def rows(s,tab):
 m=re.search(r'\b'+tab+r'\[.*?\] = \{(.*?)\};',s,re.S);assert m
 return [[int(x.strip().rstrip('u'),0) for x in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[1])]
def signed(x):return ((x+2**31)%2**32)-2**31
def check(a,b,k):
 assert -(1<<(2*k-1))<a<=b<(1<<(2*k-1)),(a,b,k)
def tl(s):
 # For tl, center the last coefficient at a multiple of 2^19, so the
 # removed offset's contribution is exactly 128*x, x=th>>13.
 bias=1<<26
 bounds=[]
 for _,b,c,d in rows(s,'tl_r'):
  a=abs(c)+(abs(d)+1)//2
  lo,hi=b-(a+1)//2-bias,b+(a+1)//2-bias;assert -(1<<26)+8192<lo<=hi<(1<<26)-8192;bounds.extend((lo,hi))
 print('tl-last biased signed bounds',min(bounds),max(bounds))
 p=s.index('static inline uint32_t rb_cell_r(')
 body='''static inline uint32_t tl_fast_r(const struct rl_r *r,int32_t th) {
    int32_t a=r->c2+shifted13_r(r->c3,th);
    int32_t b=r->c1-67108864+shifted13_r(a,th);
    return r->c0+(uint32_t)shifted13_r(b,th)+((uint32_t)(th>>13)<<7);
}
'''
 s=s[:p]+body+s[p:];return rep(s,'rl_cell_r(r, (int32_t)(w << 13))','tl_fast_r(r, (int32_t)(w << 13))',2)
def rt(s):
 bound=[]
 for i,(_,b,c,d) in enumerate(rows(s,'tld_r')):
  w=(i+0xf64)<<19;lo,hi=sorted((c+((d*w)>>32),c+((d*(w+(1<<19)-1))>>32)));check(lo,hi,13);bound.extend((lo,hi))
 print('rt first result bounds',min(bound),max(bound))
 a=s.index('static inline uint32_t rt_cell_r(');b=s.index('static inline uint32_t rl_cell_r(',a)
 return s[:a]+rep(s[a:b],'r->c1 + mulhs_r(s, th)','r->c1 + shifted13_r(s, th)')+s[b:]
def rb(s):
 # w3 is interpreted unsigned; the cast of the product is modulo 2^32.
 # Verify signed c2 - high-product modulo 2^32 on both endpoints,
 # including no signed-wrap crossing inside any cell.
 bound=[]
 for i,(_,b,c,d) in enumerate(rows(s,'tb_r')):
  w=(i+0x5ffc)<<17;u=d&0xffffffff
  l,h=sorted((c-((u*w)>>32),c-((u*(w+(1<<17)-1))>>32)))
  assert (l+2**31)//2**32==(h+2**31)//2**32
  l,h=signed(l),signed(h);check(l,h,14);bound.extend((l,h))
 print('rb first result bounds',min(bound),max(bound))
 a=s.index('static inline uint32_t rb_cell_r(');b=s.index('static inline uint64_t umul_r(',a)
 return s[:a]+rep(s[a:b],'r->c1 + mulhs_r(s, th)','r->c1 + shifted14_r(s, th)')+s[b:]
def quartic(s,tab):
 m=re.search(r'\b'+tab+r'\[.*?\] = \{(.*?)\};',s,re.S);vals=[int(v,16) for v in re.findall(r'0x([0-9a-f]+)u',m[1])];n=len(vals)//5;assert len(vals)==n*5
 c=[vals[i*n:(i+1)*n] for i in range(5)];bound=[]
 if tab=='nq4_r':
  assert n==32
  for i,(_,b,c2,d,e) in enumerate(zip(*c)):
   d,e,c2=map(signed,(d,e,c2));w=(i+(385<<5))<<18
   lo,hi=sorted((d+((e*w)>>32),d+((e*(w+(1<<18)-1))>>32)));check(lo,hi,14);check(c2+min(0,lo),c2+max(0,hi),14);bound.extend((lo,hi,c2+min(0,lo),c2+max(0,hi)))
  s=rep(s,'s = (int32_t)q[2 * 32] + mulhsx_r(s,tt);','s = (int32_t)q[2 * 32] + nx_shift14_r(s,tt);')
  s=rep(s,'s = (int32_t)q[32] + mulhsx_r(s,tt);','s = (int32_t)q[32] + nx_shift14_r(s,tt);')
 else:
  assert n==33
  for _,b,c2,d,e in zip(*c):
   d,e=map(signed,(d,e));check(e,e,13);r=(abs(e)+1)//2;check(d-r,d+r,13);bound.extend((e,d-r,d+r))
  s=rep(s,'mulhs_r((int32_t)c4, (int32_t)tt)','shifted13_r((int32_t)c4, (int32_t)tt)')
  s=rep(s,'s = (int32_t)q[2 * 33] + mulhs_r(s, (int32_t)tt);','s = (int32_t)q[2 * 33] + shifted13_r(s, (int32_t)tt);')
 print(tab,'narrow signed bounds',min(bound),max(bound));return s
def packed(s):
 # Retain exact high and low limbs of w3 in its existing 4-byte footprint.
 # Outside the evaluators only W<<23 (or (W-2)<<23) is observed.
 s=rep(s,'    int32_t c1, c2, w3;\n    uint16_t rem;', '    int32_t c1, c2;\n    uint16_t low;\n    int16_t high;\n    uint16_t rem;')
 m=re.search(r'(static const struct nxb_r nx_all\[20 \+ 161\] = \{)(.*?)(\};)',s,re.S);assert m
 rs=rows(s,'nx_all');assert len(rs)==181
 table=[]
 for c0,c1,c2,d,rem in rs:
  lo=d&65535;hi=d>>16;assert -32768<=hi<=32767 and d==hi*65536+lo
  table.append('    {'+str(c0)+'u,'+','.join(map(str,[c1,c2,lo,hi,rem]))+'}')
 s=s[:m.start()]+m[1]+'\n'+',\n'.join(table)+'\n'+m[3]+s[m.end():]
 a=s.index('static inline uint32_t nx_cell11_r(');b=s.index('static const uint32_t nq4_r',a)
 sub=rep(s[a:b],'(uint32_t)r->w3&65535u','r->low',3);sub=rep(sub,'(r->w3>>16)','(int32_t)r->high',3);s=s[:a]+sub+s[b:]
 a=s.index('static inline uint32_t eik_exp_r(');b=s.index('static const uint32_t tsr_r',a)
 sub=rep(s[a:b],'W = (uint32_t)r->w3','W = r->low',2);assert 'r->w3' not in sub;s=s[:a]+sub+s[b:]
 return s
F={'tl-last':tl,'rt-second':rt,'rb-second':rb,'sq-first':lambda s:quartic(s,'sq_r'),'nq-first':lambda s:quartic(s,'nq4_r'),'nx-packed':packed}
def make(s,v):
 assert hashlib.sha256(s.encode()).hexdigest()==BASE
 for t in F if v=='joint' else [v]:s=F[t](s)
 return s
if __name__=='__main__':
 s=pathlib.Path(sys.argv[1]).read_text();pathlib.Path(sys.argv[2]).write_text(make(s,sys.argv[3]))
