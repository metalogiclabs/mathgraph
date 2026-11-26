"""Reconstruct a complete uniform negative-exp family from pinned source.

The general-range prototype is a numerical experiment. New table synthesis,
if admitted, must verify every word in its declared cells before measurement.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
from hot_path_hints import BASE

LO, HI = 0xbe680000, 0xc1000000


def block(source, start):
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', lambda m:' '*len(m[0]), source, flags=re.S)
    opening = clean.index('{', start)
    depth = 1
    end = opening+1
    while depth:
        depth += (clean[end]=='{')-(clean[end]=='}')
        end += 1
    return opening,end


def replace_family(source, replacement):
    if hashlib.sha256(source.encode()).hexdigest()!=BASE:
        raise ValueError('wrong baseline')
    fn = source.index('static inline uint32_t r_eik_exp_r(')
    start = source.index('        if (r_w <= 0xBF801000u) {',fn)
    small1 = source.index('            if (r_w <= 0xBB051000u) {',start)
    _,end1 = block(source,small1)
    small2 = source.index('            if (r_w <= 0xBE680000u) {',end1)
    open2,end2 = block(source,small2)
    end = source.index('        if (r_w >= 0xC2D00000u)',end2)
    prefix = '        if (r_w <= 0xBE680000u) {\n'+source[small1:end1]+'\n'+source[open2:end2]+'\n        }\n'
    return source[:start]+prefix+replacement+source[end:]


if __name__=='__main__':
    original,out = map(Path,sys.argv[1:3])
    candidate = replace_family(original.read_text(),'''        if (r_w < 0xC1000000u) {
            r_cB=&r_exp8_r;
            goto r_negmain_;
        }
''')
    out.write_text(candidate)
    print(json.dumps({'kind':'CANDIDATE_GENERAL_RANGE_REUSE','baseline_sha256':BASE,
                      'domain':[LO,HI], 'source_sha256':hashlib.sha256(candidate.encode()).hexdigest()},indent=2))
