import io, tarfile, random, re, sys, hashlib
def candidate_methods(docs):
    matches=list(re.finditer(r'^\.\. method:: TarFile\.(\w+)\(([^\n]*)\)', docs, re.M))
    result=[]
    for i,m in enumerate(matches):
        chunk=docs[m.end():matches[i+1].start() if i+1<len(matches) else len(docs)]
        summary=re.sub(r'\s+',' ',chunk).strip()[:350]
        # Restricted source-derived admission; NOT general safety proof.
        if 'Return the members' in summary: result.append(m.group(1))
    return sorted(set(result))
def make_archive(seed, executable):
    buffer=io.BytesIO()
    data=random.Random(seed).randbytes(40)
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as t:
        item=tarfile.TarInfo('doc_%d.bin'%(seed%11))
        item.size=len(data);item.mode=0o755 if executable else 0o644
        t.addfile(item,io.BytesIO(data))
    return buffer.getvalue()
def raw_header_oracle(raw):
    header=raw[:512]
    assert header[257:263]==b'ustar\x00'
    checksum=int(header[148:156].rstrip(b'\x00 ').strip(),8)
    clone=bytearray(header);clone[148:156]=b'        '
    assert sum(clone)==checksum
    return bool(int(header[100:108].rstrip(b'\x00 ').strip(),8)&0o111)
def readout(method, raw):
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as obj:
        result=getattr(obj,method)()
        assert isinstance(result,list)
        if result and isinstance(result[0],tarfile.TarInfo):
            return tuple(bool(int(x.mode)&0o111) for x in result)
        return tuple(result)
def main(path):
    source=open(path,encoding='utf-8').read()
    admitted=candidate_methods(source)
    assert len(admitted)>1,admitted
    pairs=[(make_archive(i,False),make_archive(i,True)) for i in range(10)]
    scores={m:sum(readout(m,a)!=readout(m,b) for a,b in pairs) for m in admitted}
    eligible=sorted(m for m,n in scores.items() if n==len(pairs))
    assert eligible,scores
    chosen=eligible[0]
    mapping={readout(chosen,raw):raw_header_oracle(raw) for pair in pairs for raw in pair}
    assert len(mapping)==2,mapping
    for seed in range(100,150):
        for executable in (False,True):
            raw=make_archive(seed,executable)
            assert mapping[readout(chosen,raw)]==raw_header_oracle(raw)
        assert readout('getnames',make_archive(seed,False))==readout('getnames',make_archive(seed,True))
    print('SOURCE_SHA256',hashlib.sha256(source.encode()).hexdigest())
    print('SOURCE_ADMITTED',admitted,'SCORES',scores,'SELECTED',chosen)
    print('HELDOUT_PASS',100,'PERMISSION_WITHDRAWN','OBSTRUCTED')
if __name__=='__main__':main(sys.argv[1])
