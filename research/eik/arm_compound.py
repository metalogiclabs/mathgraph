"""Portable arithmetic transformations on the exhaustively qualified ARM baseline."""
import hashlib,pathlib,re,sys
BASE='099c17e7ea81db42254cbcbbf21ec0ca229e29e386d5f9e3abef39fb4629f567'
VARIANTS=['correction','square','exp-direct','exp-square','limb-carry','square-exp','correction-square-exp']
def one(s,a,b,n=1):
    assert s.count(a)==n,(a[:100],s.count(a),n);return s.replace(a,b)
def change(s,v):
    if v=='correction':
        j=s.index('static inline uint32_t th_lt_r('); k=s.index('\nstatic inline uint32_t eik_tanh_r',j)
        a=s.index('static inline uint32_t sg_lt_r('); b=s.index('\nstatic inline uint32_t eik_sigmoid_r',a)
        body=s[a:b];body=one(body,'static inline uint32_t sg_lt_r(int32_t ts, uint32_t c0, int32_t dx, uint32_t mq, uint32_t e)','static uint32_t shared_lt_r(int32_t ts, uint32_t c0, int32_t dx, uint32_t mq, uint32_t e, uint32_t p0, uint32_t p1)')
        body=one(body,'0xAAAAAA80u - mulhu_r(zq, 0xB6090000u)','p0 - mulhu_r(zq, p1)')
        s=s[:a]+s[b:];s=s[:j]+body+s[k:]
        s=one(s,'th_lt_r((int32_t)th_, (int32_t)(0u - th_), 15u - 125u, c0v_, dx_, a1, a1, 0, e_)','shared_lt_r((int32_t)th_, c0v_, dx_, a1, e_+1u, 0xAAAAAAABu, 0xB6200000u)')
        s=one(s,'sg_lt_r((int32_t)ts_, c0v_, dx_, a1, e_)','shared_lt_r((int32_t)ts_, c0v_, dx_, a1, e_, 0xAAAAAA80u, 0xB6090000u)')
    elif v=='square':
        # a = 2^16*h+l. Cross = h*l. Split cross before doubling to avoid overflow.
        # All unsigned intermediates fit; for signed h, cross fits signed 32 bits.
        body='''static inline uint32_t sqhu_r(uint32_t a) {
    uint32_t l=a&65535u,h=a>>16,c=h*l;
    return h*h+2u*(c>>16)+(((c&65535u)*2u+((l*l)>>16))>>16);
}
static inline int32_t sqhs_r(int32_t a) {
    uint32_t l=(uint32_t)a&65535u;
    int32_t h=a>>16,c=h*(int32_t)l;
    return h*h+2*(c>>16)+(int32_t)((((uint32_t)c&65535u)*2u+((l*l)>>16))>>16);
}
'''
        s,n=re.subn(r'\bmulhu_r\(([A-Za-z_]\w*), \1\)',r'sqhu_r(\1)',s);assert n>=5
        s,n=re.subn(r'\bmulhs_r\(([A-Za-z_]\w*), \1\)',r'sqhs_r(\1)',s);assert n>=5
        p=s.index('static inline int32_t shifted13_r(');s=s[:p]+body+s[p:]
    elif v=='exp-direct':
        for x,n in [('Q',1),('P',2)]:
            s=one(s,f'((int64_t)(uint64_t)T * (int32_t){x}) >> 32',f'mulhsx_r((int32_t){x}, T)',n)
        s=one(s,'((int64_t)(uint64_t)(T + 817u) * (int32_t)(h - (uint32_t)rho)) >> 32','mulhsx_r((int32_t)(h - (uint32_t)rho), T + 817u)')
        s=one(s,'((int64_t)rho * rho) >> 32','mulhs_r(rho, rho)')
    elif v=='exp-square':
        # Exact low/high half of a square. Replace only direct square in th_core.
        s=one(s,'''    uint64_t m2 = umul_r(p, p);
    uint32_t m2h = (uint32_t)(m2 >> 32), m2l = (uint32_t)m2;''','''    uint32_t l=p&65535u,h=p>>16,c=h*l,lo=l*l;
    uint32_t u=(c&65535u)*2u+(lo>>16);
    uint32_t m2h=h*h+2u*(c>>16)+(u>>16),m2l=(u<<16)|(lo&65535u);''')
    elif v=='limb-carry':
        # Difference-free cross-limb carry, alternative grouping. In signed and mixed cases
        # use signed partial terms, unsigned bit extraction, and bounded signed sums.
        s=one(s,'''    uint32_t u=ah*bl+((al*bl)>>16);
    uint32_t v=al*bh+(u&65535u);
    return ah*bh+(u>>16)+(v>>16);''','''    uint32_t x=ah*bl,y=al*bh,z=(al*bl)>>16;
    return ah*bh+(x>>16)+(y>>16)+(((x&65535u)+(y&65535u)+z)>>16);''')
        s=one(s,'''    int32_t u=ah*(int32_t)bl+(int32_t)((al*bl)>>16);
    int32_t v=(int32_t)al*bh+(int32_t)((uint32_t)u&65535u);
    return ah*bh+(u>>16)+(v>>16);''','''    int32_t x=ah*(int32_t)bl,y=(int32_t)al*bh;
    uint32_t z=(al*bl)>>16;
    return ah*bh+(x>>16)+(y>>16)+(int32_t)((((uint32_t)x&65535u)+((uint32_t)y&65535u)+z)>>16);''')
        s=one(s,'''    int32_t u=ah*(int32_t)bl+(int32_t)((al*bl)>>16);
    uint32_t v=al*bh+((uint32_t)u&65535u);
    return (int32_t)((uint32_t)ah*bh+(uint32_t)(u>>16)+(v>>16));''','''    int32_t x=ah*(int32_t)bl;
    uint32_t y=al*bh,z=(al*bl)>>16;
    return (int32_t)((uint32_t)ah*bh+(uint32_t)(x>>16)+(y>>16)+((((uint32_t)x&65535u)+(y&65535u)+z)>>16));''')
    elif v=='square-exp':s=change(change(change(s,'exp-direct'),'square'),'exp-square')
    elif v=='correction-square-exp':s=change(change(s,'correction'),'square-exp')
    else:raise ValueError(v)
    return s
if __name__=='__main__':
    s=pathlib.Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
    for v in sys.argv[3:]:s=change(s,v)
    pathlib.Path(sys.argv[2]).write_text(s)
