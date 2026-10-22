import io, random, zlib, hashlib, json
from PIL import Image, ImageFile

CLAUSE = """CRC (Cyclic Redundancy Code) A four-byte CRC (Cyclic Redundancy Code) calculated on the preceding bytes in the chunk, including the chunk type field and chunk data fields, but not including the length field. The CRC (Cyclic Redundancy Code) is always present, even for chunks containing no data."""
REQUIRED = ("chunk type field and chunk data fields", "not including the length field", "always present")
def authoritative(clause):
    normalized=" ".join(clause.lower().split())
    return all(p in normalized for p in REQUIRED)
def independent_crc(data):
    state=0xffffffff
    for b in data:
        state^=b
        for _ in range(8):
            state=(state>>1)^(0xedb88320 if state&1 else 0)
    return (~state)&0xffffffff
def check(data,crc):
    if data[:8]!=bytes.fromhex("89504e470d0a1a0a"):return False
    pos=8; types=[]
    while pos+12<=len(data):
        n=int.from_bytes(data[pos:pos+4],"big")
        if n>len(data)-pos-12:return False
        tag=data[pos+4:pos+8];body=data[pos+8:pos+8+n]
        got=int.from_bytes(data[pos+8+n:pos+12+n],"big")
        if crc(tag+body)!=got:return False
        pos+=n+12;types.append(tag)
        if tag==b"IEND":return pos==len(data) and types[0]==b"IHDR" and b"IDAT" in types
    return False
def original(data):
    parser=ImageFile.Parser()
    try:parser.feed(data);parser.close();return True
    except Exception:return False
def image(seed):
    rng=random.Random(seed);stream=io.BytesIO()
    Image.frombytes("L",(8,8),bytes(rng.randrange(256) for _ in range(64))).save(stream,format="PNG")
    return stream.getvalue()
def cases(seed):
    raw=image(seed)
    yield "intact",raw
    for name,tag,offset in (("payload",b"IDAT",-1),("idat_crc",b"IDAT",0),("iend_crc",b"IEND",0)):
        data=bytearray(raw);p=8
        while p+12<=len(data):
            n=int.from_bytes(data[p:p+4],"big")
            if data[p+4:p+8]==tag:
                data[p+8+(n//2 if offset==-1 else n)]^=1
                yield name,bytes(data)
                break
            p+=12+n
def main():
    assert authoritative(CLAUSE)
    assert not authoritative(CLAUSE.replace("always present","sometimes present"))
    assert not authoritative(CLAUSE.replace("not including the length field","including the length field"))
    train=[data for i in range(20) for _,data in cases(i)]
    hold=[data for i in range(100,200) for _,data in cases(i)]
    mismatches=sum(original(x)!=check(x,independent_crc) for x in train)
    repaired=sum(check(x,zlib.crc32)!=check(x,independent_crc) for x in train+hold)
    assert mismatches==40 and repaired==0
    assert len(hold)==400
    print(json.dumps({"train":len(train),"heldout":len(hold),"original_mismatches":mismatches,"repaired_mismatches":repaired,"clause_sha256":hashlib.sha256(CLAUSE.encode()).hexdigest(),"withdraw_clause":"UNKNOWN_NO_WARRANT","mutate_clause":"UNKNOWN_NO_WARRANT","baseline":"direct_bitwise_crc_matches_zlib","status":"BOUNDED_SOURCE_EXCERPT_REPAIR_PASS","source_limitation":"excerpt manually selected; checker and test authored together"},sort_keys=True))
if __name__=="__main__":main()
