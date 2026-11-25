"""Remove source-pinned impossible branches using exact integer/table certificates."""
import pathlib,re,sys,json,hashlib
from rv_fusion import make,BASE,PUBLIC

def one(s,a,b,n=1):
    assert s.count(a)==n,(a,s.count(a),n)
    return s.replace(a,b)

def tanh_nonzero(s,source):
    m=re.search(r'tld_r\[156\] = \{(.*?)\};',source,re.S);assert m
    rows=[[int(x.strip().rstrip('u'),0) for x in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[1])]
    cert=[]
    for i,(a,b,c,d) in enumerate(rows):
        if b!=0:continue
        # For signed 32-bit t, |mulhi(z,t)| <= ceil(|z|/2)+1.
        # For unsigned u32 t, |mulhi(d,t)| <= |d|+1.
        # rt_cell = a + mulhi(mulhi(c+mulhi(d,t),th),th) when b=0.
        bound1=abs(c)+abs(d)+1
        assert bound1<2**31
        bound2=(bound1+1)//2+1
        bound3=(bound2+1)//2+1
        assert bound3<a<2**32-bound3
        cert.append({'row':i,'c0':a,'c2':c,'c3':d,'absolute_remainder_bound':bound3,'zero_impossible':True})
    assert len(cert)==3
    s=one(s,'            if (V == 0u)\n                return eik_exp(w) >> 31;\n','')
    return s,cert

def public_nonzero(s,public):
    m=re.search(r'static const struct r_exp8_s r_exp8_r = \{\s*\{(.*?)\},',public,re.S);assert m
    hi=[int(x.rstrip('u'),0) for x in re.findall(r'0x[0-9a-fA-F]+u',m[1])]
    assert len(hi)==256 and min(hi)>0
    # pT = bytes(exp8_r.hi)+1020-((k2<<1)&1020), an aligned index in 0..255.
    s,n=re.subn(r'\s*if \(r_T == 0u\)\s*goto r_nev_;','',s);assert n==1
    s,n=re.subn(r'\nr_nev_:\s*return eik_tanh\(r_w\) \^ 1u;','',s);assert n==1
    return s,{'table_words':len(hi),'minimum':min(hi),'maximum_byte_offset':1020,'all_nonzero':True}

def even_offset(s):
    pattern=r'\(\(r_w \* \(r_w \+ 1u\)\) & 1u\)'
    s,n=re.subn(pattern,'0u',s);assert n==3,n
    # Unsigned modulo 2^32 preserves parity; consecutive factors have opposite parity.
    assert all((x*(x+1)&1)==0 for x in range(2))
    return s,{'instances':n,'parity_cases_checked':2,'ring':'Z/(2^32)','always_zero':True}

def transform(base,public,variant):
    assert hashlib.sha256(base.encode()).hexdigest()==BASE
    assert hashlib.sha256(public.encode()).hexdigest()==PUBLIC
    cert={}
    if variant=='control':return base,cert
    if variant=='rrr-tanh-nonzero':
        out,cert['tanh_nonzero']=tanh_nonzero(base,base)
    else:
        fused=variant.startswith('fused-')
        out=make(base,public,'exp47-shared' if fused else 'portable47')
        if variant!='portable47-even':out,cert['public_nonzero']=public_nonzero(out,public)
        if variant not in ('portable47-nonzero',):out,cert['even_offset']=even_offset(out)
        if variant=='fused-clean-tanh':out,cert['tanh_nonzero']=tanh_nonzero(out,base)
    header='/* Portable source derived from published EIK entry #47, SHA256 '+PUBLIC+'; MIT or Apache-2.0, as granted by the competition.\n * Published provenance: https://conjectures.io/v1/competitions/exact-integer-kernels/submissions/47/source\n * Exact integer/table invariants; one implementation on every architecture. */\n'
    out=header+out
    assert len(out.encode())<=262144 and "L'" not in out
    return out,cert

if __name__=='__main__':
    b,p,o,v=sys.argv[1:]
    out,cert=transform(pathlib.Path(b).read_text(),pathlib.Path(p).read_text(),v)
    pathlib.Path(o).write_text(out)
    print(json.dumps({'variant':v,'source_sha256':hashlib.sha256(out.encode()).hexdigest(),'certificate':cert},indent=2))
