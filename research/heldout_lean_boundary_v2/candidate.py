#!/usr/bin/env python3
"""Source-neutral theorem/lemma observer; frozen before source selection."""
import hashlib, pathlib, re
TERMS = re.compile(r"correct|sound|equiv|refin|preserv|complete|faithful",re.I)
DECL = re.compile(r"^\s*(?:(?:protected|noncomputable|unsafe|partial)\s+)*(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_'.]*)\b")
NAMESPACE = re.compile(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_.]*)\s*(?:--.*)?$")
END = re.compile(r"^\s*end(?:\s+[A-Za-z_][A-Za-z0-9_.]*)?\s*(?:--.*)?$")
def propose(root):
    choices=[]
    for file in sorted(root.rglob("*.lean")):
        rel=file.relative_to(root); parts=rel.parts
        if any(p.startswith(".") or p in ("build","target","node_modules","_build","out","generated") for p in parts): continue
        if len(parts)>12 or file.stat().st_size>300000:continue
        module=".".join(rel.with_suffix("").parts)
        text=file.read_text(encoding="utf-8",errors="replace")
        ns=[]
        lines=text.splitlines()
        for i,line in enumerate(lines):
            if m:=NAMESPACE.match(line): ns.append(m.group(1));continue
            if END.match(line) and ns:ns.pop();continue
            m=DECL.match(line)
            if not m or "private " in line or "local " in line:continue
            name=m.group(2)
            follow=" ".join(lines[i:min(i+10,len(lines))])[:1400]
            if ":=" not in follow:continue
            full=".".join(ns+[name])
            score=(3 if TERMS.search(name) else 0)+(2 if " ↔ " in follow or " = " in follow else 0)
            choices.append({"arm":"candidate","file":str(rel),"module":module,"name":full,
                "line":i+1,"source_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
                "score_prefrozen":score,"declaration":line.strip()[:250]})
    return sorted(choices,key=lambda r:(-r["score_prefrozen"],r["file"],r["line"],r["name"]))[:4]
