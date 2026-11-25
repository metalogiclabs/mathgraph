"""Same-size adaptive quadratic envelope. A zero mask selects the exact cubic.
No scorer input is consulted; masks follow the analytic error bound per cell.
"""
from pathlib import Path
import sys,re,json,hashlib
from degree import rep,rnd,BASE

def apply(s,table):
    tl=table=='tl_r'; tag='tl' if tl else 'ta'; parity=0 if tl else 1
    typ='ql_row' if tl else 'qa_row'; bits=18 if tl else 16; full=511 if tl else 255
    m=re.search(r'(static const struct \w+ '+table+r'\[(\d+)\] = \{)(.*?)(\};)',s,re.S);assert m
    rows=[[int(v.strip().rstrip('u'),0) for v in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[3])]
    data=[];xh=[];active=0;groups={}
    for i,r in enumerate(rows):
        a,b,c,d,*rest=r
        if rest:xh.append(rest[0])
        assert -(1<<(bits-1))<=d<(1<<(bits-1))
        bound=(abs(d)+255)//256+5
        E=(1<<bound.bit_length())-1
        mask=full & ~(2*E+1)
        rad=(abs(b)+1)//2+(abs(c)+3)//4+(abs(d)+7)//8+6+2*E
        if tl and (a<rad or a+rad>=2**32 or (a-rad)>>31!=(a+rad)>>31):mask=0
        if mask:
            sign=1 if i%2==parity else -1
            a=(a+rnd(sign*d,8)+E)&0xffffffff;b+=rnd(-9*d,6);c+=rnd(3*sign*d,2)
            assert -2**31<=b<2**31 and -2**31<=c<2**31
            active+=1;groups[str(E)]=groups.get(str(E),0)+1
        aux=(mask<<bits)|(d&((1<<bits)-1))
        data.append('{'+','.join([f'0x{a:08x}u',str(b),str(c),f'0x{aux:08x}u'])+'}')
    txt=f'struct {typ} {{uint32_t c0;int32_t c1,c2;uint32_t aux;}};\nstatic const struct {typ} {table}[{len(rows)}] = {{\n'+',\n'.join(data)+'\n};'
    if xh:txt+='\nstatic const int16_t ta_xh[138]={'+','.join(map(str,xh))+'};'
    s=s[:m.start()]+txt+s[m.end():]
    p=s.index('static inline uint32_t rb_cell_r')
    helpers=f'''static inline uint32_t {tag}_quad(const struct {typ} *r,int32_t t) {{
    return r->c0+(uint32_t)mulhs_r(r->c1+mulhs_r(r->c2,t),t);
}}
static inline uint32_t {tag}_mask(const struct {typ} *r) {{return r->aux>>{bits};}}
static inline int32_t {tag}_c3(const struct {typ} *r) {{return (int32_t)(r->aux<<{32-bits})>>{32-bits};}}
static inline uint32_t {tag}_bias(uint32_t mask) {{return (({full}u-mask)>>1);}}
static inline uint32_t {tag}_original_c0(const struct {typ} *r,uint32_t i) {{
    uint32_t mask={tag}_mask(r); if (!mask) return r->c0;
    int32_t d={tag}_c3(r), sign=(i&1u)=={parity}u?1:-1;
    return r->c0-(uint32_t)q_round_r(sign*d,8)-{tag}_bias(mask);
}}
static uint32_t {tag}_exact(const struct {typ} *r,uint32_t i,int32_t t) {{
    uint32_t mask={tag}_mask(r);int32_t d={tag}_c3(r),a=r->c2,b=r->c1;uint32_t c=r->c0;
    if (mask) {{int32_t sign=(i&1u)=={parity}u?1:-1;
        a-=q_round_r(3*sign*d,2); b-=q_round_r(-9*d,6); c-=(uint32_t)q_round_r(sign*d,8)+{tag}_bias(mask);
    }}
    a+=mulhs_r(d,t); b+=mulhs_r(a,t);return c+(uint32_t)mulhs_r(b,t);
}}
'''
    s=s[:p]+helpers+s[p:]
    if tl:
        for offset,fast in [('0xF9Cu','if (Q & mask) return 0x3F000000u+(Q>>9);'),('0x2F9Cu','if ((int32_t)Q<0) {uint32_t q7=Q-0xc0u; if (q7 & mask & 127u) return 0x3F800000u-(q7>>7);} else {uint32_t q8=Q-0x80u;if(q8 & mask & 255u) return 0x3F000000u-(q8>>8);}')]:
            a='const struct rl_r *r = &tl_r[(w >> 18) - '+offset+'];\n        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));'
            b='uint32_t ix=(w>>18)-'+offset+';\n        const struct ql_row *r=&tl_r[ix];\n        int32_t tt=(int32_t)(w<<13);\n        uint32_t Q=tl_quad(r,tt),mask=tl_mask(r); '+fast+'\n        uint32_t V=tl_exact(r,ix,tt);'
            s=rep(s,a,b)
        j=s.index('static inline uint32_t eik_sigmoid_r');k=s.index('static const struct { int32_t c0',j)
        sub=s[j:k];sub=rep(sub,'r->c0 - 0x101u','tl_original_c0(r,ix) - 0x101u',3);s=s[:j]+sub+s[k:]
        s=rep(s,'const struct rl_r *q = (const struct rl_r *)((const uint8_t *)tl_r + (qi_ - (0xF7Cu << 4)));\n        c0v_ = q->c0 - 0x101u;','uint32_t ix=(qi_>>4)-0xF7Cu;\n        const struct ql_row *q=&tl_r[ix];\n        c0v_=tl_original_c0(q,ix)-0x101u;')
    else:
        s=rep(s,'const struct rx_r *r = &ta_r[(t >> 18) - 0x1FFFu];\n        th_ = w << 14;\n        uint32_t V = rx_cell_r(r, (int32_t)th_);','uint32_t ix=(t>>18)-0x1FFFu;\n        const struct qa_row *r=&ta_r[ix];\n        th_=w<<14;\n        uint32_t Q=ta_quad(r,(int32_t)th_); if (Q & ta_mask(r) & 127u) return w-(Q>>7);\n        uint32_t V=ta_exact(r,ix,(int32_t)th_);')
        s=rep(s,'const struct rx_r *r = &ta_r[(w >> 17) - 0x203Fu];\n        uint32_t Z = rx_cell_r(r, (int32_t)(w << 14)) - (w << 7) + 0x40u;','uint32_t ix=(w>>17)-0x203Fu;\n        const struct qa_row *r=&ta_r[ix];\n        int32_t tt=(int32_t)(w<<14);\n        uint32_t Q=ta_quad(r,tt)-(w<<7)+0x40u; if (Q & ta_mask(r)) return 0x3F800000u-(Q>>8);\n        uint32_t Z=ta_exact(r,ix,tt)-(w<<7)+0x40u;')
        for off in ['0x2000u','0x2040u']:
            a='const struct rx_r *q = (const struct rx_r *)((const uint8_t *)ta_r + 16u + o_ - ('+off+' << 4));'
            b='uint32_t qi=1u+(o_>>4)-'+off+';\n        const struct qa_row *q=&ta_r[qi];'
            s=rep(s,a,b)
        s=rep(s,'q->c0 - 0x40u','ta_original_c0(q,qi) - 0x40u',2)
        s=rep(s,'(uint32_t)(int32_t)(q)->xh << 16) | (uint16_t)(q)[-1].xh','(uint32_t)(int32_t)ta_xh[qi] << 16) | (uint16_t)ta_xh[qi-1u]',2)
    return s,{'active':active,'groups':groups}

def make(s,v):
    s=rep(s,'static inline uint32_t rx_cell_r(','''static inline int32_t q_round_r(int32_t a,unsigned k) {
    uint32_t m=a<0?0u-(uint32_t)a:(uint32_t)a;
    int32_t v=(int32_t)((m+(1u<<(k-1u)))>>k);
    return a<0?-v:v;
}
static inline uint32_t rx_cell_r(''')
    info={}
    for t in ['tl','ta']:
        if v==t or v=='both':s,info[t]=apply(s,t+'_r')
    return s,info
if __name__=='__main__':
    s=Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
    s,info=make(s,sys.argv[3]);Path(sys.argv[2]).write_text(s);print(json.dumps(info))
