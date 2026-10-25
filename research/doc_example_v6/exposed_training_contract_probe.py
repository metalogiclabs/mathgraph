#!/usr/bin/env python3
"""Exposed Mistune TRAINING ONLY: documentation authority vs runtime behavior."""
import argparse, hashlib, json, sys, zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

SOURCE="d449488ce6baf5bcc386186cc01c40bf2afdc82c"
ZIP_SHA="85cc890df28cebd208ada6b1b6330391da739dc74aba9d5b3573f3125e1aa130"
JUNIT_SHA="ffd5485ae3a797e848d504cdd50d3db415db9d37dea46d4d9f6e81964fd8acfc"

class TagReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags=[]
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag.lower())

def script_found(text):
    p=TagReader()
    p.feed(text)
    p.close()
    return "script" in p.tags

def claims(text):
    s=" ".join(text.lower().split())
    return {
      "safe_raw_html": "create_markdown()"+chr(96)*2+" escapes raw html and rejects unsafe url schemes by default" in s,
      "legacy_unescaped_html": "mistune.html()" in s and "it does not escape html tags" in s,
    }

def native_authority(path):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==ZIP_SHA
    with zipfile.ZipFile(path) as z:
        raw=z.read("native-junit.xml")
        assert hashlib.sha256(raw).hexdigest()==JUNIT_SHA
        assert z.read("native-exit-code.txt").strip()==b"0"
        meta=json.loads(z.read("metadata.json"))
        assert meta["source_sha"]==SOURCE and meta["repository"]=="lepture/mistune"
        proposal=json.loads(z.read("proposals.json"))
        assert proposal["obligations"]==[]
    root=ET.fromstring(raw)
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    out={k:sum(int(t.attrib.get(k,"0")) for t in suites)
         for k in ("tests","failures","errors","skipped")}
    assert out=={"tests":1183,"failures":0,"errors":0,"skipped":0}
    return out

def main():
    p=argparse.ArgumentParser()
    for s in ("source","native_zip","out"):
        p.add_argument("--"+s.replace("_","-"), type=Path, required=True)
    a=p.parse_args()
    native=native_authority(a.native_zip)
    root=a.source.resolve()
    docfile=root/"docs/guide.rst"
    original=docfile.read_bytes()
    doc=original.decode("utf-8")
    sys.path.insert(0,str(root/"src"))
    sys.path.insert(0,str(root))
    import mistune
    assert Path(mistune.__file__).resolve().is_relative_to(root)
    adversary="<script>alert(1)</script>"
    safe=mistune.create_markdown()(adversary)
    legacy=mistune.html(adversary)
    assert script_found(adversary) and not script_found("&lt;script&gt;alert(1)&lt;/script&gt;")
    assert not script_found(safe),safe
    assert script_found(legacy),legacy
    marker=chr(96)*2
    old_safe=marker+"create_markdown()"+marker+" escapes raw HTML and rejects unsafe URL schemes by\ndefault."
    old_legacy="* It does not escape HTML tags."
    assert doc.count(old_safe)==1 and doc.count(old_legacy)==1
    def observe(label, text):
        docfile.write_text(text,encoding="utf-8")
        c=claims(text)
        assert not script_found(mistune.create_markdown()(adversary))
        assert script_found(mistune.html(adversary))
        return {"stage":label,"doc_sha256":hashlib.sha256(text.encode()).hexdigest(),
                "declared":c,
                "warrants":{k:("WARRANTED_BOUNDED_DOC_ATTRIBUTION" if v else "UNKNOWN_WITHDRAWN")
                            for k,v in c.items()}}
    try:
        base=observe("BASE",doc)
        assert all(base["declared"].values()),base
        withdraw_safe=observe("WITHDRAW_SAFE",doc.replace(old_safe,"The parser factory remains available."))
        assert withdraw_safe["declared"]=={"safe_raw_html":False,"legacy_unescaped_html":True}
        withdraw_legacy=observe("WITHDRAW_LEGACY",doc.replace(old_legacy,"* The helper remains available."))
        assert withdraw_legacy["declared"]=={"safe_raw_html":True,"legacy_unescaped_html":False}
        restored=observe("RESTORED",doc)
        assert restored["doc_sha256"]==base["doc_sha256"]
        assert restored["warrants"]==base["warrants"]
    finally:
        docfile.write_bytes(original)
    assert docfile.read_bytes()==original
    result={"status":"WARRANTED_BOUNDED_EXPOSED_TRAINING_DOC_AUTHORITY_WITHDRAWAL",
            "source":"lepture/mistune@"+SOURCE,"doc":"docs/guide.rst",
            "original_native":native,"native_archive_sha256":ZIP_SHA,
            "source_observation":{"input":adversary,"safe_output":safe,"legacy_output":legacy,
                                  "safe_script_tag":False,"legacy_script_tag":True},
            "stages":[base,withdraw_safe,withdraw_legacy,restored],
            "bounds":"One raw-HTML input and HTMLParser only; NOT general sanitizer or URL-scheme proof",
            "source_exposed_training":True,
            "prospective_V6":"UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE",
            "autonomous_observer_type_acquired":False}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("EXPOSED_MISTUNE_DOC_AUTHORITY_WITHDRAWAL_PASS",
          json.dumps({"native":native,"base":base["declared"],
                      "minus_safe":withdraw_safe["declared"],
                      "minus_legacy":withdraw_legacy["declared"]},sort_keys=True))

if __name__=="__main__":
    main()
