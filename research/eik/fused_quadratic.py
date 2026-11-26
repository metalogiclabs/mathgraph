"""Reduce one complete ARM quadratic family from three products to two.

The original evaluator stays on every ambiguous quotient and special input.
Coefficients and guards depend on the complete mathematical family, not score
inputs. The published fixture retains its original licensing and attribution.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

BASE = '8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37'


def rows(source):
    start = source.index('} t_t_twh =')
    start = source.index('{0u, {', start)
    end = source.index('\n#define t_t_tw', start)
    result = [[int(v.strip().rstrip('u'), 0) for v in r.split(',')]
              for r in re.findall(r'\{([^{}]+)\}', source[start:end])]
    if len(result) != 128 or any(len(r) != 3 for r in result):
        raise ValueError('wrong complete mathematical family')
    return result


def certificate(coefficients):
    max_product = 0
    for v, r, p in coefficients:
        if not (0 <= v < 2**32 and 0 <= r < 2**16 and 0 <= p < 2**16):
            raise ValueError('coefficient width')
        product = (r + ((p * 65535) >> 21)) * 65535
        if product >= 2**32:
            raise ValueError('fused product exceeds its exact unsigned range')
        max_product = max(max_product, product)
    # With Z = RD/4096 + PD^2/2^33, original A has 0 <= Z-A < 5/2,
    # and fused B has 0 <= Z-B < 17. Thus -2 <= A-B <= 16.
    # B mod 256 in [21,239] gives A mod 256 in [19,255], the same
    # quotient and an original settled guard. Arithmetic is modulo 2^32;
    # the guard also excludes a carry across the whole word boundary.
    return {'cells': len(coefficients), 'offset_domain': [0, 65535],
            'maximum_fused_product': max_product,
            'original_minus_fused': [-2, 16], 'settled_guard': [21, 239]}


def transform(source, variant):
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong published fixture')
    cert = certificate(rows(source))
    if variant in ('helper', 'helper-likely'):
        old_helper = '''    uint32_t t_t_D2 = (t_t_D * t_t_D) >> 16;
    return t_t_r->t_t_v + ((t_t_r->t_t_r * t_t_D) >> 12) + ((t_t_r->t_t_p * t_t_D2) >> 17);'''
        cond = '((t_t_w<<9)>>23)!=0u && ((t_t_B-21u)&255u)<=218u'
        if variant == 'helper-likely':
            cond = '__builtin_expect((' + cond + '),1)'
        new_helper = '''    uint32_t t_t_rem=t_t_r->t_t_r+((t_t_r->t_t_p*t_t_D)>>21);
    uint32_t t_t_B=t_t_r->t_t_v+((t_t_rem*t_t_D)>>12);
    if(''' + cond + ''') return t_t_B;
''' + old_helper
        if source.count(old_helper) != 1:
            raise ValueError('nonunique original helper')
        result = source.replace(old_helper, new_helper)
        cert.update(variant=variant, baseline_sha256=BASE,
                    source_sha256=hashlib.sha256(result.encode()).hexdigest(),
                    source_bytes=len(result.encode()))
        return result, cert
    old = 't_t_tsm: {const struct t_t_ra *t_t_rr = &t_t_tw[(int32_t)(t_t_w<<6) >> 24]; t_t_zl = t_t_cell_d(t_t_rr, t_t_w, t_t_e);if((t_t_i<<27)==0u){if((t_t_w << 9) >> 23 == 0u)goto t_t_low;}t_t_q=t_t_zl>>8;'
    cond = '(t_t_zl&255u)>=37u' if variant == 'biased' else '((t_t_zl-21u)&255u)<=218u'
    if variant == 'likely':
        cond = '__builtin_expect(' + cond + ',1)'
    elif variant not in ('plain', 'plain-recompute', 'biased'):
        raise ValueError(variant)
    new = '''t_t_tsm: {const struct t_t_ra *t_t_rr = &t_t_tw[(int32_t)(t_t_w<<6) >> 24];
if((t_t_i<<27)==0u){if((t_t_w << 9) >> 23 == 0u){t_t_zl=t_t_cell_d(t_t_rr,t_t_w,t_t_e);goto t_t_low;}}
t_t_zl=t_t_cell_s(t_t_rr,t_t_w);
if(''' + cond + ''') return t_t_w-(t_t_zl>>8);
t_t_zl=t_t_cell_d(t_t_rr,t_t_w,t_t_e);t_t_q=t_t_zl>>8;'''
    if source.count(old) != 1:
        raise ValueError('nonunique exact family dispatch')
    result = source.replace(old, new)
    if variant in ('plain-recompute', 'biased'):
        # w*(w+1) is even modulo 2^32. Use an independently derived fallback
        # address so the fast-path table pointer need not stay live. The
        # arithmetic transformation is unchanged; charge every extra operation.
        old_call = 't_t_zl=t_t_cell_d(t_t_rr,t_t_w,t_t_e);t_t_q=t_t_zl>>8;'
        new_call = 't_t_zl=t_t_cell_d(&t_t_tw[(int32_t)((t_t_w+((t_t_w*(t_t_w+1u))&1u))<<6)>>24],t_t_w,t_t_e);t_t_q=t_t_zl>>8;'
        if result.count(old_call) != 1:
            raise ValueError('fallback call')
        result = result.replace(old_call, new_call)
        cert['fallback_identity'] = 'w*(w+1) is even modulo 2^32'
    if variant == 'biased':
        # Move the interval [-2,16] wholly to [-18,0] without a runtime add
        # on the fused path. A single low-byte lower-bound test now suffices.
        start = result.index('} t_t_twh =')
        start = result.index('{0u, {', start)
        end = result.index('\n#define t_t_tw', start)
        def bias_row(m):
            fields = [v.strip() for v in m[1].split(',')]
            if len(fields) != 3:
                raise ValueError('biased table row')
            fields[0] = str((int(fields[0].rstrip('u'), 0) + 16) & 0xffffffff) + 'u'
            return '{' + ','.join(fields) + '}'
        region, n = re.subn(r'\{([^{}]+)\}', bias_row, result[start:end])
        if n != 128:
            raise ValueError('biased family size')
        result = result[:start] + region + result[end:]
        old_return = 'return t_t_r->t_t_v + ((t_t_r->t_t_r * t_t_D) >> 12) + ((t_t_r->t_t_p * t_t_D2) >> 17);'
        if result.count(old_return) != 1:
            raise ValueError('original fallback compensation')
        result = result.replace(old_return, old_return.replace('t_t_r->t_t_v +', '(t_t_r->t_t_v-16u) +'))
        cert.update(positive_bias=16, original_minus_fused=[-18, 0], settled_guard=[37, 255])
    cert.update(variant=variant, baseline_sha256=BASE,
                source_sha256=hashlib.sha256(result.encode()).hexdigest(),
                source_bytes=len(result.encode()))
    return result, cert


if __name__ == '__main__':
    source, out, variant = sys.argv[1:]
    result, cert = transform(Path(source).read_text(), variant)
    Path(out).write_text(result)
    print(json.dumps(cert, indent=2))
