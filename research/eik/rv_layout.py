"""Lossless cell layouts and exact exponent-domain predicates; no score-input specialization."""
import hashlib, pathlib, re, sys

BASE = '3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'

def one(s, a, b, n=1):
    assert s.count(a) == n, (a[:100], s.count(a), n)
    return s.replace(a,b)

def layout(s, kind, order):
    fields = {
      'rl_r':[('uint32_t','c0'),('int32_t','c1'),('int32_t','c2'),('int32_t','c3')],
      'rx_r':[('uint32_t','c0'),('int32_t','c1'),('int32_t','c2'),('int16_t','c3'),('int16_t','xh')],
      'ry_r':[('uint32_t','c0'),('int32_t','c1'),('int32_t','c2'),('int32_t','w3')],
      'nxb_r':[('uint32_t','c0'),('int32_t','c1'),('int32_t','c2'),('int32_t','w3')],
    }[kind]
    m = re.search(r'struct '+kind+r' \{.*?\};',s,re.S); assert m
    decl='struct '+kind+' {\n'+''.join('    '+fields[i][0]+' '+fields[i][1]+';\n' for i in order)+'};'
    s=s[:m.start()]+decl+s[m.end():]
    def table(m):
        def row(r):
            a=[x.strip() for x in r[1].split(',')];assert len(a)==len(fields),(kind,a)
            return '{'+', '.join(a[i] for i in order)+'}'
        return m[1]+re.sub(r'\{([^{}]+)\}',row,m[2])+m[3]
    s,n=re.subn(r'(static const struct '+kind+r' \w+\[[^\]]+\] = \{)(.*?)(\};)',table,s,flags=re.S)
    assert n>0
    return s

def predicate(s):
    # For binary32 bit patterns with sign clear, w < (w>>23)-K iff w < K<<23.
    # Below K the subtraction wraps above every nonnegative w; at or above K,
    # its result is <=255-K while w is >=K<<23.
    s=one(s,'if (w < sp) {','if (w < 0x3B800000u) {')
    s=one(s,'if (w < us)\n                goto one_;','if (w < 0x33800000u)\n                goto one_;')
    return s

def bank(s, order):
    # Combine same-layout mathematical tables into one immutable object.
    names=['tl_r','kr_r','tld_r','tla_r','ta_r','tb_r','sq_r','nx_all','nq4_r','tsr_r']
    parts={}
    for name in names:
        m=re.search(r'static const (struct \w+|uint32_t) '+name+r'(\[[^\]]+\]) = (\{.*?\});',s,re.S);assert m,name
        parts[name]=(m[1],m[2],m[3]);s=s[:m.start()]+s[m.end():]
    # All type definitions must precede the bank; nxb_r was originally later.
    m=re.search(r'struct nxb_r \{.*?\};',s,re.S);assert m
    nxb=m[0];s=s[:m.start()]+s[m.end():]
    insert=s.index('static const struct { uint32_t hi')
    decl=nxb+'\nstatic const struct {\n'+''.join(f'    {parts[n][0]} {n}{parts[n][1]};\n' for n in order)+'} rv_bank = {\n'+',\n'.join(parts[n][2] for n in order)+'\n};\n'
    s=s[:insert]+decl+s[insert:]
    # Replace names in uses, not the just-written member declarations.
    end=insert+len(decl)
    s=s[:end]+re.sub(r'\b('+'|'.join(names)+r')\b',r'rv_bank.\1',s[end:])
    return s

def make(s,v):
    if v=='control':return s
    if v=='exp-domains':return predicate(s)
    if v in ('rl-cycle','rl-reverse','all-cycle','all-reverse'):
        s=layout(s,'rl_r',[1,2,3,0] if 'cycle' in v else [3,2,1,0])
    if v in ('rx-cycle','all-cycle','all-reverse'):
        s=layout(s,'rx_r',[1,2,3,4,0] if v!='all-reverse' else [3,4,2,1,0])
    if v in ('nx-cycle','all-cycle','all-reverse'):
        order=[1,2,3,0] if v!='all-reverse' else [3,2,1,0]
        for k in ('ry_r','nxb_r'):s=layout(s,k,order)
    if v in ('bank','bank-reverse','bank-interleaved'):
        order=['tl_r','kr_r','tld_r','tla_r','ta_r','tb_r','sq_r','nx_all','nq4_r','tsr_r']
        if v=='bank-reverse':order=order[::-1]
        if v=='bank-interleaved':order=['tl_r','ta_r','nx_all','tld_r','tb_r','sq_r','nq4_r','kr_r','tla_r','tsr_r']
        s=bank(s,order)
    if v=='all-cycle':s=predicate(s)
    assert v in VARIANTS,v
    return s

VARIANTS=['control','exp-domains','rl-cycle','rl-reverse','rx-cycle','nx-cycle','all-cycle','all-reverse','bank','bank-reverse','bank-interleaved']
if __name__=='__main__':
    s=pathlib.Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
    pathlib.Path(sys.argv[2]).write_text(make(s,sys.argv[3]))
