"""Exact cold arithmetic sharing with register-only tail-call interfaces.

No approximation is changed. The tanh comparison uses only five low code bits;
the cleared high bit can carry sigmoid's final inversion. Exponential and
sigmoid residual decisions share the original operations at their two scales.
"""
import argparse
import hashlib
import json
from pathlib import Path
from hot_path_hints import BASE, TRAIN_SEED, HELDOUT_SEED, change
from uniform_negative_exp import block

VARIANTS=['th-no-inline','th-tail','th-tail-inline','th-tail-guards',
          'res-tail','both-tail','both-tail-guards','unified','unified-guards']


def th_share(source, inline):
    old='static inline uint32_t r_th_lt_r('
    start=source.index(old);opening,end=block(source,start)
    body=source[opening:end]
    ret='    return (int32_t)(r_P + r_rhs + r_D2) < 0;'
    if body.count(ret)!=1:raise ValueError('comparison return')
    body=body.replace(ret,'    return r_base + (((int32_t)(r_P + r_rhs + r_D2) < 0) ^ (r_e6 >> 31));')
    header=source[start:opening].replace('r_th_lt_r(', 'r_th_tail_r(')
    header=header.replace('uint32_t r_e6)', 'uint32_t r_e6, uint32_t r_base)')
    if not inline:header=header.replace('static inline','static')
    source=source[:start]+header+body+source[end:]
    a='return r_a2 + r_th_lt_r((int32_t)r_th_, (uint32_t)r_mulhs_r((int32_t)r_th_, (int32_t)r_th_), r_c0v_, r_dx_, r_dxs_, r_a1, r_code);'
    b='return r_th_tail_r((int32_t)r_th_, (uint32_t)r_mulhs_r((int32_t)r_th_, (int32_t)r_th_), r_c0v_, r_dx_, r_dxs_, r_a1, r_code & 31u, r_a2);'
    c='return r_a2 + (r_th_lt_r((int32_t)r_ts_, r_U2_, r_c0v_, r_dx_, r_dxs_, r_a1, r_e_) ^ (r_w >> 31));'
    d='return r_th_tail_r((int32_t)r_ts_, r_U2_, r_c0v_, r_dx_, r_dxs_, r_a1, (r_e_ & 31u) | (r_w & 0x80000000u), r_a2);'
    for old,new in [(a,b),(c,d)]:
        if source.count(old)!=1:raise ValueError('comparison caller')
        source=source.replace(old,new)
    return source


SHARED='''static uint32_t r_shared_res(uint32_t k, int32_t rh,
    const struct r_exp8_s *b, uint32_t upper, uint32_t rp,
    uint32_t midpoint, uint32_t shift)
{
    uint32_t mode=midpoint!=0u, rl=k*b->r_l2;
    int32_t sq=r_mulhs_r(rh,rh);
    int32_t c=r_mulhsu_r(r_mulhsu_r(rh+(sq>>10),b->r_c6),(uint32_t)sq);
    uint32_t index=k&0x1feu;
    const uint8_t *bytes=(const uint8_t *)b;
    uint32_t th=*(const uint32_t *)(bytes+2u*index)-131u;
    uint32_t tl=*(const uint16_t *)(bytes+1024u+index);
    uint32_t lw=(th<<(19u-mode))|(tl<<(3u-mode));
    uint32_t h=th>>(13u+mode);
    uint32_t z=(lw<<8)+h*(uint32_t)rh+(uint32_t)r_mulhsu_r(rh,lw)
        +r_mulhu_r(h,rl)+((uint32_t)r_mulhsu_r(sq+c,th)<<(10u-mode));
    if(mode) {
        if((int32_t)shift<0) {
            int32_t dp=(int32_t)(z-(rp<<26));
            z-=rp*(midpoint>>(shift&31u))
                +r_mulhu_r(rp,midpoint<<((0u-shift)&31u))
                +(uint32_t)r_mulhs_r(dp,(int32_t)((midpoint<<6)>>(shift&31u)));
        } else if(shift<25u) z-=r_mulhu_r(rp,midpoint>>shift);
    }
    return upper-(z>>31);
}

'''


def res_share(source):
    anchor='uint32_t eik_tanh(uint32_t r_w);'
    if source.count(anchor)!=1:raise ValueError('shared helper anchor')
    source=source.replace(anchor,SHARED+anchor)
    start=source.index('r_res_: {');opening,end=block(source,start)
    source=source[:opening]+'''{
    return r_shared_res(r_ck,(int32_t)r_cX,r_cB,r_cV,0u,0u,0u);
}'''+source[end:]
    start=source.index('r_sdec_:\n');opening,end=block(source,start)
    source=source[:opening]+'''{
    return r_shared_res(r_dk_,(int32_t)r_dB_,r_cB_,r_dU_,r_dR_,r_dM_,r_dS_);
}'''+source[end:]
    return source


def unified(source):
    start=source.index('static inline uint32_t r_th_lt_r(')
    opening,end=block(source,start)
    th=source[opening+1:end-1]
    th=th.replace('    return (int32_t)(r_P + r_rhs + r_D2) < 0;',
                  '    return r_base + (((int32_t)(r_P + r_rhs + r_D2) < 0) ^ (r_e6>>31));')
    source=source[:start]+source[end:]
    # ts has at least 13 zero low bits; the exp reduction index k is odd.
    # This distinguishes two real numeric request types without adding an arg.
    helper='''static uint32_t r_cold_terminal(uint32_t a0,uint32_t a1,uint32_t a2,
    uint32_t a3,uint32_t a4,uint32_t a5,const struct r_exp8_s *b)
{
    if((a0&1u)==0u) {
        int32_t r_ts=(int32_t)a0, r_dx=(int32_t)a2;
        int32_t r_dxs=r_dx>>14;
        uint32_t r_U2=(uint32_t)r_mulhs_r(r_ts,r_ts);
        uint32_t r_c0=a1,r_mq=a3,r_e6=a4,r_base=a5;
'''+th+'''
    } else {
        uint32_t k=a0,upper=a2,rp=a3,midpoint=a4,shift=a5;
        int32_t rh=(int32_t)a1;
'''+SHARED[SHARED.index('{')+1:SHARED.rfind('}')]+'''
    }
}

'''
    anchor='uint32_t eik_tanh(uint32_t r_w);'
    source=source.replace(anchor,helper+anchor)
    a='return r_a2 + r_th_lt_r((int32_t)r_th_, (uint32_t)r_mulhs_r((int32_t)r_th_, (int32_t)r_th_), r_c0v_, r_dx_, r_dxs_, r_a1, r_code);'
    b='return r_cold_terminal(r_th_,r_c0v_,(uint32_t)r_dx_,r_a1,r_code&31u,r_a2,&r_exp8_r);'
    c='return r_a2 + (r_th_lt_r((int32_t)r_ts_, r_U2_, r_c0v_, r_dx_, r_dxs_, r_a1, r_e_) ^ (r_w >> 31));'
    d='return r_cold_terminal(r_ts_,r_c0v_,(uint32_t)r_dx_,r_a1,(r_e_&31u)|(r_w&0x80000000u),r_a2,&r_exp8_r);'
    for old,new in [(a,b),(c,d)]:
        if source.count(old)!=1:raise ValueError('unified caller')
        source=source.replace(old,new)
    for anchor,args in [('r_res_: {','r_ck,r_cX,r_cV,0u,0u,0u,r_cB'),
                        ('r_sdec_:\n','r_dk_,r_dB_,r_dU_,r_dR_,r_dM_,r_dS_,r_cB_')]:
        start=source.index(anchor);opening,end=block(source,start)
        source=source[:opening]+'{\n    return r_cold_terminal('+args+');\n}'+source[end:]
    return source


def make(source,variant):
    if hashlib.sha256(source.encode()).hexdigest()!=BASE:raise ValueError('baseline')
    if variant not in VARIANTS:raise ValueError('variant')
    if variant.endswith('-guards'):source=change(source,('guards',))[0]
    if variant.startswith('unified'):return unified(source)
    if variant=='th-no-inline':
        source=source.replace('static inline uint32_t r_th_lt_r(', 'static uint32_t r_th_lt_r(')
    elif variant.startswith('th-') or variant.startswith('both-'):
        source=th_share(source,variant=='th-tail-inline')
    if variant.startswith('res-') or variant.startswith('both-'):source=res_share(source)
    return source


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('baseline',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);rows=[]
    for name in VARIANTS:
        s=make(a.baseline.read_text(),name);(a.out/(name+'.c')).write_text(s)
        rows.append({'name':name,'sha256':hashlib.sha256(s.encode()).hexdigest()})
    (a.out/'protocol.json').write_text(json.dumps({'baseline_sha256':BASE,'train_seed':TRAIN_SEED,
        'heldout_seed_frozen':HELDOUT_SEED,'minimum_training_gain':.005,'variants':rows,
        'boundary':'Exact arithmetic composition proposal; native/target output and compiled cost gates required'},indent=2)+'\n')
