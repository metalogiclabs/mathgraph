"""Price simultaneous central sigmoid/tanh changes before another construction.

Only counts in complete declared regions and emitted bytes change in this
planning model. It is not executable arithmetic or a future-draw verdict.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from hot_path_hints import BASE,TRAIN_SEED


def affected(fn,w):
    y=w&0x7fffffff
    return (fn=='sigmoid' and 0x3e800000<=y<0x40800000) or (fn=='tanh' and 0x3e000000<=y<0x40000000)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--kit',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if hashlib.sha256(a.source.read_bytes()).hexdigest()!=BASE:raise ValueError('source')
    if subprocess.check_output(['git','-C',str(a.kit),'rev-parse','HEAD'],text=True).strip()!='5a32428ad4aa23bce737d50a738ace24ddeeed2e':raise ValueError('kit')
    sys.path.insert(0,str(a.kit.resolve()))
    from eik import toolchain as T,inputs as I,config as K,score as S,fingerprint as F
    from eik.emu import Core
    core=Core(T.guest_image(a.source,'rv32im'),'rv32im');raw={}
    for fn in K.FUNCTIONS:
        raw[fn]={name:[(w,core.call(fn,w)[1]) for w in words] for name,words in I.draw(TRAIN_SEED,fn).items()}
    def model(saving,byte_saving):
        m={'functions':{}}
        for fn,sets in raw.items():
            m['functions'][fn]={}
            for name,words in sets.items():
                counts=[n-saving if affected(fn,w) else n for w,n in words]
                if min(counts)<=0:raise ValueError('nonpositive model count')
                m['functions'][fn][name]={'mean':sum(counts)/len(counts),'p999':S._p(counts,.999)}
        return S.score(m,19272-byte_saving)[0]
    assert abs(model(0,0)-29.051537885810436)<1e-12
    out={'source_sha256':BASE,'seed':TRAIN_SEED,'fingerprint':F.ids(),
        'regions':{'sigmoid_abs':[0x3e800000,0x40800000],'tanh_abs':[0x3e000000,0x40000000]},
        'recorded_bar':27.338009176634163,
        'boundary':'Local planning model; other instructions fixed. Recorded target for orientation, not cross-environment admission or a future-draw verdict.',
        'models':[{'common_instruction_saving':n,'byte_saving':b,'S':model(n,b)} for n in range(7) for b in [0,1024,2048]]}
    a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
