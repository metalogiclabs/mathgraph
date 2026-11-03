"""Finite parity admission. Differences are observations, not automatic bug claims."""
from pathlib import Path
import re,importlib.util
_shared=Path(__file__).resolve().parents[1]/'repository-contract-v1/contract.py'
_spec=importlib.util.spec_from_file_location('cli_shared_contract',_shared);shared=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(shared)

def safe_path(name):
    p=Path(name)
    if not isinstance(name,str) or not name or '\\' in name or p.is_absolute() or any(x in ['', '.', '..'] for x in name.split('/')) or name.split('/')[0] in ['.lake','scripts','.git']:raise ValueError('UNSAFE_FIXTURE_PATH')
    return p

def effects(before,after):
    return {p:{'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)}

def project_stdout(text,mode,contract):
    if mode=='exact':return text
    if mode!='generator-provenance':raise ValueError('UNKNOWN_STDOUT_PROJECTION')
    parts=text.splitlines(keepends=True);hits=[i for i,l in enumerate(parts) if l.rstrip('\r\n') in contract['generator_provenance_lines']]
    if len(hits)!=1:raise ValueError('GENERATOR_PROVENANCE_NOT_RECOGNIZED')
    i=hits[0];ending=parts[i][len(parts[i].rstrip('\r\n')):];parts[i]='-- GENERATED: declared generator provenance'+ending
    return ''.join(parts)

def compare_case(base,repeat,head,case,contract):
    result={'state':'UNKNOWN','differences':[]}
    if not all(o.get('complete') is True for o in [base,repeat,head]):return {**result,'reason':'EXECUTION_INCOMPLETE'}
    if base['exit']!=case['expected_base_exit']:return {**result,'reason':'REFERENCE_EXIT_UNEXPECTED'}
    if any(base.get(k)!=repeat.get(k) for k in ['exit','stdout','stderr','effects']):return {**result,'reason':'REFERENCE_NONDETERMINISTIC'}
    try:
        for key,mode in case['comparison'].items():
            b,h=base[key],head[key]
            if key=='stdout':b,h=project_stdout(b,mode,contract),project_stdout(h,mode,contract)
            elif key=='stderr' and mode=='nonempty':
                if not b:return {**result,'reason':'REFERENCE_DIAGNOSTIC_ABSENT'}
                b,h=True,bool(h)
            elif mode!='exact':raise ValueError('UNKNOWN_CHANNEL_PROJECTION')
            if b!=h:result['differences'].append(key)
    except (KeyError,ValueError) as e:return {**result,'reason':str(e)}
    result['state']='DIFFERENCE' if result['differences'] else 'PARITY';return result

def project_closure(root,roots):
    root=Path(root).resolve();seen=set();pending=list(roots)
    while pending:
        name=pending.pop()
        if name in seen:continue
        if not shared.MODULE.fullmatch(name) or name.split('.')[0] not in ['Scripts','L4YAML']:raise ValueError('OUTSIDE_REVIEWED_PROJECT')
        p=root/Path(name.replace('.','/')+'.lean')
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):raise ValueError('MISSING_OR_UNSAFE_IMPORT:'+name)
        seen.add(name)
        for dep in shared.imports(p.read_text()):
            if dep.split('.')[0] in ['Scripts','L4YAML']:pending.append(dep)
            elif dep.split('.')[0] not in ['Lean','Std','Init','Lake']:raise ValueError('EXTERNAL_PROJECT_IMPORT:'+dep)
    return sorted(seen)

def lake_config(profile,modules):
    text='import Lake\nopen Lake DSL\npackage mathgraphCliParity where\n  leanOptions := #[⟨`autoImplicit, false⟩]\n'
    for prefix in ['Scripts','L4YAML']:
        roots=[m for m in modules if m.split('.')[0]==prefix]
        if roots:
            text+='lean_lib '+prefix+' where\n  srcDir := "/source"\n'
            if prefix=='L4YAML':text+='  precompileModules := true\n'
            text+='  roots := #['+', '.join('`'+m for m in roots)+']\n'
    text+='lean_exe cli where\n  srcDir := "/source"\n  root := `'+profile['head_module']+'\n  supportInterpreter := true\n'
    return text
