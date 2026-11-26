"""Split complete Horner cells into certified quadratic envelopes.

For x = h+z, |z| <= r, replace x^3 by
3h*x^2 + (-3h^2 + 3r^2/4)*x + h^3 - 3h*r^2/4.
The omitted cubic is z^3-3r^2*z/4, bounded by r^3/4.
The original cubic has floor error <= 7/4; the quadratic <= 3/2;
rounding three coefficients adds <= 7/8 when |x| <= 1/2.
Thus the integer envelope error is <= 33/8 + |d|*r^3/4.

Only the declared, complete mathematical cell families are transformed.
Their original implementation remains the fallback. No benchmark inputs
are used to construct coefficients, partitions or guards.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import re
import sys

BASE = '3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
VARIANTS = {
    'tl2': (2, 0, True),
    'tl4': (4, 0, True),
    'ta2': (0, 2, True),
    'ta2-compact': (0, 2, False),
    'both2': (2, 2, True),
    'both4': (4, 2, True),
}


def one(s, a, b):
    assert s.count(a) == 1, a[:100]
    return s.replace(a, b)


def nearest(x):
    # A deterministic ties-to-even coefficient rounding, using rational arithmetic.
    lo = x.numerator // x.denominator
    rem = x - lo
    return lo + (rem > F(1, 2) or (rem == F(1, 2) and lo % 2 != 0))


def cell_rows(source, name):
    m = re.search(r'\b' + name + r'\[\d+\] = \{(.*?)\};', source, re.S)
    assert m
    return [[int(v.strip().rstrip('u'), 0) for v in r.split(',')]
            for r in re.findall(r'\{([^{}]+)\}', m[1])]


def transformed_rows(source, table, n):
    assert n in (2, 4)
    original = cell_rows(source, table)
    radius = F(1, 4*n)
    bound = max(F(33, 8) + abs(row[3])*radius**3/4 for row in original)
    E = 1
    while E < bound:
        E = 2*E+1
    assert E < (128 if table == 'ta_r' else 512)//2
    rows = []
    for i, (a, b, c, d, *_) in enumerate(original):
        # tl's phase is positive for even indices; ta's phase is negative.
        lower = F(-1, 2) if ((i % 2 == 1) if table == 'tl_r' else (i % 2 == 0)) else F(0)
        for j in range(n):
            h = lower + F(2*j+1, 4*n)
            ka = h**3 - 3*h*radius**2/4
            kb = -3*h*h + 3*radius**2/4
            kc = 3*h
            aa = (a + nearest(d*ka) + E) & 0xffffffff
            bb, cc = b+nearest(d*kb), c+nearest(d*kc)
            assert -(1 << 31) <= bb < (1 << 31)
            assert -(1 << 31) <= cc < (1 << 31)
            for x in (h-radius, h+radius):
                inner = bb + (cc*x).__floor__()
                assert -(1 << 31) <= inner < (1 << 31)
            rows.append((aa, bb, cc))
    return rows, {'original_cells': len(original), 'subdivisions': n,
                  'quadratic_cells': len(rows), 'radius': str(radius),
                  'uniform_error_bound': str(bound), 'positive_bias': E}


def transform(source, variant):
    assert hashlib.sha256(source.encode()).hexdigest() == BASE
    tl_n, ta_n, padded = VARIANTS[variant]
    definitions = ['struct sq_row { uint32_t a; int32_t b, c;' +
                   (' uint32_t pad;' if padded else '') + ' };']
    definitions.append('''static inline uint32_t sq_eval(const struct sq_row *r, int32_t t) {
    int32_t s=r->b+mulhs_r(r->c,t);
    return r->a+(uint32_t)mulhs_r(s,t);
}''')
    certificate = {'variant': variant, 'baseline_sha256': BASE,
                   'row_bytes': 16 if padded else 12, 'families': {}}
    changes = []
    for table, n in [('tl_r', tl_n), ('ta_r', ta_n)]:
        if not n:
            continue
        rows, info = transformed_rows(source, table, n)
        certificate['families'][table] = info
        E = info['positive_bias']
        tag = 'sq_' + table
        definitions.append('static const struct sq_row '+tag+'['+str(len(rows))+']={\n'+
                           ',\n'.join('{'+str(a)+'u,'+str(b)+','+str(c)+(',0u' if padded else '')+'}'
                                     for a,b,c in rows)+'\n};')
        lg = n.bit_length()-1
        if table == 'tl_r':
            mask = 511 & ~(2*E+1)
            old = '''        const struct rl_r *r = &tl_r[(w >> 18) - 0xF9Cu];
        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));'''
            new = f'''        const struct sq_row *qr=&{tag}[(w>>{18-lg})-{0xf9c*n}u];
        uint32_t Q=sq_eval(qr,(int32_t)(w<<13));
        if (Q & {mask}u) return 0x3F000000u+(Q>>9);
'''+old
            changes.append((old, new))
        else:
            old = '''        const struct rx_r *r = &ta_r[(t >> 18) - 0x1FFFu];
        th_ = w << 14;
        uint32_t V = rx_cell_r(r, (int32_t)th_);'''
            new = f'''        const struct sq_row *qr=&{tag}[(t>>{18-lg})-{0x1fff*n}u];
        uint32_t Q=sq_eval(qr,(int32_t)(w<<14));
        if (Q & {127 & ~(2*E+1)}u) return w-(Q>>7);
'''+old
            changes.append((old, new))
            old = '''        const struct rx_r *r = &ta_r[(w >> 17) - 0x203Fu];
        uint32_t Z = rx_cell_r(r, (int32_t)(w << 14)) - (w << 7) + 0x40u;'''
            new = f'''        const struct sq_row *qr=&{tag}[(w>>{17-lg})-{0x203f*n}u];
        uint32_t Q=sq_eval(qr,(int32_t)(w<<14))-(w<<7)+0x40u;
        if (Q & {255 & ~(2*E+1)}u) return 0x3F800000u-(Q>>8);
'''+old
            changes.append((old, new))
    for a, b in changes:
        source = one(source, a, b)
    marker = 'static inline uint32_t rb_cell_r'
    source = one(source, marker, '\n'.join(definitions)+'\n'+marker)
    assert len(source.encode()) <= 262144
    certificate['source_sha256'] = hashlib.sha256(source.encode()).hexdigest()
    return source, certificate


if __name__ == '__main__':
    src, out, variant = sys.argv[1:]
    s, cert = transform(Path(src).read_text(), variant)
    Path(out).write_text(s)
    print(json.dumps(cert, indent=2))
