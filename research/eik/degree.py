"""Reversible quadratic envelope for a contiguous block of signed Horner cells.
The arithmetic error bound is |c3|/256 + 5 on either half interval.
The positive envelope bias E=2^k-1 lets one masked test certify rounding.
No use of scorer inputs; transformations depend only on coefficients and domains.
"""
from pathlib import Path
import re, sys, hashlib, json
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'

def rep(s,a,b,n=1):
    assert s.count(a)==n,(a[:150],s.count(a),n)
    return s.replace(a,b)

def rnd(a, k):
    return ((abs(a)+(1<<(k-1)))>>k)*(-1 if a<0 else 1)

def transform(s, table, lo, hi, E, parity):
    m=re.search(r'(static const struct \w+ '+table+r'\[\d+\] = \{)(.*?)(\};)',s,re.S);assert m
    rows=[[int(v.strip().rstrip('u'),0) for v in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[2])]
    new=[]; worst=0
    for i,r in enumerate(rows):
        a,b,c,d,*rest=r
        if lo<=i<hi:
            sign=1 if i%2==parity else -1
            bound=(abs(d)+255)//256+5;assert bound<=E,(table,i,bound,E)
            worst=max(bound,worst)
            a=(a+rnd(sign*d,8)+E)&0xffffffff
            b+=rnd(-9*d,6);c+=rnd(3*sign*d,2)
            assert -2**31<=b<2**31 and -2**31<=c<2**31
        new.append('{'+','.join([f'0x{a:08x}u',str(b),str(c),str(d)]+[str(x) for x in rest])+'}')
    return s[:m.start()]+m[1]+'\n'+',\n'.join(new)+'\n'+m[3]+s[m.end():],worst

def helpers(table,struct,lo,hi,E,parity):
    tag=table.split('_')[0]
    cond=f'i < {hi}u' if lo==0 else f'i >= {lo}u' if hi==138 else f'i >= {lo}u && i < {hi}u'
    return f'''\nstatic inline int {tag}_active(uint32_t i) {{ return {cond}; }}
static inline uint32_t {tag}_original_c0(const struct {struct} *r, uint32_t i) {{
    if (!{tag}_active(i)) return r->c0;
    int32_t d=r->c3, sign=(i&1u)=={parity}u ? 1 : -1;
    return r->c0-(uint32_t)q_round_r(sign*d,8)-{E}u;
}}
static inline uint32_t {tag}_quad(const struct {struct} *r,int32_t t) {{
    int32_t a=r->c1+mulhs_r(r->c2,t);
    return r->c0+(uint32_t)mulhs_r(a,t);
}}
static uint32_t {tag}_exact(const struct {struct} *r,uint32_t i,int32_t t) {{
    if (!{tag}_active(i)) {{
        int32_t a=r->c2+mulhs_r(r->c3,t);
        a=r->c1+mulhs_r(a,t);
        return r->c0+(uint32_t)mulhs_r(a,t);
    }}
    int32_t d=r->c3, sign=(i&1u)=={parity}u ? 1 : -1;
    int32_t a=r->c2-q_round_r(3*sign*d,2)+mulhs_r(d,t);
    a=r->c1-q_round_r(-9*d,6)+mulhs_r(a,t);
    return r->c0-(uint32_t)q_round_r(sign*d,8)-{E}u+(uint32_t)mulhs_r(a,t);
}}
'''

def make(s, variant):
    s=rep(s,'static inline uint32_t rx_cell_r(','''static inline int32_t q_round_r(int32_t a,unsigned k) {
    uint32_t m=a<0?0u-(uint32_t)a:(uint32_t)a;
    int32_t v=(int32_t)((m+(1u<<(k-1u)))>>k);
    return a<0?-v:v;
}
static inline uint32_t rx_cell_r(''')
    info={}
    if variant in ('tl15','tl31','both15','both31'):
        E=15 if variant.endswith('15') else 31
        hi=33 if E==15 else 66
        m=re.search(r'\btl_r\[132\] = \{(.*?)\};',s,re.S)
        rows=[[int(v.strip().rstrip('u'),0) for v in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[1])]
        for i,(a,b,c,d) in enumerate(rows[:hi]):
            rad=(abs(b)+1)//2+(abs(c)+3)//4+(abs(d)+7)//8+6+2*E
            assert a>rad and a+rad<0x80000000,(i,a,rad)
        s,worst=transform(s,'tl_r',0,hi,E,0); info['tl']={'cells':hi,'bound':worst,'E':E}
        p=s.index('static inline uint32_t rb_cell_r');s=s[:p]+helpers('tl_r','rl_r',0,hi,E,0)+s[p:]
        maskp=511 & ~(2*E+1);maskn=255 & ~(2*E+1)
        for offset,fast in [('0xF9Cu',f'if (Q & {maskp}u) return 0x3F000000u+(Q>>9);'),('0x2F9Cu',f'if ((Q-0x80u)&{maskn}u) return 0x3F000000u-((Q-0x80u)>>8);')]:
            a='const struct rl_r *r = &tl_r[(w >> 18) - '+offset+'];\n        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));'
            b='uint32_t ix=(w>>18)-'+offset+';\n        const struct rl_r *r=&tl_r[ix];\n        int32_t tt=(int32_t)(w<<13);\n        if (tl_active(ix)) { uint32_t Q=tl_quad(r,tt); '+fast+' }\n        uint32_t V=tl_exact(r,ix,tt);'
            s=rep(s,a,b)
        j=s.index('static inline uint32_t eik_sigmoid_r');k=s.index('static const struct { int32_t c0',j)
        sub=s[j:k];sub=rep(sub,'r->c0 - 0x101u','tl_original_c0(r,ix) - 0x101u',3);s=s[:j]+sub+s[k:]
        s=rep(s,'c0v_ = q->c0 - 0x101u;','c0v_ = tl_original_c0(q,(qi_>>4)-0xF7Cu) - 0x101u;')
    if variant in ('ta15','ta31','both15','both31'):
        E=15 if variant.endswith('15') else 31
        lo=72 if E==15 else 24
        s,worst=transform(s,'ta_r',lo,138,E,1);info['ta']={'cells':138-lo,'bound':worst,'E':E}
        p=s.index('static inline uint32_t rb_cell_r');s=s[:p]+helpers('ta_r','rx_r',lo,138,E,1)+s[p:]
        maskt=127 & ~(2*E+1); masks=255 & ~(2*E+1)
        s=rep(s,'const struct rx_r *r = &ta_r[(t >> 18) - 0x1FFFu];\n        th_ = w << 14;\n        uint32_t V = rx_cell_r(r, (int32_t)th_);',f'uint32_t ix=(t>>18)-0x1FFFu;\n        const struct rx_r *r=&ta_r[ix];\n        th_=w<<14;\n        if (ta_active(ix)) {{uint32_t Q=ta_quad(r,(int32_t)th_); if (Q & {maskt}u) return w-(Q>>7);}}\n        uint32_t V=ta_exact(r,ix,(int32_t)th_);')
        s=rep(s,'const struct rx_r *r = &ta_r[(w >> 17) - 0x203Fu];\n        uint32_t Z = rx_cell_r(r, (int32_t)(w << 14)) - (w << 7) + 0x40u;',f'uint32_t ix=(w>>17)-0x203Fu;\n        const struct rx_r *r=&ta_r[ix];\n        int32_t tt=(int32_t)(w<<14);\n        if (ta_active(ix)) {{uint32_t Q=ta_quad(r,tt)-(w<<7)+0x40u; if (Q & {masks}u) return 0x3F800000u-(Q>>8);}}\n        uint32_t Z=ta_exact(r,ix,tt)-(w<<7)+0x40u;')
        s=rep(s,'((o_ + 1024u) << 21) - 2u * (q->c0 - 0x40u)','((o_ + 1024u) << 21) - 2u * (ta_original_c0(q,1u+(o_>>4)-0x2000u) - 0x40u)')
        s=rep(s,'(o_ << 21) - 2u * (q->c0 - 0x40u)','(o_ << 21) - 2u * (ta_original_c0(q,1u+(o_>>4)-0x2040u) - 0x40u)')
    return s,info
if __name__=='__main__':
    s=Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
    s,info=make(s,sys.argv[3]);Path(sys.argv[2]).write_text(s);print(json.dumps(info))
