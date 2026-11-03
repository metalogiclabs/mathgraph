"""Source scope and evidence classification for the fixed repository contract."""
from pathlib import Path
import re

MODULE=re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')

def scope(files):
    modules=[];uncovered=[];deleted=[]
    for row in files:
        path=row['filename'];parts=path.split('/')
        if path.startswith('/') or '\\' in path or any(x in ['', '.', '..'] for x in parts):raise ValueError('UNSAFE_SOURCE_PATH')
        if path.startswith('Scripts/') and path.endswith('.lean'):
            name=path[:-5].replace('/','.')
            if not MODULE.fullmatch(name):raise ValueError('UNSUPPORTED_MODULE_NAME')
            (deleted if row['status']=='removed' else modules).append(name)
        else:uncovered.append(path)
    return {'modules':sorted(set(modules)),'uncovered':sorted(set(uncovered)),'deleted_modules':sorted(set(deleted))}

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
