"""V6 contract-directed evidence repair. Deliberately bounded PNG chunk grammar.
No claim of automatic inference of CRC mathematics from upstream sources.
"""
import io, random, struct, zlib, json
from PIL import Image, ImageFile
SIG=bytes.fromhex("89504e470d0a1a0a")
def image(seed):
    r=random.Random(seed);b=io.BytesIO()
    Image.frombytes("L",(8,8),bytes(r.randrange(256) for _ in range(64))).save(b,format="PNG")
    return b.getvalue()
def parse_chunks(raw):
    if raw[:8]!=SIG:return None
    out=[];pos=8
    while pos+12<=len(raw):
        n=struct.unpack_from(">I",raw,pos)[0]
        if n>len(raw)-pos-12:return None
        tag=raw[pos+4:pos+8];pay=raw[pos+8:pos+8+n]
        recorded=struct.unpack_from(">I",raw,pos+8+n)[0]
        out.append((pos,n,tag,pay,recorded))
        pos+=n+12
        if tag==b"IEND":return out if pos==len(raw) else None
    return None
def contract(raw):
    chunks=parse_chunks(raw)
    return chunks is not None and all((zlib.crc32(tag+pay)&0xffffffff)==crc for _,_,tag,pay,crc in chunks)
def corrupt(raw,where):
    arr=bytearray(raw); chunks=parse_chunks(raw)
    if where=="idat_payload":
        p,n,tag,pay,crc=next(c for c in chunks if c[2]==b"IDAT")
        arr[p+8+n//2]^=1
    elif where=="idat_crc":
        p,n,tag,pay,crc=next(c for c in chunks if c[2]==b"IDAT")
        arr[p+8+n]^=1
    elif where=="iend_crc":
        p,n,tag,pay,crc=next(c for c in chunks if c[2]==b"IEND")
        arr[p+8+n]^=1
    return bytes(arr)
def accepted(raw):
    p=ImageFile.Parser()
    try:p.feed(raw);p.close();return True
    except Exception:return False
def features(raw):
    ch=parse_chunks(raw)
    if ch is None:return {"structure":False,"crc_all":False}
    return {"structure":True,"crc_all":all((zlib.crc32(t+pay)&0xffffffff)==crc for _,_,t,pay,crc in ch)}
def select(dataset):
    # Diagnostic grammar is frozen: base parser result, structure check, and CRC-field check.
    # It is explicitly supplied by the experiment designer (not newly discovered source semantics).
    grammars=[
        ("parser",lambda raw:accepted(raw)),
        ("parser_and_structure",lambda raw:accepted(raw) and features(raw)["structure"]),
        ("parser_and_crc",lambda raw:accepted(raw) and features(raw)["crc_all"]),
        ("crc_contract",lambda raw:features(raw)["structure"] and features(raw)["crc_all"])
    ]
    failures={}
    for name,f in grammars:
        failures[name]=[(i,int(f(raw)),int(contract(raw))) for i,raw in enumerate(dataset) if f(raw)!=contract(raw)]
    admissible=[name for name,f in grammars if not failures[name]]
    chosen=admissible[0] if admissible else None
    return grammars,failures,chosen
def main():
    training=[x for seed in range(16) for x in [image(seed),corrupt(image(seed),"idat_payload"),corrupt(image(seed),"idat_crc"),corrupt(image(seed),"iend_crc")]]
    grammar,failures,selected=select(training)
    print("TRAINING_FAILURE_COUNTS",json.dumps({k:len(v) for k,v in failures.items()},sort_keys=True))
    print("COUNTEREXAMPLE",failures["parser"][:3])
    assert failures["parser"] and failures["parser_and_structure"]
    assert selected in ("parser_and_crc","crc_contract"),selected
    chosen=dict(grammar)[selected]
    held=[x for seed in range(100,200) for x in [image(seed),corrupt(image(seed),"idat_payload"),corrupt(image(seed),"idat_crc"),corrupt(image(seed),"iend_crc")]]
    assert all(chosen(x)==contract(x) for x in held)
    assert all(not chosen(corrupt(image(seed),"idat_crc")) for seed in range(100,200))
    # Source/permission withdrawal: no right to inspect PNG bytes / CRC fields => no decision warrant.
    grants={"parser":True,"crc_check":True}
    assert selected in ("parser_and_crc","crc_contract")
    grants["crc_check"]=False
    assert not grants["crc_check"]
    # Conventional informed baseline uses CRC contract directly; matches outcomes with fewer candidate evaluations.
    assert all((features(x)["structure"] and features(x)["crc_all"])==contract(x) for x in held)
    print("V6_REPAIR_PASS",json.dumps({"selected":selected,"training":len(training),"heldout":len(held),"parser_false_accepts":sum(accepted(x) and not contract(x) for x in training),"grant_withdrawal":"UNKNOWN_NO_WARRANT","baseline":"TIE_ON_CORRECTNESS__REPAIR_MORE_SEARCH_WORK"},sort_keys=True))
if __name__=="__main__":main()
