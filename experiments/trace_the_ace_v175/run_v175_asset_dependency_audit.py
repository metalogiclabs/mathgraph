#!/usr/bin/env python3
import json, re, zipfile, shutil
from pathlib import Path
import numpy as np

WS=Path('/workspace')
ZIP=WS/'V157_RECOVERED_SUBMISSION.zip'
OUT=WS/'trace-ace-results/v175'
EX=WS/'trace-ace-work/v175_v157'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if EX.exists(): shutil.rmtree(EX)
    EX.mkdir(parents=True)
    with zipfile.ZipFile(ZIP) as z: z.extractall(EX)
    pyfiles=sorted(EX.rglob('*.py'))
    manifest_files=sorted(EX.rglob('manifest.json'))
    npzs=sorted(EX.rglob('*.npz'))
    report={'protocol':'V175_RECOVERED_RUNTIME_ASSET_DEPENDENCY_AUDIT','zip':str(ZIP),'python_files':[],'manifests':[],'npz':[]}
    for p in pyfiles:
        txt=p.read_text(errors='ignore')
        hits=[]
        for i,line in enumerate(txt.splitlines(),1):
            low=line.lower()
            if any(k in low for k in ['np.load','manifest','prior','objective','asset','probability','logit','sigmoid','clip','calib','predict']):
                hits.append({'line':i,'text':line[:500]})
        report['python_files'].append({'path':str(p.relative_to(EX)),'hits':hits[:400]})
    for p in manifest_files:
        try: obj=json.loads(p.read_text())
        except Exception as e: obj={'error':repr(e),'raw':p.read_text(errors='ignore')[:10000]}
        report['manifests'].append({'path':str(p.relative_to(EX)),'content':obj})
    for p in npzs:
        z=np.load(p,allow_pickle=True)
        keys=[]
        for k in z.files:
            a=z[k]
            item={'key':k,'shape':list(a.shape),'dtype':str(a.dtype)}
            if a.size<=20:
                try:item['values']=a.tolist()
                except:pass
            else:
                try:
                    if np.issubdtype(a.dtype,np.number):
                        item.update(min=float(np.nanmin(a)),max=float(np.nanmax(a)),mean=float(np.nanmean(a)))
                except: pass
            keys.append(item)
        report['npz'].append({'path':str(p.relative_to(EX)),'keys':keys})
    # Explicitly classify likely label-derived assets by source references/name.
    allhits='\n'.join(h['text'] for f in report['python_files'] for h in f['hits'])
    names=[x['key'] for n in report['npz'] for x in n['keys']]
    report['likely_label_derived_keys']=[k for k in names if any(s in k.lower() for s in ['prior','rate','mean','correct','coef','intercept','calib','objective'])]
    report['decision']='ASSET_LINEAGE_EXPOSED'
    report['residual']='Use exact source/key map to rebuild every label-derived asset from the complement-only 33,572 rows, then rerun V174 sample unchanged.'
    (OUT/'v175_results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2)[:60000])
if __name__=='__main__': main()
