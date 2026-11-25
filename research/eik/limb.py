"""Portable exact high-product decomposition. No compiler/target tests or score input dependence."""
import hashlib,pathlib,re,sys
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
V=['limbs','shifted','shifted-limbs','shifted-ta','shifted-tl']
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
# Split at k: x = th / 2^k signed, al*x fits int32 for k=13,14.
# |a| < 2^(2*k-1) suffices for the signed high intermediate:
# |x| <= 2^(31-k); splitting a at k then taking nested floors is exact.
HELP='''static inline int32_t shifted13_r(int32_t a,int32_t t) {
    int32_t x=t>>13;
    int32_t lo=(int32_t)((uint32_t)a&8191u)*x;
    int32_t hi=(a>>13)*x+(lo>>13);
    return hi>>6;
}
static inline int32_t shifted14_r(int32_t a,int32_t t) {
    int32_t x=t>>14;
    int32_t lo=(int32_t)((uint32_t)a&16383u)*x;
    int32_t hi=(a>>14)*x+(lo>>14);
    return hi>>4;
}
'''
# All additions in unsigned 32-bit for mixed case, plus range-checked signed intermediates.
LIMB='''static inline uint32_t mulhu_r(uint32_t a,uint32_t b) {
    uint32_t al=a&65535u,bl=b&65535u,ah=a>>16,bh=b>>16;
    uint32_t u=ah*bl+((al*bl)>>16);
    uint32_t v=al*bh+(u&65535u);
    return ah*bh+(u>>16)+(v>>16);
}
static inline int32_t mulhs_r(int32_t a,int32_t b) {
    uint32_t al=(uint32_t)a&65535u,bl=(uint32_t)b&65535u;
    int32_t ah=a>>16,bh=b>>16;
    int32_t u=ah*(int32_t)bl+(int32_t)((al*bl)>>16);
    int32_t v=(int32_t)al*bh+(int32_t)((uint32_t)u&65535u);
    return ah*bh+(u>>16)+(v>>16);
}
static inline int32_t mulhsx_r(int32_t a,uint32_t b) {
    uint32_t al=(uint32_t)a&65535u,bl=b&65535u,bh=b>>16;
    int32_t ah=a>>16;
    int32_t u=ah*(int32_t)bl+(int32_t)((al*bl)>>16);
    uint32_t v=al*bh+((uint32_t)u&65535u);
    return (int32_t)((uint32_t)ah*bh+(uint32_t)(u>>16)+(v>>16));
}
'''
def rows(s,table):
    m=re.search(r'\b'+table+r'\[\d+\] = \{(.*?)\};',s,re.S);assert m
    return [[int(x.strip().rstrip('u'),0) for x in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[1])]
def bound(r,k,n):
    # th is signed, |th/2^32| <= 1/2. Conservative absolute Horner bounds.
    z=abs(r[3]);b=[z]
    z=abs(r[2])+(z+1)//2;b.append(z)
    z=abs(r[1])+(z+1)//2;b.append(z)
    assert all(x < (1<<(2*k-1)) for x in b[:n]),(r,k,b)
    return b

def make(s,v):
    assert hashlib.sha256(s.encode()).hexdigest()==BASE
    if v in ['limbs','shifted-limbs']:
        a=s.index('static inline uint32_t mulhu_r(');b=s.index('static inline uint32_t rx_cell_r(',a)
        s=s[:a]+LIMB+s[b:]
        s=one(s,'''static inline int32_t mulhsu_r(int32_t a, uint32_t b)
{
    return (int32_t)(((int64_t)a * (int64_t)(uint64_t)b) >> 32);
}''','''static inline int32_t mulhsu_r(int32_t a, uint32_t b)
{
    return mulhsx_r(a,b);
}''')
    if v in ['shifted','shifted-limbs','shifted-ta','shifted-tl']:
        p=s.index('static inline uint32_t rx_cell_r(');s=s[:p]+HELP+s[p:]
    if v in ['shifted','shifted-limbs','shifted-ta']:
        # rx_cell_r is called only with th=w<<14, for ta_r family.
        assert s.count('rx_cell_r(')==3
        for r in rows(s,'ta_r'):bound(r,14,3)
        a=s.index('static inline uint32_t rx_cell_r(');b=s.index('static inline uint32_t rt_cell_r(',a)
        s=s[:a]+s[a:b].replace('mulhs_r(','shifted14_r(')+s[b:]
    if v in ['shifted','shifted-limbs','shifted-tl']:
        # rl_cell_r is called with w<<13 / th_ = w<<13. Use bounded first
        # two multiplies; third can exceed 2^26 and remains generic.
        assert s.count('rl_cell_r(')==4
        for table in ('tl_r','kr_r'):
            for r in rows(s,table):bound(r,13,2)
        a=s.index('static inline uint32_t rl_cell_r(');b=s.index('static inline uint32_t rb_cell_r(',a)
        q=s[a:b].replace('mulhs_r(r->c3, th)','shifted13_r(r->c3, th)').replace('mulhs_r(s, th);\n    return','shifted13_r(s, th);\n    return')
        s=s[:a]+q+s[b:]
    return s
if __name__=='__main__':
    pathlib.Path(sys.argv[2]).write_text(make(pathlib.Path(sys.argv[1]).read_text(),sys.argv[3]))
