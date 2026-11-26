"""Frozen single-condition compiler-hint search in the three whole kernels.

Every original condition is evaluated once and retains its truth value. The
search varies only advisory branch probabilities. No input-specific dispatch,
target flags, test sets, or arithmetic are changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from hot_path_hints import BASE, body_span, TRAIN_SEED, HELDOUT_SEED


def sites(source):
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', lambda m: ' '*len(m[0]), source, flags=re.S)
    result = []
    for fn in ('exp','tanh','sigmoid'):
        lo, hi = body_span(source,fn)
        for index,m in enumerate(re.finditer(r'\bif\s*\(',clean[lo:hi])):
            start = lo+m.end()
            depth = 1
            end = start
            while depth:
                depth += (clean[end]=='(')-(clean[end]==')')
                end += 1
            cond = source[start:end-1]
            if '__builtin_expect' not in cond:
                result.append({'function':fn,'index':index,'start':start,'end':end-1,
                               'condition':cond,'line':source.count('\n',0,start)+1})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('baseline',type=Path)
    ap.add_argument('out',type=Path)
    a = ap.parse_args()
    source = a.baseline.read_text()
    if hashlib.sha256(source.encode()).hexdigest()!=BASE:
        raise ValueError('wrong baseline')
    a.out.mkdir(parents=True,exist_ok=True)
    variants = []
    for site in sites(source):
        for hint in (0,1):
            name = site['function']+'-'+str(site['index'])+'-'+str(hint)
            expression = '__builtin_expect(!!('+site['condition']+'),'+str(hint)+')'
            candidate = source[:site['start']]+expression+source[site['end']:]
            (a.out/(name+'.c')).write_text(candidate)
            variants.append({'name':name,'hint':hint,**site,
                             'source_sha256':hashlib.sha256(candidate.encode()).hexdigest()})
    protocol = {'baseline_sha256':BASE,'train_seed':TRAIN_SEED,'heldout_seed_frozen':HELDOUT_SEED,
                'minimum_paired_gain':0.005,'variants':variants,
                'boundary':'Development measurement; no full-domain qualification or competition admission claim'}
    (a.out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    print('Frozen',len(variants),'single-condition variants; heldout',HELDOUT_SEED)


if __name__=='__main__':
    main()
