"""Replace repeated monotone tail searches with a fixed integer decision tree.

The transformation is certified against the original table and loop on the
complete partition induced by its thresholds and counter-initializer changes.
Original paths remain for every input outside the declared tail domains.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

BASE = '8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37'
VARIANTS = ['tanh-sum', 'tanh-tree', 'sigmoid-tree', 'tails-tree']


def table(source):
    m=re.search(r't_t_epa\[256\]\s*=\s*\{(.*?)\};',source,re.S)
    assert m
    a=[[int(x.strip().rstrip('u'),0) for x in r.split(',')]
       for r in re.findall(r'\{([^{}]+)\}',m[1])]
    assert len(a)==256 and all(len(r)==6 for r in a)
    return [r[-1] for r in a]


def sig_original(a, cuts):
    n=(13 >> ((a>>19)-0x82b)) | 1
    while a < cuts[173+n]:
        n+=1
        assert n<=23
    return n


def rank(a, thresholds):
    return 1+sum(a<t for t in thresholds)


def sig_certificate(cuts, proposed=None):
    lo,hi=0x41580000,0x418aa123
    thresholds=cuts[174:196]
    assert len(thresholds)==22 and all(a>b for a,b in zip(thresholds,thresholds[1:]))
    assert cuts[196]<lo and thresholds[0]<hi
    boundaries={lo,hi,*thresholds}
    boundaries.update(range(((lo>>19)+1)<<19,hi,1<<19))
    boundaries=sorted(boundaries)
    count=0
    for a,b in zip(boundaries,boundaries[1:]):
        for w in set([a,b-1,(a+b-1)//2]):
            assert sig_original(w,cuts)==rank(w,thresholds if proposed is None else proposed)
            count+=1
    return {'domain_lo':lo,'domain_hi_exclusive':hi,'partition_intervals':len(boundaries)-1,
            'exact_partition_checks':count,'thresholds':thresholds}


def decision_tree(thresholds, var, prefix, first=1):
    if not thresholds:
        return 'return '+prefix+str(first)+'u;'
    j=len(thresholds)//2
    cut=thresholds[j]
    return ('if ('+var+'>=0x'+format(cut,'08x')+'u) {'+
            decision_tree(thresholds[:j],var,prefix,first)+'} else {'+
            decision_tree(thresholds[j+1:],var,prefix,first+j+1)+'}')


def transform(source, variant):
    assert hashlib.sha256(source.encode()).hexdigest()==BASE
    assert variant in VARIANTS
    cuts=table(source)
    cert={'baseline_sha256':BASE,'variant':variant,'source_is_published_entry':49}
    if variant in ['tanh-sum','tanh-tree','tails-tree']:
        assert cuts[169:173]==[0x820ec57e,0x82069926,0x820136f6,0x81fa6324]
        assert cuts[172]<0x82000000<cuts[171]<cuts[170]<cuts[169]<0x82205968
        for w in [0x82000000,0xffffffff,*[x+d for x in [0x82205968,*cuts[169:172]] for d in [-1,0,1]]]:
            old=0
            if w<0x82205968:
                old=1
                while w<cuts[168+old]:old+=1
            new=sum(w<t for t in [0x82205968,*cuts[169:172]])
            assert old==new
        if variant=='tanh-sum':
            code='uint32_t tr_n=(t_t_tt<0x82205968u)+(t_t_tt<0x820ec57eu)+(t_t_tt<0x82069926u)+(t_t_tt<0x820136f6u);'
        else:
            code='uint32_t tr_n; if(t_t_tt>=0x82069926u){if(t_t_tt>=0x820ec57eu) tr_n=t_t_tt<0x82205968u;else tr_n=2u;}else tr_n=3u+(t_t_tt<0x820136f6u);'
        old='t_t_rest: {uint32_t t_t_tt=t_t_w<<1; '
        new=old+'if(t_t_tt>=0x82000000u){'+code+'return t_t_tanh_pm1[t_t_w>>31]-tr_n;} '
        assert source.count(old)==1
        source=source.replace(old,new)
        cert['tanh']={'domain_lo':0x82000000,'complete_integer_intervals':5,
                      'thresholds':[0x82205968,*cuts[169:172]],'outside_domain_unchanged':True}
    if variant in ['sigmoid-tree','tails-tree']:
        cert['sigmoid']=sig_certificate(cuts)
        old='static uint32_t t_t_sig_plateau(uint32_t t_t_a){'
        new=old+'\nif(t_t_a>=0x41580000u && t_t_a<0x418aa123u){'+decision_tree(cuts[174:196],'t_t_a','0x3f800000u-')+'}\n'
        assert source.count(old)==1
        source=source.replace(old,new)
    assert len(source.encode())<=262144
    cert['source_sha256']=hashlib.sha256(source.encode()).hexdigest()
    return source,cert


if __name__=='__main__':
    src,out,v=sys.argv[1:]
    s,c=transform(Path(src).read_text(),v)
    Path(out).write_text(s)
    print(json.dumps(c,indent=2))
