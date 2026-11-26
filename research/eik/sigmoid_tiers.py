"""Two fixed RV32IM sigmoid tier experiments; neither is a retained winner."""
import argparse
import hashlib
import json
from pathlib import Path
from hot_path_hints import BASE, TRAIN_SEED, HELDOUT_SEED
from uniform_negative_exp import block


def variants(source):
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong baseline')
    i = source.index('        if (r_V8 >= r_w) {')
    opening, end = block(source, i)
    # On am_, w < 0xc0000000. Its inner test requires V8 >= 0xc00000e0,
    # so the outer comparison is implied whenever the inner body is entered.
    removed = source[:i]+source[opening+1:end-1]+source[end:]
    start = source.index('    uint32_t r_V8 = ', source.index('r_am_: {'))
    endline = source.index('\n', start)
    extra = '''
    uint32_t uk=8u-(r_V8>>31)-(r_V8>=0xc00000e0u);
    uint32_t uq=255u-r_V8+(1u<<(uk-1u));
    uint32_t um=(1u<<uk)-2u;
    if ((uq&um)!=um) return 0x3a000000u+(uk<<23)+(uq>>uk);
'''
    return {'remove-implied-gate': removed,
            'dynamic-tier': source[:endline]+extra+source[endline:]}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('baseline', type=Path)
    ap.add_argument('out', type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    records = []
    for name, source in variants(a.baseline.read_text()).items():
        (a.out/(name+'.c')).write_text(source)
        records.append({'name': name, 'sha256': hashlib.sha256(source.encode()).hexdigest()})
    (a.out/'protocol.json').write_text(json.dumps({
        'baseline_sha256': BASE, 'train_seed': TRAIN_SEED,
        'heldout_seed_frozen': HELDOUT_SEED, 'variants': records}, indent=2)+'\n')
