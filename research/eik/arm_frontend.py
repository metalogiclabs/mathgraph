"""Screen Cortex-M immediate returns separately from the large numerical body.

The thresholds are conservative subsets of the existing source's tiny and
saturated ranges. Genuine shared callers provide a normal outlining option;
no compiler attributes, impossible calls or target-dependent preprocessing.
"""
from pathlib import Path
import argparse
import hashlib
import json
from hot_path_hints import BASE, HELDOUT_SEED

VARIANTS = ['shared','shared-tanh','shared-all','shared-all-tiny','shared-all-large','direct-all']
CORE_VARIANTS = ['in-core-all-tiny','in-core-all-large','in-core-all',
                 'in-core-tanh-tiny','in-core-sigmoid-tiny','in-core-exp-tiny']
TRAIN = 150897616


def make(source, variant):
    if hashlib.sha256(source.encode()).hexdigest()!=BASE:
        raise ValueError('wrong baseline')
    if variant not in VARIANTS+CORE_VARIANTS:
        raise ValueError('undeclared variant')
    if variant in CORE_VARIANTS:
        for fn in ['sigmoid','tanh','exp']:
            if 'all' not in variant and fn not in variant:
                continue
            tiny=0x73000000 if fn=='tanh' else 0x65000000
            large=0x83000000 if fn=='tanh' else 0x86000000
            small={'sigmoid':'0x3f000000u','tanh':'t_t_w','exp':'0x3f800000u'}[fn]
            big={'sigmoid':'(t_t_w>>31)?0u:0x3f800000u',
                 'tanh':'(t_t_w&0x80000000u)|0x3f800000u',
                 'exp':'(t_t_w>>31)?0u:0x7f800000u'}[fn]
            body='\nuint32_t fe_t=t_t_w<<1;\n'
            if 'large' not in variant:
                body+=f'if(fe_t<{hex(tiny)}u) return {small};\n'
            if 'tiny' not in variant:
                body+=f'''if(fe_t>={hex(large)}u) {{
    if(fe_t>0xff000000u) return t_t_w|0x00400000u;
    return {big};
}}
'''
            anchor=f'static uint32_t t_t_eik_{fn}(uint32_t t_t_w)\n{{'
            if source.count(anchor)!=1:raise ValueError('core anchor')
            source=source.replace(anchor,anchor+body)
        return source
    shared = variant!='direct-all'
    prefix = '''static uint32_t arm_core(uint32_t w,uint32_t operation) {
    if(operation==0u) return t_t_eik_sigmoid(w);
    if(operation==1u) return t_t_eik_tanh(w);
    return t_t_eik_exp(w);
}
''' if shared else ''
    for operation,fn in enumerate(['sigmoid','tanh','exp']):
        old=f'static uint32_t t_eik_{fn}(uint32_t t_w) {{ return t_t_eik_{fn}(t_w); }}'
        if source.count(old)!=1:
            raise ValueError('wrapper anchor')
        tiny=0x73000000 if fn=='tanh' else 0x65000000
        large=0x83000000 if fn=='tanh' else 0x86000000
        small_out={'sigmoid':'0x3f000000u','tanh':'t_w','exp':'0x3f800000u'}[fn]
        big_out={'sigmoid':'(t_w>>31)?0u:0x3f800000u',
                 'tanh':'(t_w&0x80000000u)|0x3f800000u',
                 'exp':'(t_w>>31)?0u:0x7f800000u'}[fn]
        enabled=variant!='shared' and (variant!='shared-tanh' or fn=='tanh')
        body=f'static uint32_t t_eik_{fn}(uint32_t t_w) {{\n'
        if enabled:
            body+='    uint32_t t=t_w<<1;\n'
            if variant!='shared-all-large':
                body+=f'    if(t<{hex(tiny)}u) return {small_out};\n'
            if variant!='shared-all-tiny':
                body+=f'''    if(t>={hex(large)}u) {{
        if(t>0xff000000u) return t_w|0x00400000u;
        return {big_out};
    }}
'''
        body+=f'    return arm_core(t_w,{operation}u);\n}}' if shared else f'    return t_t_eik_{fn}(t_w);\n}}'
        source=source.replace(old,body)
    anchor='static uint32_t t_eik_sigmoid(uint32_t t_w) {\n'
    if source.count(anchor)!=1:raise ValueError('insertion anchor')
    return source.replace(anchor,prefix+anchor)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('baseline',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name in VARIANTS+CORE_VARIANTS:
        source=make(a.baseline.read_text(),name);(a.out/(name+'.c')).write_text(source)
        rows.append({'name':name,'source_sha256':hashlib.sha256(source.encode()).hexdigest()})
    (a.out/'protocol.json').write_text(json.dumps({
        'baseline_sha256':BASE,'train_seed':TRAIN,'heldout_seed_frozen':HELDOUT_SEED,
        'minimum_training_gain':0.005,'target':'thumbv6m','variants':rows,
        'boundary':'Compiled cost and scored outputs first; no all-input qualification claimed'},indent=2)+'\n')
