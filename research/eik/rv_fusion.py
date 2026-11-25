"""Fixed portable composition of public predecessor #47 and retained RRR.

The choice is the same on every architecture and every input. No live/private
champion source is accessed. Public predecessor provenance is retained.
"""
import hashlib,pathlib,re,sys
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
PUBLIC='bd2b39b11a3756c7545fc8b56cadabcb150acb6b8465842985363404c45dfd42'
def make(base,public,variant):
    assert hashlib.sha256(base.encode()).hexdigest()==BASE
    assert hashlib.sha256(public.encode()).hexdigest()==PUBLIC
    marker='/* ===== Thumb body ===== */'
    assert marker in public
    s=public.split(marker)[0]
    s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
    s,n=re.subn(r'^#define RVB .*$', '#define RVB 1',s,flags=re.M);assert n==1
    s,n=re.subn(r'^#define r_EIK_SEL .*$', '#define r_EIK_SEL 1',s,flags=re.M);assert n==1
    for f in ('sigmoid','tanh','exp'):
        s,n=re.subn(r'static uint32_t t_eik_'+f+r'\([^;]+;','',s);assert n==1
        s,n=re.subn(r'if \(!RVB\)\s*return t_eik_'+f+r'\(r_w\);\s*','',s);assert n==1
    # Remove unreachable old Thumb kernels from the retained baseline as well.
    start=base.index('static const struct { int32_t c0, c1, c2, c3; } small_exp_rows[]')
    end=base.index('uint32_t eik_sigmoid(uint32_t w)\n{',start)
    base=base[:start]+base[end:]
    if variant=='portable47':return s
    assert variant in ('exp47-isolated','exp47-shared')
    if variant=='exp47-isolated':
        for f in ('sigmoid','tanh','exp'):
            s=re.sub(r'\beik_'+f+r'\b','p47_eik_'+f,s)
            s=s.replace('uint32_t p47_eik_'+f+'(', 'static uint32_t p47_eik_'+f+'(')
        target='p47_eik_exp'
    else:
        s,n=re.subn(r'uint32_t eik_(sigmoid|tanh|exp)\(uint32_t r_w\)\s*\{\s*return r_eik_\1_r\(r_w\);\s*\}', '',s);assert n==3
        target='r_eik_exp_r'
    result=s+'\n'+base
    assert result.count('return eik_exp_r(w);')==1
    result=result.replace('return eik_exp_r(w);','return '+target+'(w);')
    assert "L'" not in result and len(result.encode())<=262144
    return result
if __name__=='__main__':
    b,p,o,v=sys.argv[1:]
    pathlib.Path(o).write_text(make(pathlib.Path(b).read_text(),pathlib.Path(p).read_text(),v))
