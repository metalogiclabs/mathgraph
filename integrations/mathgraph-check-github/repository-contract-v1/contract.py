"""Source scope and evidence classification for the fixed repository contract."""
from pathlib import Path
import re

MODULE=re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')

def scope(files):
    modules=[];uncovered=[];deleted=[];base=[]
    def as_module(path):
        parts=path.split('/')
        if path.startswith('/') or '\\' in path or any(x in ['', '.', '..'] for x in parts):raise ValueError('UNSAFE_SOURCE_PATH')
        if not path.startswith('Scripts/') or not path.endswith('.lean'):return None
        name=path[:-5].replace('/','.')
        if not MODULE.fullmatch(name):raise ValueError('UNSUPPORTED_MODULE_NAME')
        return name
    for row in files:
        path=row['filename'];name=as_module(path);status=row['status']
        if status not in ['added','modified','removed','renamed','copied']:raise ValueError('UNSUPPORTED_DIFF_STATUS')
        if status=='renamed':
            previous=as_module(row['previous_filename'])
            if previous:
                base.append(previous)
                if previous!=name:deleted.append(previous)
        if name:
            (deleted if row['status']=='removed' else modules).append(name)
            if status in ['modified','removed']:base.append(name)
        else:uncovered.append(path)
    return {'modules':sorted(set(modules)),'uncovered':sorted(set(uncovered)),'deleted_modules':sorted(set(deleted)),'base_modules':sorted(set(base))}

def pinned_files(data,base,head):
    commits=data.get('commits');files=data.get('files');count=data.get('total_commits')
    if (data.get('base_commit',{}).get('sha')!=base or not isinstance(commits,list)
        or type(count) is not int or count!=len(commits) or count>250
        or not isinstance(files,list) or len(files)>=300):raise ValueError('INCOMPLETE_SHA_BOUND_COMPARISON')
    if (commits and commits[-1].get('sha')!=head) or (not commits and (base!=head or files)):raise ValueError('COMPARISON_HEAD_MISMATCH')
    return files

def required_roots(root,modules):
    for module in modules:
        if not MODULE.fullmatch(module) or not (Path(root)/Path(module.replace('.','/')+'.lean')).is_file():raise ValueError('EXPECTED_MODULE_ABSENT:'+module)
    return sorted(set(modules))

def imports(text):
    # Comments are ignored only for dependency discovery; Lean remains the parser.
    out=[];i=0;depth=0;string=False
    while i<len(text):
        if depth:
            if text[i:i+2]=='/-':depth+=1;i+=2
            elif text[i:i+2]=='-/':depth-=1;i+=2
            else:
                out.append('\n' if text[i]=='\n' else ' ');i+=1
        elif string:
            if text[i]=='\\':out.extend('  ');i+=2
            elif text[i]=='"':string=False;out.append(' ');i+=1
            else:out.append('\n' if text[i]=='\n' else ' ');i+=1
        elif text[i:i+2]=='/-':depth=1;out.extend('  ');i+=2
        elif text[i:i+2]=='--':
            j=text.find('\n',i);i=len(text) if j<0 else j
        elif text[i]=='"':string=True;out.append(' ');i+=1
        else:out.append(text[i]);i+=1
    found=[]
    for line in ''.join(out).splitlines():
        m=re.match(r'^\s*(?:public\s+)?(?:meta\s+)?import\s+(?:all\s+)?(.+?)\s*$',line)
        if m:
            for token in m[1].split():
                if not MODULE.fullmatch(token):raise ValueError('UNSUPPORTED_IMPORT_SYNTAX')
                found.append(token)
    return found

def closure(root,modules):
    root=Path(root).resolve();seen=set();pending=list(modules)
    while pending:
        name=pending.pop()
        if name in seen:continue
        if not MODULE.fullmatch(name) or not name.startswith('Scripts.'):raise ValueError('OUTSIDE_NATIVE_MODULE_SCOPE')
        p=root/Path(name.replace('.','/')+'.lean')
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):raise ValueError('MISSING_OR_UNSAFE_IMPORT')
        seen.add(name)
        for dep in imports(p.read_text()):
            if dep.startswith('Scripts.'):pending.append(dep)
            elif dep.split('.')[0] not in ['Lean','Std','Init','Lake']:raise ValueError('EXTERNAL_PROJECT_IMPORT:'+dep)
    return sorted(seen)

def comparison(base,head):
    if not base.get('qualified') or not head.get('qualified'):return 'UNKNOWN'
    b,h=base['failed'],head['failed']
    if b and h:return 'FAILURE_ON_BOTH_REVISIONS'
    if h:return 'NEW_FROZEN_PROBE_FAILURE'
    if b:return 'RESOLVED_FROZEN_PROBE_FAILURE'
    return 'NO_FAILURE_IN_FROZEN_CORPUS'


def hosted_snapshot(data,repo,number,base,head):
    if data.get('schema')!='mathgraph.repository-contract.snapshot.v1' or data.get('repository')!=repo:raise ValueError('INVALID_HOSTED_SNAPSHOT')
    pr=data.get('pr',{})
    if pr.get('number')!=number or pr.get('state')!='open':raise ValueError('HOSTED_PR_MISMATCH')
    for side,revision in [('base',base),('head',head)]:
        row=pr.get(side,{})
        if row.get('sha')!=revision or row.get('repo',{}).get('full_name')!=repo or row['repo'].get('private') is not False:raise ValueError('HOSTED_SOURCE_MISMATCH')
    diff=data.get('comparison',{});files=pinned_files(diff,base,head)
    if len(files)!=pr.get('changed_files'):raise ValueError('INCOMPLETE_HOSTED_COMPARISON')
    return pr,diff
