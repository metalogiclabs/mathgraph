import inspect, io, random, struct, zipfile, zlib
# Source-selection target and API name deliberately decoupled.
DENIED = {'extract','extractall','write','writestr','mkdir','close','setpassword','open','read','printdir'}
def sample(seed, corrupt):
    rng = random.Random(seed)
    name = f"file_{seed%7}.bin"
    data = bytes(rng.randrange(256) for _ in range(25 + seed % 17))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_STORED) as z: z.writestr(name,data)
    raw = bytearray(buf.getvalue())
    if corrupt: raw[30+len(name)+len(data)//2] ^= 1
    return bytes(raw)
def oracle(raw):
    e = raw.rfind(b'PK\\x05\\x06')
    assert e >= 0
    _,_,_,_,entries,_,cd,_ = struct.unpack_from('<4sHHHHIIH',raw,e)
    assert entries == 1 and raw[cd:cd+4] == b'PK\\x01\\x02'
    crc = struct.unpack_from('<I',raw,cd+16)[0]
    assert raw[:4] == b'PK\\x03\\x04' and struct.unpack_from('<H',raw,8)[0] == 0
    length = struct.unpack_from('<I',raw,18)[0]
    n,x = struct.unpack_from('<HH',raw,26)
    data = raw[30+n+x:30+n+x+length]
    assert len(data) == length
    return (zlib.crc32(data) & 0xffffffff) == crc
def eligible():
    result=[]
    for n,f in inspect.getmembers(zipfile.ZipFile,predicate=inspect.isfunction):
        if n.startswith('_') or n in DENIED: continue
        params = list(inspect.signature(f).parameters.values())[1:]
        if all(p.default is not inspect.Parameter.empty or p.kind in (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD) for p in params): result.append(n)
    return result
def observe(method,raw):
    with zipfile.ZipFile(io.BytesIO(raw),'r') as z:
        try:
            v=getattr(z,method)()
            # Probe is restricted to a small known grammar; no general side-effect guarantee.
            if isinstance(v,(str,bytes,int,bool,float,type(None))): return 'NULL' if v is None else 'NONNULL:'+type(v).__name__
            if isinstance(v,(tuple,list)): return repr(v)
            return 'UNSUPPORTED:'+type(v).__name__
        except Exception as e: return 'EXCEPTION:'+type(e).__name__
def main():
    methods=eligible()
    scores={n:sum(observe(n,sample(i,False))!=observe(n,sample(i,True)) for i in range(8)) for n in methods}
    choices=sorted(n for n in methods if scores[n]==8)
    assert choices, scores
    winner=choices[0]
    clean,bad=sample(0,False),sample(0,True)
    mapping={observe(winner,clean):oracle(clean),observe(winner,bad):oracle(bad)}
    assert len(mapping)==2
    for seed in range(100,140):
        for broken in (False,True):
            raw=sample(seed,broken)
            assert mapping[observe(winner,raw)]==oracle(raw)
    assert all(observe('namelist',sample(i,False))==observe('namelist',sample(i,True)) for i in range(100,140))
    print('LOCAL_RESTRICTED_SOURCE_SELECTION_PASS',scores,'selected',winner,'heldout',80,'permission_revoked','OBSTRUCTED')
if __name__=='__main__': main()
