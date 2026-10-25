#!/usr/bin/env python3
"""Only synthetic source before freeze; validates claim authority, negatives and withdrawal."""
import argparse,hashlib,importlib.util,json,sys,tempfile
from pathlib import Path


def load(name,path):
    spec=importlib.util.spec_from_file_location("v5_preflight_"+name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--resolver",type=Path,required=True)
    a=parser.parse_args()
    here=Path(__file__).resolve().parent
    contracts=load("contracts",here/"contracts.py")
    propose=load("propose",here/"propose.py")
    evaluate=load("evaluate",here/"evaluate.py")
    resolver=contracts.load_resolver(a.resolver)
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);pkg=root/"demo";pkg.mkdir()
        (pkg/"__init__.py").write_text("from .core import *\n")
        original=(
            '__all__ = ["underscore", "dasherize", "camelize"]\n'
            'def underscore(text):\n'
            '    """Make an underscored, lowercase form from the expression in the string."""\n'
            '    return text.lower().replace(" ", "_")\n'
            'def dasherize(text):\n'
            '    """Replace underscores with dashes."""\n'
            '    return text.replace("_", "-")\n'
            'def camelize(text):\n'
            '    """Make a CamelCase form from the expression in the string."""\n'
            '    return text\n'
        )
        core=pkg/"core.py";core.write_text(original)
        meta={"repository":"synthetic/demo","source_sha":"a"*40}
        view=contracts.snapshot(root,resolver)
        assert view["status"]=="PUBLIC_DOCSTRING_AUTHORITY_EXTRACTED",view
        assert {i["symbol"] for i in view["contracts"]}=={"underscore","dasherize","camelize"}
        ca=propose.propose(view,meta,"candidate")
        ex=propose.propose(view,meta,"expert")
        assert [(x["symbol"],x["relation"]) for x in ca["claims"]]==[
            ("dasherize","underscore-elimination"),("underscore","lowercase-output")]
        assert {i["claim_id"] for i in ex["claims"]}=={i["claim_id"] for i in ca["claims"]}
        junit=root/"native.xml";junit.write_text('<testsuite tests="7" failures="0" errors="0" skipped="1"></testsuite>')
        sys.path.insert(0,str(root))
        import demo
        native=evaluate.native_tests(junit)
        good=evaluate.evaluate_arm(ca,demo,native,view)
        assert {x["verdict"] for x in good["results"]}=={"WARRANTED_BOUNDED_DOC_BOUND_REFERENCE"},good
        assert all(all(v["malformed_output_rejected"] for v in x["observations"]) for x in good["results"])
        changed=original.replace("Make an underscored, lowercase form from the expression in the string.",
                                  "Return an unspecified representation from this string.")
        core.write_text(changed)
        after=contracts.snapshot(root,resolver)
        withdrawn=propose.propose(after,meta,"candidate")
        assert {i["claim_id"] for i in withdrawn["claims"]}=={"dasherize::underscore-elimination"}
        assert view["api"]["api_sha256"] != after["api"]["api_sha256"]
        core.write_text(original)
        restored=contracts.snapshot(root,resolver)
        assert restored["api"]["api_sha256"]==view["api"]["api_sha256"]
        assert propose.propose(restored,meta,"candidate")["claims"]==ca["claims"]
        junit.write_text('<testsuite tests="7" failures="1" errors="0" skipped="0"></testsuite>')
        bad_native=evaluate.evaluate_arm(ca,demo,evaluate.native_tests(junit),view)
        assert {x["verdict"] for x in bad_native["results"]}=={"UNKNOWN_NATIVE_AUTHORITY"}
        docless=propose.propose({"status":"UNKNOWN_NO_SOURCE_DECLARED_FUNCTION_DOC","api":{"api_sha256":"a"},"contracts":[],"unknowns":[]},meta,"candidate")
        assert not docless["claims"] and docless["status"].startswith("UNKNOWN_")
        print("SOURCE_DOC_AUTHORITY_SYNTHETIC_PASS physical_authority_withdrawal_selective native_negative UNKNOWN")
if __name__=="__main__":
    main()
