"""Integrate already qualified band polynomials inside existing dispatch paths.
No scorer-dependent generation or evaluator changes. Inputs pinned by SHA256.
"""
import hashlib,pathlib,sys
PINS={'control':'3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4','quadratic':'6224bb17d718e06dc506f1e5b50eef75694ea91833f106f7f3eaf5d9b1928351','joint':'920577f11c4f328d6f00eb8e877214b1f60d9b2b7bec2ed32d89cf680a2fbeeb'}
def one(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def load(p,k):
 b=pathlib.Path(p).read_bytes();assert hashlib.sha256(b).hexdigest()==PINS[k];return b.decode()
def change(s,v):
 if v.startswith('quad'):
  guard='    if(w>=0x3f800000u && w<0x3fa00000u) return isyn_sigmoid(w);\n'
  s=one(s,guard,'')
  where='    {\n        const struct rl_r *r = &tl_r[(w >> 18) - 0xF9Cu];'
  if v=='quad-mask':
   s=one(s,where,'    if ((w>>21)==508u) return isyn_sigmoid(w);\n'+where)
  elif v=='quad-range':
   s=one(s,where,guard+where)
  elif v=='quad-hint':
   s=one(s,where,'    if (__builtin_expect((w>>21)==508u,0)) return isyn_sigmoid(w);\n'+where)
  elif v=='quad-local':
   s=one(s,where,'    {\n        if ((w>>21)==508u) return isyn_sigmoid(w);\n        const struct rl_r *r = &tl_r[(w >> 18) - 0xF9Cu];')
  else:raise ValueError(v)
 elif v.startswith('joint'):
  a='    if ((w<<1)>>22==508u) { const struct js_row *r=&js_rows[(w>>15)&63u]; int32_t p=js_value(r,w); uint32_t a=2u*r->base-0x3f800000u+(uint32_t)((p-32768)>>16); return a|(w&0x80000000u); }\n'
  b='    if ((w>>21)==512u) { const struct js_row *r=&js_rows[(w>>15)&63u]; int32_t p=js_value(r,w); return r->base+(uint32_t)(p>>17); }\n'
  s=one(one(s,a,''),b,'')
  if v!='joint-sigmoid-only':
   s=one(s,'cells_: {\n        const struct rl_r *r = &tld_r', 'cells_: {\n'+a+'        const struct rl_r *r = &tld_r')
  if v!='joint-tanh-only':
   s=one(s,'    {\n        const struct rl_r *r = &tl_r[(w >> 18) - 0xF9Cu];',b+'    {\n        const struct rl_r *r = &tl_r[(w >> 18) - 0xF9Cu];')
 else:raise ValueError(v)
 return s
if __name__=='__main__':
 v=sys.argv[1];s=load(sys.argv[2], 'quadratic' if v.startswith('quad') else 'joint');s=change(s,v);pathlib.Path(sys.argv[3]).write_text(s)
