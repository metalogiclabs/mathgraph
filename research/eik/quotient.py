"""Source-equivalent quotient of existing arithmetic, no new approximation."""
import hashlib,pathlib,re,sys
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
V=['correction','central','central-ptr','central-split','small','exp-shifts','address','correction-small','dispatch-pos','dispatch-neg']
def one(s,a,b,n=1):
    assert s.count(a)==n,(a[:80],s.count(a),n);return s.replace(a,b)
def quotient(s,variant):
    if variant=='correction':
        # Only callers have j=0, tq=-ts modulo 2^32 and mq=mB. The high square
        # is identical, even for INT_MIN. All dynamic shifts mask to five bits.
        # Substituting e=ux+1 changes each shift to its sigmoid counterpart.
        j=s.index('static inline uint32_t th_lt_r(');k=s.index('\nstatic inline uint32_t eik_tanh_r',j)
        a=s.index('static inline uint32_t sg_lt_r(');b=s.index('\nstatic inline uint32_t eik_sigmoid_r',a)
        body=s[a:b];body=one(body,'static inline uint32_t sg_lt_r(int32_t ts, uint32_t c0, int32_t dx, uint32_t mq, uint32_t e)','static uint32_t shared_lt_r(int32_t ts, uint32_t c0, int32_t dx, uint32_t mq, uint32_t e, uint32_t p0, uint32_t p1)')
        body=one(body,'0xAAAAAA80u - mulhu_r(zq, 0xB6090000u)','p0 - mulhu_r(zq, p1)')
        s=s[:a]+s[b:];s=s[:j]+body+s[k:]
        s=one(s,'th_lt_r((int32_t)th_, (int32_t)(0u - th_), 15u - 125u, c0v_, dx_, a1, a1, 0, e_)','shared_lt_r((int32_t)th_, c0v_, dx_, a1, e_+1u, 0xAAAAAAABu, 0xB6200000u)')
        s=one(s,'sg_lt_r((int32_t)ts_, c0v_, dx_, a1, e_)','shared_lt_r((int32_t)ts_, c0v_, dx_, a1, e_, 0xAAAAAA80u, 0xB6090000u)')
    elif variant in ('central','central-ptr','central-split'):
        # Central positive and negative inputs share exact polynomial evaluation;
        # retain all original signed rounding cases and correction consumers.
        marker='static inline uint32_t eik_sigmoid_r(uint32_t w)\n{'
        j=s.index(marker);k=s.index('\nstatic const struct { int32_t c0',j);f=s[j:k]
        pos='''    {
        const struct rl_r *r = &tl_r[(w >> 18) - 0xF9Cu];
        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));'''
        neg='''    {
        const struct rl_r *r = &tl_r[(w >> 18) - 0x2F9Cu];
        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));'''
        pstart=f.index(pos);pend=f.index('\nphi_:',pstart)
        nstart=f.index(neg);nend=f.index('\nnb_:',nstart)
        pbody=f[pstart+len(pos):pend];nbody=f[nstart+len(neg):nend]
        assert pbody.endswith('\n    }') and nbody.endswith('\n    }')
        if variant=='central-ptr':
            f=f[:nstart]+'    r = &tl_r[(w >> 18) - 0x2F9Cu]; goto common_;'+f[nend:]
            f=f[:pstart]+'''    r = &tl_r[(w >> 18) - 0xF9Cu];
common_: { uint32_t V = rl_cell_r(r, (int32_t)(w << 13));
        if ((int32_t)w < 0) {'''+nbody[:-6]+'''\n        }'''+pbody+f[pend:]
            f=one(f,'    int32_t dx_;','    int32_t dx_;\n    const struct rl_r *r;')
        else:
            f=f[:nstart]+'    goto common_;'+f[nend:]
            idx='((w<<1)>>19) - 0xF9Cu' if variant=='central' else '((w & 0x7fffffffu)>>18)-0xF9Cu'
            f=f[:pstart]+'''common_: {
        const struct rl_r *r = &tl_r['''+idx+'''];
        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));
        if ((int32_t)w < 0) {'''+nbody[:-6]+'''\n        }'''+pbody+f[pend:]
        s=s[:j]+f+s[k:]
    elif variant=='small':
        # Two small sigmoid branches share exactly the mantissa/polynomial.
        p='''        uint32_t e = w >> 23;
        M = (w << 8) | 0x80000000u;
        uint32_t s_ = e ^ 31u, Ms = M >> (s_ & 31u), Z = mulhu_r(Ms, Ms);
        uint32_t Pn = (uint32_t)mulhs_r((int32_t)Z, (int32_t)(mulhu_r(Z, 0x21D70000u) - 0x5554F000u));'''
        j=s.index('static inline uint32_t eik_sigmoid_r');k=s.index('\nstatic const struct { int32_t c0',j);f=s[j:k];assert f.count(p)==2
        a=f.index('    {\n'+p);b=f.index('\nneg_:',a)
        c=f.index('    {\n'+p,b);d=f.index('\ns1_:',c)
        pos=f[a+len('    {\n'+p):b];neg=f[c+len('    {\n'+p):d];assert pos.endswith('\n    }') and neg.endswith('\n    }')
        f=f[:c]+'    goto small_common_;'+f[d:]
        f=f[:a]+'small_common_: {\n'+p+'\n        if ((int32_t)w<0) {'+neg[:-6]+'\n        }'+pos+f[b:]
        s=s[:j]+f+s[k:]
    elif variant in ('dispatch-pos','dispatch-neg'):
        # Exact unsigned interval check (no sign wrap admits other words).
        p='''    if ((int32_t)w < 0)
        goto neg_;
    if (w < 0x3E701000u)
        goto plo_;
    if (w > 0x407FF000u)
        goto phi_;
    {'''
        n='''neg_:
    if (w < 0xBE701000u)
        goto nlo_;
    if (w > 0xBFF80000u)
        goto nb_;
    {'''
        if variant=='dispatch-pos':
            s=one(s,p,'''    if (w-0x3E701000u <= 0x407FF000u-0x3E701000u) goto pc_;
    if ((int32_t)w < 0) goto neg_;
    if (w < 0x3E701000u) goto plo_;
    goto phi_;
pc_: {''')
        else:
            s=one(s,p,'''    if (w-0xBE701000u <= 0xBFF80000u-0xBE701000u) goto nc0_;
    if ((int32_t)w < 0) goto neg_;
    if (w < 0x3E701000u) goto plo_;
    if (w > 0x407FF000u) goto phi_;
    {''')
            s=one(s,n,'''neg_:
    if (w < 0xBE701000u) goto nlo_;
    goto nb_;
nc0_: {''')
    elif variant=='exp-shifts':
        s=one(s,'if (w < sp) {\n            uint32_t us = up - 103u;\n            if (w < us)','if (w < 0x3b800000u) {\n            uint32_t us = up - 103u;\n            if (w < 0x33800000u)')
    elif variant=='address':
        for a,b in [('&tl_r[(w >> 18) - 0xF9Cu]','(const struct rl_r *)((const uint8_t *)tl_r + (((w-0x3e700000u)>>14)&~15u))'),('&tl_r[(w >> 18) - 0x2F9Cu]','(const struct rl_r *)((const uint8_t *)tl_r + (((w-0xbe700000u)>>14)&~15u))'),('&tld_r[(t >> 19) - 0xF64u]','(const struct rl_r *)((const uint8_t *)tld_r + (((t-0x7b200000u)>>15)&~15u))'),('&ta_r[(w >> 17) - 0x203Fu]','(const struct rx_r *)((const uint8_t *)ta_r + (((w-0x407e0000u)>>13)&~15u))'),('&ta_r[(t >> 18) - 0x1FFFu]','(const struct rx_r *)((const uint8_t *)ta_r + (((t-0x7ffc0000u)>>14)&~15u))')]:
            s=one(s,a,b)
    elif variant=='correction-small':
        s=quotient(quotient(s,'correction'),'small')
    else:raise ValueError(variant)
    return s
if __name__=='__main__':
    s=pathlib.Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
    for v in sys.argv[3:]:s=quotient(s,v)
    pathlib.Path(sys.argv[2]).write_text(s)
