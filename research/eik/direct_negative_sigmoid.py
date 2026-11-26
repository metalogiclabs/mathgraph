"""Direct float-word cubics over a complete negative sigmoid family.

Fit parameters are proposals; acceptance checks every word of every complete
cell against a pinned source oracle. Ambiguous quotients use the old evaluator.
No scoring input is used to construct coefficients, activation, or guards.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import numpy as np

BASE = '8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37'
LO, HI, K = 0xbe600000, 0xc0000000, 18
GUARDS = (8, 16, 32, 64)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--oracle', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    source = a.baseline.read_text()
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong source oracle fixture')
    a.out.mkdir(parents=True, exist_ok=True)
    lib = C.CDLL(str(a.oracle.resolve()))
    oracle = lib.direct_ns_outputs
    oracle.argtypes = [C.c_uint32, C.c_uint32, C.POINTER(C.c_uint32)]
    n = 1 << K
    u = np.arange(n, dtype=np.int64) << (32-K)
    x = np.arange(n, dtype=np.float64) / n
    fit_indices = np.unique(np.linspace(0, n-1, 4097).astype(np.int64))
    records = []
    digest = hashlib.sha256()
    for lo in range(LO, HI, n):
        words = np.empty(n, dtype=np.uint32)
        oracle(lo, n, words.ctypes.data_as(C.POINTER(C.c_uint32)))
        digest.update(words.tobytes())
        rec = {'lo': lo, 'hi': lo+n, 'prefix': 0x3e, 'accepted': False}
        if not np.all(words >> 24 == 0x3e):
            rec['reason'] = 'output prefix changes or lies outside the selected representation'
            records.append(rec)
            continue
        y = (words & 0xffffff).astype(np.int64)
        center = int(y[n//2])
        proposal = np.polynomial.polynomial.polyfit(x[fit_indices], y[fit_indices]-center, 3)
        c1, c2, c3 = np.rint(proposal[1:]*256).astype(np.int64).tolist()
        low2, high2 = c2+min(0,c3), c2+max(0,c3)
        low1, high1 = c1+min(0,low2), c1+max(0,high2)
        if not all(-(1<<31) <= z < (1<<31) for z in [c1,c2,c3,low2,high2,low1,high1]):
            rec['reason'] = 'coefficient or Horner intermediate range'
            records.append(rec)
            continue
        p = (c3*u) >> 32
        p = ((c2+p)*u) >> 32
        p = ((c1+p)*u) >> 32
        lower = int((y*256-p).max())
        upper = int(((y+1)*256-1-p).min())
        need = max(1, lower-upper)
        rec.update(coefficients=[lower,c1,c2,c3], minimum_guard=need,
                   intermediate_bounds=[low2,high2,low1,high1])
        if not 0 <= lower < (1<<32) or int((lower+p).min()) < 0 or int((lower+p).max()) >= (1<<32):
            rec['reason'] = 'direct unsigned output range'
            records.append(rec)
            continue
        q = lower+p
        rec['accepted'] = need <= max(GUARDS)
        for guard in GUARDS:
            if need > guard:
                continue
            settled = (q & (256-guard)) != 0
            assert np.all((q[settled] >> 8) == y[settled])
            rec.setdefault('guard_replays', {})[str(guard)] = {
                'words': n, 'settled': int(settled.sum()), 'mismatches': 0}
        records.append(rec)
        if len(records) % 16 == 0:
            print('complete cells',len(records),'last guard',need,flush=True)
    common = {'baseline_sha256': BASE, 'oracle_library_sha256': hashlib.sha256(a.oracle.read_bytes()).hexdigest(),
              'oracle_output_sha256': digest.hexdigest(), 'domain': [LO,HI],
              'cell_bits': K, 'words_enumerated': HI-LO, 'cells': records,
              'boundary': 'Source-relative complete-cell numerical synthesis, not independent all-input reference qualification'}
    (a.out/'synthesis.json').write_text(json.dumps(common,indent=2)+'\n')
    for guard in GUARDS:
        active = [r for r in records if r.get('accepted') and r['minimum_guard'] <= guard]
        coeffs = [r['coefficients'] if r in active else [0,0,0,0] for r in records]
        table = 'struct direct_ns_row {uint32_t c0;int32_t c1,c2,c3;};\n'
        table += 'static const struct direct_ns_row direct_ns_rows['+str(len(records))+']={\n'
        table += ',\n'.join('{'+str(c[0])+'u,'+','.join(map(str,c[1:]))+'}' for c in coeffs)+'\n};\n'
        insert = 'static inline uint32_t r_eik_sigmoid_r(uint32_t r_w)'
        if source.count(insert) != 1:
            raise ValueError('sigmoid insertion anchor')
        candidate = source.replace(insert,table+insert)
        anchor = 'r_am_: {\n'
        if candidate.count(anchor) != 1:
            raise ValueError('negative family anchor')
        block = '''r_am_: {
    {
        const struct direct_ns_row *dr=&direct_ns_rows[(r_w>>18)-''' + str(LO>>18) + '''u];
        uint32_t du=r_w<<14;
        int32_t ds=dr->c2+r_mulhsx_r(dr->c3,du);
        ds=dr->c1+r_mulhsx_r(ds,du);
        uint32_t dv=dr->c0+(uint32_t)r_mulhsx_r(ds,du);
        if(dv & ''' + str(256-guard) + '''u) return 0x3e000000u|(dv>>8);
    }
'''
        candidate = candidate.replace(anchor,block)
        if len(candidate.encode()) > 262144:
            raise ValueError('source cap')
        name = 'guard'+str(guard)
        (a.out/(name+'.c')).write_text(candidate)
        receipt = {'guard':guard,'active_cells':len(active),'total_cells':len(records),
                   'covered_words':len(active)*n,'source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                   'source_bytes':len(candidate.encode()), 'baseline_sha256':BASE}
        (a.out/(name+'-certificate.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt),flush=True)


if __name__ == '__main__':
    main()
