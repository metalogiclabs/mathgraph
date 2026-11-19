#!/usr/bin/env python3
"""Independent finite RFC 9484 §4.7.3 oracle; no production imports."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

SHA = '9ee608a68fbbc6c377d13da4df2a269580b78909'
RFC = 'https://www.rfc-editor.org/rfc/rfc9484.html#section-4.7.3'
ROUTES = [dict(version=v, start=a, end=b, protocol=p)
          for v in (4,6) for p in (0,6,17) for a in range(4) for b in range(4)]
assert len(ROUTES)==96

def oracle(rs):
    if any(r['start'] > r['end'] for r in rs): return 'MUST_ABORT'
    for i,a in enumerate(rs):
        for b in rs[i+1:]:
            if a['version']>b['version']: return 'MUST_ABORT'
            if a['version']==b['version'] and a['protocol']>b['protocol']: return 'MUST_ABORT'
            if a['version']==b['version'] and a['protocol']==b['protocol'] and a['end']>=b['start']: return 'MUST_ABORT'
    for a,b in itertools.combinations(rs,2):
        if (a['version']==b['version'] and a['protocol']!=b['protocol']
                and 0 in (a['protocol'],b['protocol'])
                and max(a['start'],b['start']) <= min(a['end'],b['end'])):
            return 'OPTIONAL_ABORT'
    return 'NO_MANDATORY_ABORT'

def conventional(rs):
    if any(r['start'] > r['end'] for r in rs): return 'MUST_ABORT'
    for a,b in itertools.combinations(rs,2):
        ka=(a['version'],a['protocol']); kb=(b['version'],b['protocol'])
        if ka>kb or (ka==kb and a['end']>=b['start']): return 'MUST_ABORT'
    for a,b in itertools.combinations(rs,2):
        if (a['version']==b['version'] and a['protocol']!=b['protocol']
                and 0 in (a['protocol'],b['protocol'])
                and max(a['start'],b['start']) <= min(a['end'],b['end'])):
            return 'OPTIONAL_ABORT'
    return 'NO_MANDATORY_ABORT'

def corpus():
    yield []
    for a in ROUTES: yield [a]
    for a,b in itertools.product(ROUTES, repeat=2): yield [a,b]
    state=0x9484
    for _ in range(1024):
        picks=[]
        for _ in range(3):
            state=(1664525*state+1013904223)&0xffffffff
            picks.append(state%96)
        yield [ROUTES[i] for i in picks]

def main():
    cases=[]
    for i,rs in enumerate(corpus()):
        p=oracle(rs)
        if conventional(rs)!=p: raise RuntimeError('baseline diverged at '+str(i))
        cases.append(dict(id=f'rfc9484-{i:05d}', routes=rs, oracle=p))
    assert len(cases)==10337
    counts=dict(sorted(Counter(c['oracle'] for c in cases).items()))
    assert counts=={'MUST_ABORT':8664,'NO_MANDATORY_ABORT':1387,'OPTIONAL_ABORT':286},counts
    record={'schema':'mathgraph.rfc9484.route-order.v0.1','source_rfc':RFC,
            'upstream_sha':SHA,'input_domain':'0,1,2 routes exhaustive + 1024 seeded triples',
            'status':'BOUNDED_STUDY_ORACLE_NOT_INDEPENDENT_HUMAN_ADJUDICATED','cases':cases}
    b=(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode()
    root=Path(__file__).resolve().parent
    (root/'oracle_cases.json').write_bytes(b)
    sha=hashlib.sha256(b).hexdigest()
    print(json.dumps({'cases':len(cases),'counts':counts,'conventional_tie':len(cases),'corpus_sha256':sha},sort_keys=True))
    (root/'ORACLE_RESULT.json').write_text(json.dumps({'count':len(cases),'verdicts':counts,
        'conventional_script_tie':len(cases),'corpus_sha256':sha,
        'scope':'finite, source-exposed, unaudited oracle; no human baseline'},indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
