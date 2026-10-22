"""Bounded acquisition of observation sequences; safety/admissibility NOT proved."""
import io, struct, zlib, random, inspect
from PIL import Image, ImageFile
from frozen_admission import scan
def png(seed, bad):
    rng=random.Random(seed)
    data=bytes(rng.randrange(256) for _ in range(64))
    b=io.BytesIO(); Image.frombytes('L',(8,8),data).save(b,format='PNG')
    v=bytearray(b.getvalue()); k=v.index(b'IDAT'); n=struct.unpack_from('>I',v,k-4)[0]
    if bad:v[k+4+n//2]^=1
    return bytes(v)
def oracle(raw):
    pos=8; ok=True
    assert raw[:8]==bytes.fromhex('89504e470d0a1a0a')
    while pos+12<=len(raw):
        size=struct.unpack_from('>I',raw,pos)[0]
        tag=raw[pos+4:pos+8];dat=raw[pos+8:pos+8+size]
        old=struct.unpack_from('>I',raw,pos+8+size)[0]
        ok &= (zlib.crc32(tag+dat)&0xffffffff)==old
        pos+=size+12
        if tag==b'IEND':break
    return ok
def methods():
    p=ImageFile.Parser()
    return sorted(n for n in dir(p) if not n.startswith('_') and callable(getattr(p,n)))
def evaluate(sequence,raw):
    obj=ImageFile.Parser()
    trace=[]
    for name in sequence:
        try:
            fn=getattr(obj,name)
            sig=inspect.signature(fn)
            required=[p for p in sig.parameters.values() if p.default==p.empty and p.kind not in (p.VAR_POSITIONAL,p.VAR_KEYWORD)]
            args=[raw] if len(required)==1 else []
            if len(required)>1:return ('UNSUPPORTED',)
            ret=fn(*args)
            trace.append((name,'OK',type(ret).__name__))
        except Exception as exc:
            trace.append((name,'ERROR',type(exc).__name__))
            break
    return tuple(trace)
def main():
    allmethods=methods()
    # Frozen generic operation grammar: bounded public calls; zero-argument plus
    # one binary-input-argument, depth <=2; name-agnostic enumerator.
    pool=[]
    p=ImageFile.Parser()
    for name in allmethods:
        try:
            s=inspect.signature(getattr(p,name))
            required=[q for q in s.parameters.values() if q.default==q.empty and q.kind not in (q.VAR_POSITIONAL,q.VAR_KEYWORD)]
            if len(required)<=1:pool.append(name)
        except (TypeError,ValueError):pass
    sequences=[(a,) for a in pool]+[(a,b) for a in pool for b in pool]
    training=[(png(i,False),png(i,True)) for i in range(8)]
    scores={seq:sum(evaluate(seq,a)!=evaluate(seq,b) for a,b in training) for seq in sequences}
    winners=sorted((seq for seq,v in scores.items() if v==8),key=lambda s:(len(s),s))
    print('METHOD_ONLY_ABLATION',scan(ImageFile.Parser()))
    print('ENUMERATION',len(pool),len(sequences),'BEST',winners[:5])
    if not winners:
        print('PROTOCOL_RESULT OBSTRUCTED');return
    selected=winners[0]
    good=evaluate(selected,training[0][0]);bad=evaluate(selected,training[0][1])
    print('SELECTED',selected,'GOOD',good,'BAD',bad)
    assert good!=bad
    correct=0
    for seed in range(100,140):
        for corruption in (False,True):
            raw=png(seed,corruption)
            observed=evaluate(selected,raw)
            predicted=(observed==good)
            if observed not in (good,bad):
                print('GENERALIZATION_FAILURE',seed,corruption,observed)
                print('PROTOCOL_RESULT UNKNOWN_GENERALIZATION')
                return
            assert predicted==oracle(raw),(seed,corruption)
            correct+=1
    print('PROTOCOL_HELDOUT_PASS',correct)
if __name__=='__main__':main()
