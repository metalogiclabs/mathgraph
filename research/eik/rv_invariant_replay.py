"""Replay the arithmetic certificates, native full-cell enumeration and two falsifiers."""
import hashlib,json,pathlib,re,subprocess,sys,tempfile
from rv_invariants import tanh_nonzero,public_nonzero
from rv_fusion import BASE,PUBLIC,make

def replay(basepath,publicpath):
 b=pathlib.Path(basepath).read_text();p=pathlib.Path(publicpath).read_text()
 assert hashlib.sha256(b.encode()).hexdigest()==BASE
 assert hashlib.sha256(p.encode()).hexdigest()==PUBLIC
 _,cert=tanh_nonzero(b,b)
 portable=make(b,p,'portable47');_,exp=public_nonzero(portable,p)
 # Deliberately invalidate one cell constant; the interval certificate must refuse it.
 m=re.search(r'tld_r\[156\] = \{(.*?)\};',b,re.S);body=m[1]
 q=list(re.finditer(r'\{([^{}]+)\}',body))[28];vs=q[1].split(',');vs[0]='0u'
 badbody=body[:q.start()]+'{'+','.join(vs)+'}'+body[q.end():]
 bad=b[:m.start(1)]+badbody+b[m.end(1):]
 try:tanh_nonzero(b,bad)
 except AssertionError:pass
 else:raise AssertionError('zero-cell falsifier accepted')
 bad=p.replace('0x802c64b9u','0x00000000u',1);assert bad!=p
 try:public_nonzero(portable,bad)
 except AssertionError:pass
 else:raise AssertionError('zero-table falsifier accepted')
 harness=r'''
int main(void) {
 uint64_t checked=0,zero=0;
 for(unsigned i=0;i<156;i++) if(tld_r[i].c1==0) {
  uint32_t lo=(i+0xF64u)<<18,hi=lo+(1u<<18),mn=0xffffffffu,mx=0;
  for(unsigned sign=0;sign<2;sign++)for(uint32_t a=lo;a<hi;a++) {
   uint32_t w=a+(sign<<31),v=rt_cell_r(&tld_r[i],w<<1,(int32_t)(w<<13));
   if(v<mn)mn=v;if(v>mx)mx=v;zero+=v==0;checked++;
  }
  printf("row %u min=%08x max=%08x\n",i,mn,mx);
 }
 printf("checked=%llu zero=%llu\n",(unsigned long long)checked,(unsigned long long)zero);
 return zero!=0;
}
'''
 pre='#include <stdint.h>\n#include <stdbool.h>\n#include <stddef.h>\n#include <string.h>\n#include <stdio.h>\n'
 with tempfile.TemporaryDirectory() as tmp:
  d=pathlib.Path(tmp);src=d/'certificate.c';exe=d/'certificate'
  src.write_text(pre+b+harness)
  subprocess.run(['gcc','-std=c11','-O2','-fno-strict-aliasing',str(src),'-o',str(exe)],check=True)
  out=subprocess.run([str(exe)],capture_output=True,text=True,check=True).stdout
 assert 'checked=1572864 zero=0' in out
 return {'status':'PASSED_SOURCE_PINNED_CERTIFICATES','baseline_sha256':BASE,'public_sha256':PUBLIC,'tanh_integer_bounds':cert,'exp_table_bound':exp,'native_full_cell_enumeration':out.splitlines(),'negative_controls_rejected':2,'full_function_correctness_or_speed_claim':False}
if __name__=='__main__':print(json.dumps(replay(*sys.argv[1:]),indent=2))
