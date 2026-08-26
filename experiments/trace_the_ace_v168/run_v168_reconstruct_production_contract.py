#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, subprocess, zipfile
from pathlib import Path

HINTS = ('trace','ace','submit','submission','runtime','predict','inference','v154','v157','v75','portable')
SKIP = ('transcript','checkpoint','actions-runner/_work/_actions')

def score_name(s:str)->int:
    z=s.lower(); return sum(3 if h in ('v154','v157','submission','submit') else 1 for h in HINTS if h in z)

def workspace_archives(root:Path):
    out=[]
    for p in root.rglob('*'):
        if not p.is_file(): continue
        ps=str(p).lower()
        if any(x in ps for x in SKIP): continue
        if p.suffix.lower() not in ('.zip','.tar','.gz','.tgz'): continue
        rec={'path':str(p),'bytes':p.stat().st_size,'score':score_name(str(p))}
        if p.suffix.lower()=='.zip':
            try:
                with zipfile.ZipFile(p) as z:
                    names=z.namelist()
                rec['entries']=len(names)
                rec['interesting_entries']=[n for n in names if score_name(n)>0][:80]
                rec['score'] += sum(min(score_name(n),4) for n in names[:5000])
            except Exception as e: rec['zip_error']=repr(e)
        out.append(rec)
    return sorted(out,key=lambda r:(r['score'],r['bytes']),reverse=True)[:50]

def git_history(repo:Path):
    cmds=[
      ['git','log','--all','--date=iso','--pretty=format:COMMIT %H %ad %s','--name-only'],
    ]
    try:
      txt=subprocess.check_output(cmds[0],cwd=repo,text=True,errors='replace',timeout=120)
    except Exception as e:
      return {'error':repr(e),'matches':[]}
    blocks=[]; cur=None
    for line in txt.splitlines():
      if line.startswith('COMMIT '):
        if cur: blocks.append(cur)
        cur={'header':line,'files':[],'score':score_name(line)}
      elif cur and line.strip():
        if score_name(line): cur['files'].append(line.strip()); cur['score']+=score_name(line)
    if cur: blocks.append(cur)
    blocks=[b for b in blocks if b['score']>0 or b['files']]
    blocks.sort(key=lambda b:b['score'],reverse=True)
    return {'matches':blocks[:100]}

def repo_current(repo:Path):
    out=[]
    for p in repo.rglob('*'):
      if p.is_file():
        rel=str(p.relative_to(repo))
        s=score_name(rel)
        if s>0 and 'trace_the_ace' in rel.lower(): out.append({'path':rel,'score':s,'bytes':p.stat().st_size})
    return sorted(out,key=lambda x:x['score'],reverse=True)[:100]

def main(a):
    archives=workspace_archives(a.workspace)
    hist=git_history(a.repo)
    current=repo_current(a.repo)
    strong_arch=[x for x in archives if x['score']>=4]
    hist_prod=[x for x in hist.get('matches',[]) if x['score']>=5]
    if strong_arch:
      decision='WORKSPACE_PRODUCTION_ARTIFACT_FOUND'
    elif hist_prod:
      decision='GIT_HISTORY_PRODUCTION_CONTRACT_FOUND'
    else:
      decision='EXACT_SCORED_RUNTIME_NOT_RECOVERED_LOCALLY'
    out={'protocol':'V168_RECONSTRUCT_EXACT_SCORED_RUNTIME','decision':decision,
         'workspace_archives':archives,'git_history_candidates':hist.get('matches',[])[:50],
         'current_repo_candidates':current,
         'next':'If an exact V154/V157 or scored submission runtime is found, restore that tree/archive verbatim and change only its learned payload to full-data V75. Otherwise recover the scored zip externally before claiming a production port.'}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--workspace',type=Path,default=Path('/workspace')); p.add_argument('--repo',type=Path,default=Path('.')); p.add_argument('--out',type=Path,required=True); main(p.parse_args())
