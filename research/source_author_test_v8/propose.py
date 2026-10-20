#!/usr/bin/env python3
"""V8 frozen source-neutral ORIGINAL-AUTHOR native test-entrypoint proposal.

Read only public documentation/configuration, never run source while proposing.
Any unsupported command, ambiguous evidence, or unverifiable authority => UNKNOWN.
This is a human-frozen finite command grammar, not autonomous observation-language genesis.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, shlex

CANDIDATE_DOCS = (
    "test/README.md", "test/README.rst",
    "tests/README.md", "tests/README.rst",
    "CONTRIBUTING.md", "CONTRIBUTING.rst",
    "README.md", "README.rst",
)
RUN_PYTHON = {"python", "python3"}
MAX_DOC_BYTES = 100_000
EXECUTABLE_ARGS = {"-knownfailure", "-q", "-v", "--verbose", "-s", "--", "-known-failure"}
FORBIDDEN = re.compile(r"[;&|$><`]|\$\(|\b(?:sudo|rm|curl|wget|pip install)\b")

def resolve_command(line: str, source: pathlib.Path, doc_path: pathlib.Path):
    # Support only exact single Python test-script or unittest/pytest module invocations.
    cleaned = line.strip().strip("`").strip()
    cleaned = cleaned.lstrip("$ ").strip()
    if not cleaned or FORBIDDEN.search(cleaned):
        return None
    try:
        tokens = shlex.split(cleaned)
    except ValueError:
        return None
    if not tokens or tokens[0] not in RUN_PYTHON:
        return None
    if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] in ("pytest", "unittest"):
        # Generic native-runner command permitted when explicit in author docs.
        tail=tokens[3:]
        if any(t.startswith("-") and t not in ("-q","-v","-s","--verbose","discover") for t in tail):
            return None
        if any(not re.fullmatch(r"[a-zA-Z0-9_./-]+", t) for t in tail):
            return None
        return {"argv":[tokens[0],"-m",tokens[2],*tail],"cwd":".","runner":"module"}
    if len(tokens)<2:
        return None
    filename=tokens[1]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.py",filename):
        return None
    # Native author's test command should run in the doc directory if relative test.py exists.
    local=source / doc_path.parent / filename
    root=source / filename
    if local.is_file():
        base=doc_path.parent
    elif root.is_file():
        base=pathlib.Path(".")
    else:
        return None
    flags=tokens[2:]
    if any(t not in EXECUTABLE_ARGS for t in flags):
        return None
    return {"argv":[tokens[0],filename,*flags],"cwd":str(base),"runner":"script"}

def collect(source: pathlib.Path):
    source=pathlib.Path(source)
    evidence=[]
    for filename in CANDIDATE_DOCS:
        doc=source / filename
        if not doc.is_file() or doc.stat().st_size>MAX_DOC_BYTES:
            continue
        raw=doc.read_bytes()
        try: text=raw.decode("utf-8")
        except UnicodeDecodeError: continue
        lines=text.splitlines()
        for idx,line in enumerate(lines):
            cmd=resolve_command(line,source,pathlib.Path(filename))
            if not cmd:
                continue
            # The line must occur in a native-test context, not merely code examples.
            vicinity=" ".join(lines[max(0,idx-8):idx+1]).lower()
            if not any(tag in vicinity for tag in ("test", "suite", "harness", "run ", "running")):
                continue
            if any(x in vicinity[-130:] for x in ("do not run", "don't run", "not recommended", "deprecated command")):
                continue
            evidence.append({
                "source_doc":filename,"line":idx+1,"exact_line":line.strip(),
                "doc_sha256":hashlib.sha256(raw).hexdigest(),
                "command":cmd,
            })
    # Preserve conflicting observed commands and abstain rather than choose by outcomes.
    unique={(tuple(e["command"]["argv"]),e["command"]["cwd"]) for e in evidence}
    status=("UNKNOWN_NO_SOURCE_DECLARED_RUNNER" if not evidence else
            "UNKNOWN_AMBIGUOUS_AUTHOR_RUNNER" if len(unique)!=1 else
            "CANDIDATE_AUTHOR_DECLARED_RUNNER")
    return {"status":status,"evidence":evidence,
            "selected": evidence[0] if status=="CANDIDATE_AUTHOR_DECLARED_RUNNER" else None}

def expert_reference(source: pathlib.Path):
    """Independently coded conventional same-information cookbook.

    It inspects the same allowed docs and proposes the same declared command if
    exactly one command survives. Not a recruited human expert.
    """
    source=pathlib.Path(source)
    matches=[]
    for filename in CANDIDATE_DOCS:
        doc=source/filename
        if not doc.exists() or doc.stat().st_size>MAX_DOC_BYTES:
            continue
        try: raw=doc.read_text(encoding="utf8")
        except UnicodeDecodeError: continue
        for linenum,line in enumerate(raw.splitlines(),start=1):
            if not re.match(r"\s*(?:\$\s*)?python(?:3)?\s+(?:[\w.-]+\.py|\-m\s+(?:pytest|unittest))\b",line):
                continue
            if not any(t in raw.lower() for t in ("test","suite","harness")): continue
            command=resolve_command(line,source,pathlib.Path(filename))
            if command:
                matches.append((linenum,filename,command))
    choices={(tuple(c["argv"]),c["cwd"]) for _,_,c in matches}
    if len(choices)!=1:
        return {"status":"UNKNOWN_NO_UNAMBIGUOUS_DECLARED_RUNNER","selected":None,"count":len(matches)}
    first=next((n,p,c) for n,p,c in matches if (tuple(c["argv"]),c["cwd"]) in choices)
    return {"status":"CANDIDATE_AUTHOR_DECLARED_RUNNER",
            "selected":{"source_doc":first[1],"line":first[0],"command":first[2]},
            "count":len(matches)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--metadata",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    meta=json.loads(a.metadata.read_text())
    assert re.fullmatch(r"[a-f0-9]{40}",meta["source_sha"])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps({"protocol":"AUTHOR_RUNNER_AUTHORITY_V8",
      "source":meta,"candidate":collect(a.source),"expert":expert_reference(a.source),
      "api":"public author docs only; no production/test files read to derive policy",
      "limits":"finite safe Python-only command grammar; no automatic learning or human review"},indent=2,sort_keys=True)+"\n")
    print("V8_PRE_NATIVE_AUTHOR_RUNNER_PROPOSALS_SEALED",
          collect(a.source)["status"],expert_reference(a.source)["status"])

if __name__=="__main__":
    main()
