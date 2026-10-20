#!/usr/bin/env python3
"""Synthetic source, doc-withdrawal and exposed Mistune proposal tests only."""
import importlib.util,json,sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
def load(label,path):
 spec=importlib.util.spec_from_file_location("preflight_"+label,path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
here=Path(__file__).resolve().parent
candidate=load("candidate",here/"propose.py")
expert=load("expert",here/"baseline.py")
audit=load("audit",here/"evaluate.py")
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);pkg=root/"docmark";pkg.mkdir()
 (pkg/"__init__.py").write_text('import html\ndef create_renderer():\n    return lambda text: html.escape(text)\ndef html(text):\n    return text\n')
 doc=root/"README.rst"
 original='''Source documentation
====================

Create a renderer to escape raw HTML::

    import docmark
    renderer = docmark.create_renderer()
    renderer(YOUR_MARKDOWN_TEXT)

create_renderer() escapes raw HTML by default.

Legacy renderer
---------------
The docmark.html() compatibility helper provides older behavior:

* It does not escape HTML tags.
'''
 doc.write_text(original)
 a=candidate.discover(root);b=expert.assess(root)
 assert len(a["claims"])==2,(a["claims"],a["unknowns"])
 assert len(b["claims"])==2,b
 assert {(x["function"],x["mode"]) for x in a["claims"]}=={("create_renderer","escape"),("html","raw")}
 assert any(x["factory"] for x in a["claims"] if x["mode"]=="escape")
 junit=root/"native.xml"
 junit.write_text('<testsuite tests="5" failures="0" errors="0" skipped="0"></testsuite>')
 sys.path.insert(0,str(root))
 observed=audit.judge(None,root,a,b,junit,{"repository":"synthetic/docmark","source_sha":"a"*40})
 assert observed["comparison"]["verdict"]=="AUTHORED_RULE_TIE",observed
 assert observed["arms"]["candidate"]["warrants"]==2,observed
 doc.write_text(original.replace("create_renderer() escapes raw HTML by default.","create_renderer() has undocumented behavior."))
 changed=candidate.discover(root)
 assert len(changed["claims"])==1 and changed["claims"][0]["mode"]=="raw",changed
 doc.write_text(original)
 restored=candidate.discover(root)
 assert restored["claims"]==a["claims"] and restored["files"]==a["files"]
 junit.write_text('<testsuite tests="5" failures="1" errors="0" skipped="0"></testsuite>')
 denied=audit.judge(None,root,a,b,junit,{"repository":"synthetic/docmark","source_sha":"a"*40})
 assert denied["arms"]["candidate"]["warrants"]==0
 assert all(x["status"]=="UNKNOWN_NATIVE_SUITE" for x in denied["arms"]["candidate"]["rows"])
 assert not audit.parsed_script("hello &lt;script&gt;alert(1)&lt;/script&gt;")
 assert audit.parsed_script("<script>alert(1)</script>")
print("SYNTHETIC_HTML_DOC_AUTHORITY_PRE_FREEZE_GREEN")
