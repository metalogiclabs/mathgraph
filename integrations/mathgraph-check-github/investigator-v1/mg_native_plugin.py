"""Trusted pytest observation plugin, mounted read-only outside the subject tree."""
import ast, json, os, sys
from pathlib import Path
import pytest
_cases={};_hits={}
_subject_hits={}
_audit_root=str(Path(os.environ.get('MG_AUDIT_DIR','/audit')).resolve())+os.sep
_subject_paths=frozenset(str(Path(p).resolve()) for p in json.loads(os.environ.get('MG_SUBJECT_FILES','[]')))
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    path=str(Path(item.path).resolve())
    if not path.startswith(_audit_root):
        yield;return
    tree=ast.parse(Path(path).read_text());lines={x.lineno for x in ast.walk(tree) if isinstance(x,ast.Assert)}
    seen=set();subject_seen=set();previous=sys.gettrace()
    def trace(frame,event,arg):
        if event=='line':
            filename=frame.f_code.co_filename
            if filename==path and frame.f_lineno in lines:seen.add(frame.f_lineno)
            if filename in _subject_paths:subject_seen.add((filename,frame.f_lineno))
        return trace
    sys.settrace(trace)
    try:yield
    finally:
        sys.settrace(previous);_hits[item.nodeid]=len(seen);_subject_hits[item.nodeid]=len(subject_seen)
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield;report=outcome.get_result()
    if report.when=='call' or report.failed or report.skipped:
        _cases[item.nodeid]={'id':item.nodeid,'status':report.outcome,'exception':call.excinfo.type.__name__ if call.excinfo else None,'assertions_reached':_hits.get(item.nodeid,0),'subject_lines_reached':_subject_hits.get(item.nodeid,0)}
def pytest_sessionfinish(session,exitstatus):
    Path(os.environ['MG_CASES_FILE']).write_text(json.dumps(list(_cases.values())))
