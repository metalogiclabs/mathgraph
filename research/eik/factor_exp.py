"""A two-table negative-exp proposal, screened on complete compiled cost first.

Decompose |x|=i/2^a+j/2^b+r/2^28, where b>=12. Two downward
rounded factor tables and a quadratic residual form the proposal. A biased
rounding guard settles outputs; all uncertain inputs use the full evaluator.
No scoring inputs influence the factor tables or the fixed six layouts.
"""
import argparse
from decimal import Decimal as D, localcontext, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
from hot_path_hints import BASE, TRAIN_SEED, HELDOUT_SEED
from uniform_negative_exp import replace_family, LO, HI

LAYOUTS = [(3,12), (4,12), (5,12), (3,13), (4,13), (5,13)]


def coordinate(word):
    return (((word << 8) & 0xffffffff) | 0x80000000) >> (386-(word >> 23))


def tables(a, b):
    if (a,b) not in LAYOUTS:
        raise ValueError('undeclared layout')
    large, small = [], []
    with localcontext() as ctx:
        ctx.prec = 100
        ln2 = D(2).ln()
        for i in range(8 << a):
            value = (-D(i)/D(1 << a)).exp()
            exponent = int((value.ln()/ln2).to_integral_value(rounding=ROUND_FLOOR)) if i else 0
            mantissa = int((value*D(2)**(31-exponent)).to_integral_value(rounding=ROUND_FLOOR))
            assert 2**31 <= mantissa < 2**32-1024
            large.append((mantissa, (126+exponent) << 23))
        for j in range(1 << (b-a)):
            value = (-D(j)/D(1 << b)).exp()*D(2)**32
            small.append(min(2**32-1, int(value.to_integral_value(rounding=ROUND_FLOOR))))
    return large, small


def make(source, a, b):
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong baseline')
    large, small = tables(a,b)
    table = 'struct fx_a {uint32_t mantissa,base;};\n'
    table += 'static const struct fx_a fx_large['+str(len(large))+']={\n'
    table += ',\n'.join('{'+str(m)+'u,'+str(e)+'u}' for m,e in large)+'\n};\n'
    table += 'static const uint32_t fx_small['+str(len(small))+']={\n'
    table += ','.join(str(v)+'u' for v in small)+'\n};\n'
    body = '''        if (r_w < 0xC1000000u) {
            uint32_t fq=((r_w<<8)|0x80000000u)>>(386u-(r_w>>23));
            const struct fx_a *fa=&fx_large[fq>>'''+str(28-a)+'''];
            uint32_t ft=r_mulhu_r(fa->mantissa,fx_small[(fq>>'''+str(28-b)+''')&'''+str((1<<(b-a))-1)+'''u]);
            uint32_t fr=fq&'''+str((1<<(28-b))-1)+'''u;
            uint32_t fp=(fr<<4)-((fr*fr)>>25);
            uint32_t fv=ft-r_mulhu_r(ft,fp)+5u;
            if((int32_t)fv<0) {
                uint32_t fz=fv+128u;
                if(fz&248u) return fa->base+(fz>>8);
            } else {
                uint32_t fz=fv+64u;
                if(fz&120u) return fa->base-0x800000u+(fz>>7);
            }
            r_cB=&r_exp8_r;goto r_negmain_;
        }
'''
    candidate = replace_family(source, body)
    anchor = 'static inline uint32_t r_eik_exp_r('
    if candidate.count(anchor) != 1:
        raise ValueError('table anchor')
    candidate = candidate.replace(anchor, table+anchor)
    if len(candidate.encode()) > 262144:
        raise ValueError('source cap')
    return candidate, {'coarse_bits':a,'fine_bits':b,'large_rows':len(large),
                       'small_rows':len(small),'table_bytes':8*len(large)+4*len(small),
                       'source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                       'source_bytes':len(candidate.encode())}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('baseline',type=Path)
    ap.add_argument('out',type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    records=[]
    for a,b in LAYOUTS:
        text, rec = make(args.baseline.read_text(),a,b)
        name='a'+str(a)+'b'+str(b)
        (args.out/(name+'.c')).write_text(text)
        records.append({'name':name,**rec})
    protocol={'state':'CANDIDATE','baseline_sha256':BASE,'domain':[LO,HI],
              'train_seed':TRAIN_SEED,'heldout_seed_frozen':HELDOUT_SEED,
              'minimum_training_gain':0.005,'layouts':records,
              'order':'Compiled whole score including table bytes first; finite native qualification only after a meaningful gain',
              'guard_boundary':'Algebraic error proposal plus arithmetic tests; full changed-family replay required before promotion'}
    (args.out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    print(json.dumps(protocol,indent=2))
