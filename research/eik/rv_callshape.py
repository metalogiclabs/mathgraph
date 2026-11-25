"""Cost search within one certified unreachable return site.

The rt_cell integer interval certificate proves V != 0 for each of the only
three rows where c1 == 0. Alter only that unreachable return; no seed or target
selection, compiler flags or numerical path changes.
"""
import pathlib,hashlib,json,sys
from rv_invariants import tanh_nonzero
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
RETURNS={
 'constant':'0u',
 'exp-direct':'eik_exp(w)',
 'exp-half':'eik_exp(w) >> 1',
 'exp-lsb':'eik_exp(w) & 1u',
 'exp-offset':'eik_exp(w ^ 1u) >> 31',
 'sigmoid-msb':'eik_sigmoid(w) >> 31',
 'sigmoid-direct':'eik_sigmoid(w)',
 'two-exp':'eik_exp(w) ^ eik_exp(w ^ 1u)',
 'exp-negative':'eik_exp(0u - w) >> 31',
}
def make(s,v):
 assert hashlib.sha256(s.encode()).hexdigest()==BASE
 _,cert=tanh_nonzero(s,s)
 if v=='control':return s,cert
 old='return eik_exp(w) >> 31;';assert s.count(old)==1
 out=s.replace(old,'return '+RETURNS[v]+';')
 if v.startswith('sigmoid'):
  marker='uint32_t eik_exp(uint32_t w);';assert out.count(marker)==1
  out=out.replace(marker,marker+'\nuint32_t eik_sigmoid(uint32_t w);')
 return out,cert
if __name__=='__main__':
 b,o,v=sys.argv[1:];s,c=make(pathlib.Path(b).read_text(),v);pathlib.Path(o).write_text(s)
 print(json.dumps({'variant':v,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'unreachable_site_certificate':c},indent=2))
