#!/usr/bin/env python3
"""Independently authored all-information expert-rule comparator PROXY."""
import os, re, hashlib
def propose(root):
    records=[]
    for directory,_,names in os.walk(root):
        segs=os.path.relpath(directory,root).split(os.sep)
        if any(p.startswith(".") or p in ("target","build","node_modules","_build","out","generated") for p in segs):continue
        for filename in sorted(names):
            if not filename.endswith(".lean"):continue
            file=__import__("pathlib").Path(directory)/filename
            if file.stat().st_size>300000:continue
            rel=file.relative_to(root);module=".".join(rel.with_suffix("").parts)
            raw=file.read_bytes(); text=raw.decode("utf-8","replace")
            segments=[]; scope=[]
            for pos,line in enumerate(text.splitlines(),1):
                clean=line.strip()
                if clean.startswith("namespace "):
                    scope.append(clean.split()[1]);continue
                if (clean=="end" or clean.startswith("end ")) and scope:
                    scope.pop();continue
                match=re.match(r"^(theorem|lemma)\s+([A-Za-z_][\w.']*)\b",clean)
                if match:
                    name=".".join(scope+[match.group(2)])
                    # Rules independently favor simple, source-declared top-level proofs.
                    measure=(1 if "proof" in str(rel).lower() else 0)+(1 if "theorem"==match.group(1) else 0)
                    records.append({"arm":"baseline","file":str(rel),"module":module,
                      "name":name,"line":pos,"source_sha256":hashlib.sha256(raw).hexdigest(),
                      "score_prefrozen":measure,"declaration":clean[:250]})
    records.sort(key=lambda x:(-x["score_prefrozen"],x["file"],x["line"],x["name"]))
    return records[:4]
