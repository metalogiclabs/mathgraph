#!/usr/bin/env python3
"""V6 static, bounded public class-method and function doc example obligation miner.

The source implementation is parsed but never executed prior to proposal seal.
Only literal argument calls and literal expected-result examples are admitted.
"""
import argparse,ast,doctest,hashlib,importlib.util,json,pathlib


def load_export(path):
    spec=importlib.util.spec_from_file_location("v4_frozen_static_exports",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_value(node):
    value=ast.literal_eval(node)
    if value is None or isinstance(value,(str,int,float,bool)):
        return value
    if isinstance(value,(list,tuple)) and all(isinstance(x,(str,int,float,bool,type(None))) for x in value):
        return list(value)
    raise ValueError("UNSUPPORTED_LITERAL")


def eligible_example(source,expected_text,cls,method,aliases):
    try:
        value=safe_value(ast.parse(expected_text.strip(),mode="eval").body)
        tree=ast.parse(source,mode="exec")
        if len(tree.body)!=1 or not isinstance(tree.body[0],ast.Expr):
            return None
        call=tree.body[0].value
        if not isinstance(call,ast.Call):
            return None
        if cls is None:
            if not isinstance(call.func,ast.Name) or call.func.id!=method:
                return None
        else:
            fn=call.func
            if not isinstance(fn,ast.Attribute) or fn.attr!=method:
                return None
            target=fn.value
            if isinstance(target,ast.Name):
                if aliases.get(target.id)!=cls:
                    return None
            elif isinstance(target,ast.Call):
                if not isinstance(target.func,ast.Name) or target.func.id!=cls or target.args or target.keywords:
                    return None
            else:
                return None
        args=[safe_value(a) for a in call.args]
        kwargs={k.arg:safe_value(k.value) for k in call.keywords if k.arg is not None}
        if len(kwargs)!=len(call.keywords) or len(args)>5 or len(kwargs)>5:
            return None
        return {"args":args,"kwargs":kwargs,"expected":value,"source_example":source.strip(),"wanted_repr":expected_text.strip()}
    except (SyntaxError,ValueError,TypeError,RecursionError):
        return None


def mine_examples(doc,cls,method):
    # Do not attempt arbitrary doc code or setup variables. Class().method(...) only.
    parser=doctest.DocTestParser()
    try:
        examples=parser.get_examples(doc)
    except ValueError:
        return []
    found=[]
    aliases={}
    for ex in examples[:25]:
        # Recognize only a literal no-argument constructor alias as doc setup.
        # We do not run that setup while proposing obligations.
        try:
            node=ast.parse(ex.source,mode="exec")
            if cls is not None and len(node.body)==1 and isinstance(node.body[0],ast.Assign):
                assignment=node.body[0]
                if (len(assignment.targets)==1 and isinstance(assignment.targets[0],ast.Name)
                    and isinstance(assignment.value,ast.Call) and isinstance(assignment.value.func,ast.Name)
                    and assignment.value.func.id==cls and not assignment.value.args and not assignment.value.keywords
                    and not ex.want.strip()):
                    aliases[assignment.targets[0].id]=cls
                    continue
        except SyntaxError:
            continue
        e=eligible_example(ex.source,ex.want,cls,method,aliases)
        if e is not None:
            found.append(e)
    return found


def scan(source,resolver):
    source=pathlib.Path(source)
    view=resolver.scan(source)
    result={"status":"UNKNOWN_NO_API","api":view,"obligations":[],"unknowns":[],"files":{}}
    if view.get("status")!="STATIC_EXPORT_CLOSURE_BOUNDED":
        result["unknowns"].append(view.get("status"))
        return result
    package=source/pathlib.Path(view["relative_api_path"]).parent
    files=sorted(package.glob("*.py"))
    if len(files)>30:
        result["status"]="UNKNOWN_SCAN_BUDGET"
        return result
    exports=set(view["exports"])
    for file in files:
        raw=file.read_bytes()
        rel=str(file.relative_to(source))
        digest=hashlib.sha256(raw).hexdigest()
        result["files"][rel]=digest
        tree=ast.parse(raw,filename=rel)
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in exports:
                entries=[(None,node.name,ast.get_docstring(node,clean=True),node.lineno)]
            elif isinstance(node,ast.ClassDef) and node.name in exports:
                entries=[(node.name,m.name,ast.get_docstring(m,clean=True),m.lineno)
                         for m in node.body if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef))
                         and not m.name.startswith("_")]
            else:
                continue
            for cls,name,doc,line in entries:
                if not doc:
                    continue
                for example in mine_examples(doc,cls,name):
                    result["obligations"].append({
                        "class":cls,"method":name,"source_path":rel,"source_file_sha256":digest,
                        "doc_sha256":hashlib.sha256(doc.encode()).hexdigest(),
                        "source_line":line,
                        "relation":"actual_literal_result == exact_literal_doc_example",
                        **example
                    })
    result["obligations"]=sorted(result["obligations"],key=lambda x:(x["source_path"],x["class"] or "",x["method"],x["source_example"]))[:40]
    result["status"]="SOURCE_DOC_EXAMPLE_CANDIDATES" if result["obligations"] else "UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE"
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--resolver",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    data=scan(a.source,load_export(a.resolver))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("DOCUMENTED_METHOD_EXAMPLE_PROPOSALS_PRE_NATIVE",data["status"],len(data["obligations"]),
          [(x["class"],x["method"]) for x in data["obligations"][:8]])


if __name__=="__main__":
    main()
