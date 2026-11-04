"""Trusted pytest observation plugin, mounted read-only outside the subject tree."""
import ast, dis, json, os, sys
from pathlib import Path
import pytest
_cases={};_hits={}
_subject_hits={};_import_assertion_hits={}
_audit_root=str(Path(os.environ.get('MG_AUDIT_DIR','/audit')).resolve())+os.sep
_subject_paths=frozenset(str(Path(p).resolve()) for p in json.loads(os.environ.get('MG_SUBJECT_FILES','[]')))
def subject_import_assertions(tree):
    """Recognize direct assertions about exports of the exact reviewed file.

    Constants are often imported during pytest collection, before per-test
    execution tracing starts. This is bounded provenance, not semantic intent.
    """
    def reviewed(module):
        path=getattr(module,'__file__',None)
        return isinstance(path,str) and str(Path(path).resolve()) in _subject_paths
    names=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):
            module=sys.modules.get(node.module or '')
            for alias in node.names:
                if alias.name!='*' and (reviewed(module) or reviewed(getattr(module,alias.name,None))):
                    names.add(alias.asname or alias.name)
        elif isinstance(node,ast.Import):
            for alias in node.names:
                if reviewed(sys.modules.get(alias.name)):
                    names.add(alias.asname or alias.name.split('.')[0])
    return {node.lineno: {x.id for x in ast.walk(node.test)
            if isinstance(x,ast.Name) and x.id in names}
            for node in ast.walk(tree) if isinstance(node,ast.Assert)
            and any(isinstance(x,ast.Name) and x.id in names for x in ast.walk(node.test))}
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    path=str(Path(item.path).resolve())
    if not path.startswith(_audit_root):
        yield;return
    tree=ast.parse(Path(path).read_text());lines={x.lineno for x in ast.walk(tree) if isinstance(x,ast.Assert)}
    import_lines=subject_import_assertions(tree)
    seen=set();subject_seen=set();import_seen=set();opcode_map={};previous=sys.gettrace()
    def trace(frame,event,arg):
        filename=frame.f_code.co_filename
        if event=='call' and filename==path:
            frame.f_trace_opcodes=True
        if event=='opcode' and filename==path and frame.f_lineno in import_lines:
            instrs=opcode_map.get(frame.f_code)
            if instrs is None:
                instrs={i.offset:i for i in dis.get_instructions(frame.f_code)}
                opcode_map[frame.f_code]=instrs
            instr=instrs.get(frame.f_lasti)
            if (instr and instr.opname in {'LOAD_GLOBAL','LOAD_NAME','LOAD_FAST','LOAD_DEREF'}
                    and instr.argval in import_lines[frame.f_lineno]):
                import_seen.add(frame.f_lineno)
        if event=='line':
            if filename==path and frame.f_lineno in lines:
                seen.add(frame.f_lineno)
            if filename in _subject_paths:subject_seen.add((filename,frame.f_lineno))
        return trace
    sys.settrace(trace)
    try:yield
    finally:
        sys.settrace(previous);_hits[item.nodeid]=len(seen);_subject_hits[item.nodeid]=len(subject_seen);_import_assertion_hits[item.nodeid]=len(import_seen)
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield;report=outcome.get_result()
    if report.when=='call' or report.failed or report.skipped:
        _cases[item.nodeid]={'id':item.nodeid,'status':report.outcome,'exception':call.excinfo.type.__name__ if call.excinfo else None,'assertions_reached':_hits.get(item.nodeid,0),'subject_lines_reached':_subject_hits.get(item.nodeid,0),'subject_import_assertions_reached':_import_assertion_hits.get(item.nodeid,0)}
def pytest_sessionfinish(session,exitstatus):
    Path(os.environ['MG_CASES_FILE']).write_text(json.dumps(list(_cases.values())))
