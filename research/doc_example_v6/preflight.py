#!/usr/bin/env python3
"""Only synthetic inputs plus EXPOSED V5 training before future selection."""
import argparse,importlib,importlib.util,sys,tempfile
from pathlib import Path


def load(name,path):
    spec=importlib.util.spec_from_file_location("synthetic_"+name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--resolver",type=Path,required=True)
    p.add_argument("--training",type=Path,required=True)
    a=p.parse_args()
    here=Path(__file__).resolve().parent
    prop=load("propose",here/"propose.py")
    ev=load("evaluate",here/"evaluate.py")
    resolver=prop.load_export(a.resolver)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);pkg=root/"demo";pkg.mkdir()
        original=(
            '__all__ = ["Demo"]\n'
            'class Demo:\n'
            '    def lower(self,text):\n'
            '        """Return lowered text.\n\n'
            '        >>> Demo().lower("ABC")\n'
            "        'abc'\n"
            '        """\n'
            '        return text.lower()\n'
            '    def upper(self,text):\n'
            '        """Return upper text.\n\n'
            '        >>> obj = Demo()\n'
            '        >>> obj.upper("abc")\n'
            "        'ABC'\n"
            '        """\n'
            '        return text.upper()\n'
        )
        file=pkg/"__init__.py";file.write_text(original)
        view=prop.scan(root,resolver)
        assert view["status"]=="SOURCE_DOC_EXAMPLE_CANDIDATES",view
        assert len(view["obligations"])==2,view
        assert {q["method"] for q in view["obligations"]}=={"lower","upper"}
        sys.path.insert(0,str(root))
        module=importlib.import_module("demo")
        native={"admitted":True,"tests":2,"failures":0,"errors":0,"skipped":0}
        rows=ev.judge(view,module,native,root)
        assert {x["verdict"] for x in rows}=={"WARRANTED_BOUNDED_SOURCE_DOC_EXAMPLE"},rows
        file.write_text(original.replace("'abc'","'not-abc'"))
        changed=prop.scan(root,resolver)
        assert changed["api"]["api_sha256"]!=view["api"]["api_sha256"]
        assert changed["obligations"][0]["expected"]!=view["obligations"][0]["expected"]
        file.write_text(original)
        restored=prop.scan(root,resolver)
        assert restored["api"]["api_sha256"]==view["api"]["api_sha256"]
        assert restored["obligations"]==view["obligations"]
        denied=ev.judge(view,module,{"admitted":False},root)
        assert all(x["verdict"]=="UNKNOWN_NO_NATIVE_AUTHORITY" for x in denied)
    training=prop.scan(a.training,resolver)
    assert training["api"]["status"]=="STATIC_EXPORT_CLOSURE_BOUNDED"
    assert any(q["class"]=="engine" for q in training["obligations"]),training
    print("V6_PREEXPOSURE_SYNTHETIC_PASS; EXPOSED_JARACO_CLASS_DOC_OBSERVATION",
          len(training["obligations"]))
if __name__=="__main__":
    main()
