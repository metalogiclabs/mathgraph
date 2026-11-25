"""Generate complete monotone near-one rounding intervals, not benchmark samples.
Boundaries are inverse-function midpoints, independently bracketed at 80/120 digits.
"""
import bisect,hashlib,json,re,struct,sys
from pathlib import Path
import mpmath as mp
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
N=4096

def word(x):return struct.unpack('<I',struct.pack('<f',float(x)))[0]
def value(w):return mp.mpf(struct.unpack('<f',struct.pack('<I',w))[0])
def boundaries(kind):
 out=[]
 for n in range(N):
  with mp.workdps(80):
   y=1-(mp.mpf(n)+mp.mpf('0.5'))/2**24
   x=mp.atanh(y) if kind=='tanh' else mp.log(y/(1-y))
   w=word(x)
  with mp.workdps(120):
   y=1-(mp.mpf(n)+mp.mpf('0.5'))/2**24
   x=mp.atanh(y) if kind=='tanh' else mp.log(y/(1-y))
   while value(w)<=x:w+=1
   while value(w-1)>x:w-=1
   assert value(w-1)<x<value(w)
   assert min(x-value(w-1),value(w)-x)>mp.mpf('1e-80')
  out.append(w)
 assert all(a>b for a,b in zip(out,out[1:]))
 return sorted(out)

def records(kind,k,thresholds):
 # In tanh use t=w<<1, preserving both input signs in the same table.
 scale=1 if kind=='tanh' else 0
 th=[x<<scale for x in thresholds]; b=k+scale; step=1<<b
 end=((th[-1]+step-1)//step)*step
 a=end-step; rows=[]
 while a>=th[0]:
  l=bisect.bisect_right(th,a);r=bisect.bisect_left(th,a+step)
  if r-l>1:break
  n=len(th)-r
  off=th[l]-a if r>l else 0
  assert 0<=off<step and n<1<<(32-b)
  rows.append((n<<b)|off);a-=step
 start=a+step;rows.reverse()
 assert start>=th[0] and len(rows)==(end-start)//step
 for i,q in enumerate(rows):
  a=start+i*step
  for z in set([a,a+step-1,a+(q&(step-1)),max(a,a+(q&(step-1))-1)]):
   expected=len(th)-bisect.bisect_right(th,z)
   got=(q>>b)+((z&(step-1))<(q&(step-1)))
   assert expected==got,(kind,k,hex(z),expected,got)
 return start,end,b,rows

def replace(s,a,b):
 assert s.count(a)==1,(a[:120],s.count(a));return s.replace(a,b)

def make(s,k,thresholds,mode='both'):
 info={}; tables=[]; maxix=-1
 for f in ('tanh','sigmoid'):
  enabled=(mode=='both' or mode==f)
  if enabled:
   start,end,b,rows=records(f,k,thresholds[f]);assert rows
   tag='sat_'+f
   tables.append(f'static const uint32_t {tag}[{len(rows)}] = {{\n'+', '.join(f'0x{v:08x}u' for v in rows)+'\n};\n')
   x='t' if f=='tanh' else 'w'
   n=f'uint32_t q={tag}[({x}>>{b})-{start>>b}u]; uint32_t n=(q>>{b})+(({x}&0x{(1<<b)-1:x}u)<(q&0x{(1<<b)-1:x}u));'
   if f=='tanh':
    s=replace(s,'if (t <= 0x82206000u) {',f'if (t < 0x{start:08x}u) {{')
    pos='    if ((int32_t)w < 0) {\n        if (w > 0xFF800000u)\n            return w | 0xFFC00000u;'
    s=replace(s,pos,f'    if (t < 0x{end:08x}u) {{ {n} return (0x3F800000u-n)|(w&0x80000000u); }}\n'+pos)
    last=start-1;ix=(last>>18)-0x1fff;qi=1+((((last>>14)+16)&~31)>>4)-0x2000
   else:
    s=replace(s,'if (w > 0x418AB000u)\n        goto phuge_;',f'if (w >= 0x{start:08x}u)\n        goto phuge_;')
    s=replace(s,'phuge_:\n    if (w > 0x7F800000u)',f'phuge_:\n    if (w < 0x{end:08x}u) {{ {n} return 0x3F800000u-n; }}\n    if (w > 0x7F800000u)')
    last=start-1;ix=(last>>17)-0x203f;qi=1+(((((last<<1)>>14)+16)&~31)>>4)-0x2040
   maxix=max(maxix,ix,qi)
   info[f]={'start':hex(start),'end':hex(end),'shift':b,'rows':len(rows),'bytes':len(rows)*4,'last_polynomial_index':max(ix,qi)}
  else:maxix=137
 assert 0<=maxix<138
 m=re.search(r'(static const struct rx_r ta_r\[)138(\] = \{)(.*?)(\};)',s,re.S);assert m
 rows=re.findall(r'\{[^{}]+\}',m[3]);assert len(rows)==138
 # Preserve every reachable hot and cold cell and a conservative extra cell.
 keep=min(138,maxix+2)
 s=s[:m.start()]+''.join(tables)+m[1]+str(keep)+m[2]+'\n'+',\n'.join(rows[:keep])+'\n'+m[4]+s[m.end():]
 info['ta_rows']=keep
 return s,info

if __name__=='__main__':
 s=Path(sys.argv[1]).read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
 k=int(sys.argv[3]);mode=sys.argv[4] if len(sys.argv)>4 else 'both'
 th={f:boundaries(f) for f in ('tanh','sigmoid')}
 s,info=make(s,k,th,mode);Path(sys.argv[2]).write_text(s);print(json.dumps(info))
