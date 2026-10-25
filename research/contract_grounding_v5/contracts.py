#!/usr/bin/env python3
"""Extract source-declared public function docstrings, never execute target functions.

Consumes the qualified and separately pinned V4 static export resolver.
Only top-level function docstrings of statically exported package names qualify.
"""
import argparse, ast, hashlib, importlib.util, json, pathlib


def load_resolver(path):
    spec=importlib.util.spec_from_file_location("frozen_v4_export_resolver",path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snapshot(source, resolver):
    source=pathlib.Path(source)
    view=resolver.scan(source)
    ret={"api":view,"contracts":[],"unknowns":[],"status":"UNKNOWN_API_EXPORT"}
    if view.get("status") != "STATIC_EXPORT_CLOSURE_BOUNDED":
        ret["unknowns"].append(view.get("status","UNKNOWN_API_EXPORT"))
        return ret
    package=source / pathlib.Path(view["relative_api_path"]).parent
    candidates=sorted(package.glob("*.py"))
    if len(candidates) > 30:
        ret["status"]="UNKNOWN_DOC_SCAN_BUDGET"
        return ret
    exports=set(view["exports"])
    found={}
    for file in candidates:
        raw=file.read_bytes()
        tree=ast.parse(raw,filename=str(file))
        for node in tree.body:
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                continue
            if node.name not in exports:
                continue
            doc=ast.get_docstring(node,clean=True)
            key=node.name
            if not doc:
                ret["unknowns"].append({"symbol":key,"reason":"NO_STATIC_FUNCTION_DOCSTRING"})
                continue
            found.setdefault(key,[]).append({
                "symbol":key,"relative_source_path":str(file.relative_to(source)),
                "source_sha256":hashlib.sha256(raw).hexdigest(),
                "doc_sha256":hashlib.sha256(doc.encode()).hexdigest(),
                "docstring":doc,"line":node.lineno,
            })
    for symbol, items in sorted(found.items()):
        if len(items)>1:
            ret["unknowns"].append({"symbol":symbol,"reason":"AMBIGUOUS_PUBLIC_FUNCTION_DOC"})
        else:
            ret["contracts"].append(items[0])
    missing=exports-set(found)
    ret["unknowns"].extend({"symbol":n,"reason":"NO_REACHABLE_STATIC_PUBLIC_FUNCTION_DOC"}
                           for n in sorted(missing) if n!="*")
    ret["status"]="PUBLIC_DOCSTRING_AUTHORITY_EXTRACTED" if ret["contracts"] else "UNKNOWN_NO_SOURCE_DECLARED_FUNCTION_DOC"
    return ret


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--resolver",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    view=snapshot(a.source,load_resolver(a.resolver))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(view,sort_keys=True,indent=2)+"\n")
    print("SOURCE_DECLARED_PUBLIC_CONTRACT_SNAPSHOT",view["status"],
          len(view["contracts"]),view["api"].get("exports",[])[:12])


if __name__=="__main__":
    main()
