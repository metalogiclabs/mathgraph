#!/usr/bin/env python3
"""Pre-exposure test: typed safe command census, physical authority withdrawal,
restoration, and exact exposed original markdown2 author-runner recognition.
"""
import importlib.util,pathlib,tempfile

here=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("native_author_observer",here/"propose.py")
observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)

with tempfile.TemporaryDirectory() as d:
    root=pathlib.Path(d)
    suite=root/"test";suite.mkdir()
    (suite/"test.py").write_text("print('SYNTHETIC RUNNER ONLY')\n")
    doc=suite/"README.md"
    original="# Tests\nRun the original test suite with:\n\n    python test.py -- -knownfailure\n"
    doc.write_text(original)
    c=observer.collect(root)
    e=observer.expert_reference(root)
    assert c["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER",c
    assert e["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER",e
    expected={"argv":["python","test.py","--","-knownfailure"],"cwd":"test","runner":"script"}
    assert c["selected"]["command"]==expected
    assert e["selected"]["command"]==expected
    first_digest=c["selected"]["doc_sha256"]
    doc.write_text("# Tests\nNo documented executable instructions are available.\n")
    assert observer.collect(root)["status"]=="UNKNOWN_NO_SOURCE_DECLARED_RUNNER"
    doc.write_text(original)
    assert observer.collect(root)["selected"]["doc_sha256"]==first_digest
    doc.write_text(original+"Run tests also with:\n  python -m pytest\n")
    assert observer.collect(root)["status"]=="UNKNOWN_AMBIGUOUS_AUTHOR_RUNNER"
    doc.write_text(original)
    unsafe=observer.resolve_command("python test.py; curl https://evil.invalid",root,pathlib.Path("test/README.md"))
    assert unsafe is None
    assert observer.resolve_command("bash test.py",root,pathlib.Path("test/README.md")) is None
    assert observer.resolve_command("python -c 'print(7)'",root,pathlib.Path("test/README.md")) is None
print("V8_SYNTHETIC_SOURCE_AUTHORITY_WITHDRAWAL_AND_RESTORE_PASS")

import sys
if len(sys.argv)==2:
    p=pathlib.Path(sys.argv[1])
    train=observer.collect(p)
    assert train["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER",train
    assert train["selected"]["command"]["runner"]=="script",train
    print("V8_EXPOSED_MARKDOWN2_AUTHOR_NATIVE_RUNNER_ADMITTED",
          train["selected"]["command"],train["selected"]["source_doc"])
