import io, random, struct, zlib, inspect, hashlib, json, sys
from frozen_admission import scan
def make(seed, corrupted):
    from PIL import Image
    rng=random.Random(seed)
    data=bytes(rng.randrange(256) for _ in range(64))
    im=Image.frombytes("L",(8,8),data)
    b=io.BytesIO()
    im.save(b,format="PNG")
    raw=bytearray(b.getvalue())
    # Corrupt compressed IDAT bytes, preserving parseable chunk envelope.
    p=raw.find(b'IDAT')
    assert p>=0
    length=struct.unpack_from(">I",raw,p-4)[0]
    assert length>7
    if corrupted:raw[p+4+length//2]^=1
    return bytes(raw)
def independent_crc_oracle(raw):
    assert raw[:8]==bytes.fromhex('89504e470d0a1a0a')
    pos=8
    status=True
    while pos+12<=len(raw):
        n=struct.unpack_from('>I',raw,pos)[0]
        kind=raw[pos+4:pos+8]
        payload=raw[pos+8:pos+8+n]
        recorded=struct.unpack_from('>I',raw,pos+8+n)[0]
        if zlib.crc32(kind+payload)&0xffffffff!=recorded:status=False
        pos+=n+12
        if kind==b'IEND':break
    return status
def observe(name,raw):
    from PIL import ImageFile
    obj=ImageFile.Parser()
    obj.feed(raw)
    try:
        value=getattr(obj,name)()
        return ('ok',type(value).__name__,str(value)[:100])
    except Exception as ex:
        return ('error',type(ex).__name__)
def main():
    from PIL import ImageFile
    candidates=scan(ImageFile.Parser())
    print('CANDIDATES',candidates)
    pair=[(make(i,False),make(i,True)) for i in range(8)]
    scores={n:sum(observe(n,a)!=observe(n,b) for a,b in pair) for n in candidates}
    winners=sorted(n for n,v in scores.items() if v==8)
    print('SCORES',scores,'WINNERS',winners)
    # Do not weaken admission if it fails.
    if not winners:
        print('RESULT OBSTRUCTED_IN_FROZEN_GRAMMAR')
        return
    winner=winners[0]
    train={observe(winner,raw):independent_crc_oracle(raw) for pair0 in pair for raw in pair0}
    for i in range(100,140):
        for bad in [False,True]:
            raw=make(i,bad)
            assert train[observe(winner,raw)]==independent_crc_oracle(raw)
    print('HELDOUT_PASS',80,'WINNER',winner)
if __name__=='__main__':main()
