"""Trusted pytest observation plugin, mounted read-only outside the subject tree."""
import ast, dis, json, os, sys
from pathlib import Path
import pytest
_cases={};_hits={}
_subject_hits={};_import_assertion_hits={}
_audit_root=str(Path(os.environ.get('MG_AUDIT_DIR','/audit')).resolve())+os.sep
_subject_paths=frozenset(str(Path(p).resolve()) for p in json.loads(os.environ.get('MG_SUBJECT_FILES','[]')))
def pytest_sessionstart(session):
    # On CPython 3.12 the first traced frame cannot yet emit opcode events.
    # Prime bytecode instrumentation with trusted code before the first probe.
    previous=sys.gettrace()
    def warm_trace(frame,event,arg):
        if event=='call':frame.f_trace_opcodes=True
        return warm_trace
    def warm():return 2+2
    sys.settrace(warm_trace)
    try:warm()
    finally:sys.settrace(previous)
def subject_import_assertions(tree):
    """Recognize direct assertions about exports of the exact reviewed file.

    Constants are often imported during pytest collection, before per-test
    execution tracing starts. This is bounded provenance, not semantic intent.
    """
    def reviewed(module):
        path=getattr(module,'__file__',None)
        return isinstance(path,str) and str(Path(path).resolve()) in _subject_paths
    bound={}
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):
            module=sys.modules.get(node.module or '')
            for alias in node.names:
                value=vars(module).get(alias.name) if module is not None else None
                if alias.name!='*' and module is not None and alias.name in vars(module) and (reviewed(module) or reviewed(value)):
                    bound[alias.asname or alias.name]=value
        elif isinstance(node,ast.Import):
            for alias in node.names:
                module=sys.modules.get(alias.name)
                if reviewed(module):
                    bound[alias.asname or alias.name.split('.')[0]]=module
    return {node.lineno: {x.id:bound[x.id] for x in ast.walk(node.test)
            if isinstance(x,ast.Name) and x.id in bound}
            for node in ast.walk(tree) if isinstance(node,ast.Assert)
            and any(isinstance(x,ast.Name) and x.id in bound for x in ast.walk(node.test))}
def bound_value(frame,instr):
    """Resolve the value *actually* read by an opcode, not a shadowed name."""
    name=instr.argval
    if instr.opname in {'LOAD_FAST','LOAD_DEREF'}:return frame.f_locals.get(name,_unbound)
    if instr.opname=='LOAD_NAME':return frame.f_locals.get(name,frame.f_globals.get(name,_unbound))
    return frame.f_globals.get(name,_unbound)
_unbound=object()
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
                    and instr.argval in import_lines[frame.f_lineno]
                    and bound_value(frame,instr) is import_lines[frame.f_lineno][instr.argval]):
                import_seen.add(frame.f_lineno)
        if event=='line':
            if filename==path and frame.f_lineno in lines:
                seen.add(frame.f_lineno)
            if filename in _subject_paths:subject_seen.add((filename,frame.f_lineno))
        return trace
    sys.settrace(trace)
    try:yield
    finally:
        sys.settrace(previous)
        _hits[item.nodeid]=len(seen);_subject_hits[item.nodeid]=len(subject_seen);_import_assertion_hits[item.nodeid]=len(import_seen)
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield;report=outcome.get_result()
    if report.when=='call' or report.failed or report.skipped:
        # Lookup failures inside a reached assertion are materially different
        # from fixture/import crashes. Record exact traceback provenance so
        # the trusted assessor can keep that boundary narrow.
        in_assertion=False
        if call.excinfo and call.excinfo.traceback and _hits.get(item.nodeid,0)>0:
            last=call.excinfo.traceback[-1]
            path=str(Path(item.path).resolve())
            if str(Path(str(last.path)).resolve())==path:
                try:
                    lines={n.lineno for n in ast.walk(ast.parse(Path(path).read_text())) if isinstance(n,ast.Assert)}
                    in_assertion=(last.lineno+1) in lines
                except (OSError,SyntaxError):pass
        _cases[item.nodeid]={'id':item.nodeid,'status':report.outcome,'exception':call.excinfo.type.__name__ if call.excinfo else None,'exception_in_assertion':in_assertion,'assertions_reached':_hits.get(item.nodeid,0),'subject_lines_reached':_subject_hits.get(item.nodeid,0),'subject_import_assertions_reached':_import_assertion_hits.get(item.nodeid,0)}
def pytest_sessionfinish(session,exitstatus):
    Path(os.environ['MG_CASES_FILE']).write_text(json.dumps(list(_cases.values())))
