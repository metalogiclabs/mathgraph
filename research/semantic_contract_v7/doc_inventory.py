#!/usr/bin/env python3
"""V7 source-neutral, non-executing public documentation and API evidence inventory.

No behavior/test inspection. Public docs + top-level public callable signatures only.
"""
import argparse, ast, hashlib, json, pathlib, re

FUNCTIONS=("markdown","render","to_html","convert")
MODES=("safe_mode","escape_html","escape")
MAX_MODULES=35
MAX_DOCS=30
MAX_BYTES=350_000

def digest(data):
    return hashlib.sha256(data).hexdigest()

def candidate_modules(root):
    root=pathlib.Path(root)
    paths=set(root.glob("*.py"))
    paths.update(root.glob("lib/*.py"))
    paths.update(root.glob("src/*.py"))
    paths.update(root.glob("*/__init__.py"))
    paths.update(root.glob("src/*/__init__.py"))
    paths={p for p in paths if not any(part in ("test","tests","docs","examples") for part in p.parts)}
    return sorted(paths,key=lambda p:str(p.relative_to(root)))[:MAX_MODULES]

def callable_signatures(root):
    root=pathlib.Path(root)
    output=[]
    for p in candidate_modules(root):
        data=p.read_bytes()
        if len(data)>MAX_BYTES:
            continue
        try:
            tree=ast.parse(data,filename=str(p))
        except (SyntaxError,UnicodeDecodeError):
            continue
        all_names=None
        for n in tree.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="__all__" for t in n.targets):
                if isinstance(n.value,(ast.Tuple,ast.List)):
                    all_names={v.value for v in n.value.elts if isinstance(v,ast.Constant) and isinstance(v.value,str)}
        for node in tree.body:
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) or node.name not in FUNCTIONS:
                continue
            if all_names is not None and node.name not in all_names:
                continue
            args=[v.arg for v in node.args.args]+[v.arg for v in node.args.kwonlyargs]
            modes=[x for x in MODES if x in args]
            if not modes:continue
            if p.name=="__init__.py":
                module=p.parent.name
            else:
                module=p.stem
            output.append({
                "symbol":node.name,"module":module,"path":str(p.relative_to(root)),
                "line":node.lineno,"file_sha256":digest(data),"accepted_modes":modes,
                "signature_arguments":args[:20],
            })
    return sorted(output,key=lambda x:(x["path"],x["symbol"]))

def public_docs(root):
    root=pathlib.Path(root)
    paths=set(root.glob("README*"))
    paths.update(root.glob("docs/*.md"))
    paths.update(root.glob("docs/*.rst"))
    paths.update(root.glob("docs/*/*.md"))
    paths.update(root.glob("docs/*/*.rst"))
    paths={p for p in paths if p.is_file() and p.suffix.lower() in (".md",".markdown",".rst",".txt","")}
    out=[]
    for p in sorted(paths,key=lambda x:str(x.relative_to(root)))[:MAX_DOCS]:
        data=p.read_bytes()
        if len(data)>MAX_BYTES:continue
        text=data.decode("utf-8","replace")
        paragraphs=re.split(r"\n\s*\n+",text)
        for index,para in enumerate(paragraphs):
            normalized=" ".join(para.split())
            if len(normalized)>1300 or len(normalized)<15:continue
            low=normalized.lower()
            if "html" not in low or "escape" not in low or not any(w in low for w in MODES):
                continue
            out.append({
                "source_path":str(p.relative_to(root)),
                "source_sha256":digest(data),"paragraph_index":index,
                "paragraph_sha256":digest(normalized.encode()),"text":normalized,
            })
    return out[:35]

def snapshot(root):
    return {"protocol":"DOCUMENTED_HTML_ESCAPING_V7",
            "api":callable_signatures(root),
            "public_doc_paragraphs":public_docs(root),
            "scope":"top-level author docs, public callable signature; NO target imports, behavior, tests",
            "inventory_status":"INVENTORIED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    ret=snapshot(a.source)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(ret,indent=2,sort_keys=True)+"\n")
    print("PRE_NATIVE_DOC_INVENTORY",len(ret["api"]),len(ret["public_doc_paragraphs"]))

if __name__=="__main__":
    main()
