from pathlib import Path
import re,sys,hashlib
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
def rep(s,a,b,n=1):
 assert s.count(a)==n,(a[:90],s.count(a),n)
 return s.replace(a,b)
def ta(s, mode):
 bias=64 if mode=="biased" else 0
 if mode=="biased":mode="signed"
 m=re.search(r'(static const struct rx_r ta_r\[138\] = \{)(.*?)(\};)',s,re.S);assert m
 rows=[[int(v.strip().rstrip('u'),0) for v in r.split(',')] for r in re.findall(r'\{([^{}]+)\}',m[2])];assert len(rows)==138
 B=0x3f800000
 for i,row in enumerate(rows):
  w0=(i+0x1fff)<<17; center=(w0+0x20000)&~0x3ffff
  row[0]=(row[0]-((center-B)<<7)+bias)&0xffffffff
  row[1]-=1<<25
  assert -2**31<=row[1]<2**31
 s=s[:m.start()]+m[1]+'\n'+',\n'.join('{'+','.join([f'0x{a:08x}u']+[str(v) for v in b])+'}' for a,*b in rows)+'\n'+m[3]+s[m.end():]
 a='uint32_t Z = rx_cell_r(r, (int32_t)(w << 14)) - (w << 7) + 0x40u;'
 s=rep(s,a,'uint32_t Z = rx_cell_r(r, (int32_t)(w << 14))'+(';' if bias else ' + 0x40u;'))
 a='uint32_t V = rx_cell_r(r, (int32_t)th_);\n        if (V & 126u)\n            return w - (V >> 7);\n        a2 = w - (V >> 7);\n        k_ = V;'
 if mode=='direct':
  b='uint32_t Q = rx_cell_r(r, (int32_t)th_);\n        a2 = (0x3F800000u - (Q >> 7)) | (w & 0x80000000u);\n        if (Q & 126u) return a2;\n        k_ = Q;'
 elif mode=='reconstruct':
  b='uint32_t V = rx_cell_r(r, (int32_t)th_) + ((w - 0x3F800000u) << 7);\n        if (V & 126u) return w - (V >> 7);\n        a2 = w - (V >> 7);\n        k_ = V;'
 elif mode=='signed':
  b='uint32_t Q = rx_cell_r(r, (int32_t)th_);\n        a2 = ((w & 0x80000000u) + 0x3F800000u) - (Q >> 7);\n        if (Q & 126u) return a2;\n        k_ = Q;'
 else: raise ValueError(mode)
 if bias:b=b.replace("rx_cell_r(r, (int32_t)th_);","rx_cell_r(r, (int32_t)th_) - 64u;")
 s=rep(s,a,b)
 C=((1024<<21)+(B<<8)+128+2*bias)&0xffffffff
 s=rep(s,'c0v_ = ((o_ + 1024u) << 21) - 2u * (q->c0 - 0x40u);',f'c0v_ = 0x{C:08x}u - 2u * q->c0;')
 s=rep(s,'c0v_ = (o_ << 21) - 2u * (q->c0 - 0x40u);',f'c0v_ = 0x{C:08x}u - 2u * q->c0;')
 return s
def small(s,short=False):
 a='''uint32_t u = 0u - w, a = (u | 0xFF800000u) + 0xFF800000u;
            int32_t g = (int32_t)a >> ((u >> 23) & 31u);
            return (uint32_t)((int32_t)(0x7E000000u - (uint32_t)g) >> 1);'''
 b='''uint32_t m = (w & 0x7fffffu) | 0x800000u;
            uint32_t sh = 128u - (w >> 23);
            return 0x3F000000u + ((m + ((1u << (sh-1u))-1u)) >> sh);'''
 if short:b=b.replace("((m + ((1u << (sh-1u))-1u)) >> sh)","((((m-1u) >> (sh-1u))+1u)>>1)")
 s=rep(s,a,b)
 a='''uint32_t u = 0xFF800000u - w, a = (u | 0xFF800000u) + 0xFF800000u;
            int32_t g = (int32_t)a >> ((u >> 23) & 31u);
            return (0x7E000001u + (uint32_t)g) >> 1;'''
 b='''uint32_t m = (w & 0x7fffffu) | 0x800000u;
            uint32_t sh = 383u - (w >> 23);
            return 0x3F000000u - ((m + ((1u << (sh-1u))-1u)) >> sh);'''
 if short:b=b.replace("((m + ((1u << (sh-1u))-1u)) >> sh)","((((m-1u) >> (sh-1u))+1u)>>1)")
 s=rep(s,a,b)
 return s
if __name__=='__main__':
 s=Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
 for v in sys.argv[3:]:s=small(s,v=='small2') if v in ('small','small2') else ta(s,v)
 Path(sys.argv[2]).write_text(s)
