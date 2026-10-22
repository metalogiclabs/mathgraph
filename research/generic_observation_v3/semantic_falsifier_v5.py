import io,struct,zlib,random
from PIL import Image,ImageFile
def chunks(raw):
 p=8
 while p+12<=len(raw):
  n=struct.unpack_from('>I',raw,p)[0];tag=raw[p+4:p+8]
  yield p,n,tag
  p+=12+n
  if tag==b'IEND':break
def baseline(raw):
 return all((zlib.crc32(raw[p+4:p+8+n])&0xffffffff)==struct.unpack_from('>I',raw,p+8+n)[0] for p,n,t in chunks(raw))
def protocol(raw):
 p=ImageFile.Parser()
 try:p.feed(raw);p.close();return True
 except Exception:return False
def make(seed):
 rng=random.Random(seed);data=bytes(rng.randrange(256) for _ in range(64));b=io.BytesIO();Image.frombytes('L',(8,8),data).save(b,format='PNG');return b.getvalue()
def variants(raw):
 p,n,t=next(chunks(raw));at=p+n+12;payload=b'Comment\x00test';tag=b'tEXt'
 block=struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',(zlib.crc32(tag+payload)^1)&0xffffffff)
 yield 'ancillary-bad-crc',raw[:at]+block+raw[at:]
 z=bytearray(raw)
 for p,n,t in chunks(raw):
  if t==b'IDAT':z[p+8+n]^=1;break
 yield 'idat-bad-crc',bytes(z)
 yield 'intact',raw
def main():
 failures=[];matrix={}
 for seed in range(40):
  for kind,raw in variants(make(seed)):
   b,p=baseline(raw),protocol(raw)
   matrix[(kind,b,p)]=matrix.get((kind,b,p),0)+1
   if b!=p:failures.append((seed,kind,b,p))
 print('MATRIX',sorted((str(k),v) for k,v in matrix.items()))
 print('DISAGREEMENTS',len(failures),'FIRST',failures[:5])
 assert len(failures)==40,failures
 assert all(k=='idat-bad-crc' and b==False and p==True for _,k,b,p in failures)
 print('V5_SEMANTIC_FALSIFIER_PASS decoder_rejected_for_global_crc_goal')
if __name__=='__main__':main()
