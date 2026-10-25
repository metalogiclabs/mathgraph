#!/usr/bin/env python3
"""V9 frozen structured pytest-scope authority miner. Source-independent, read-only.

Reads bounded pyproject.toml / pytest.ini / setup.cfg and Makefile.
Never executes build recipes, imports target source, or treats pytest success as author completeness.
"""
import argparse,configparser,hashlib,json,pathlib,re,shlex,tomllib

MAX_BYTES=160_000
CONFIGS=("pyproject.toml","pytest.ini","setup.cfg","Makefile")
PATTERN=re.compile(r"^[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*$")
TEST_TARGET=re.compile(r"^(?:test|tests|check):(?:\s+[^#]*)?$")


def safe_paths(value, root):
    if isinstance(value,str):
        try: parts=shlex.split(value)
        except ValueError: return None
    elif isinstance(value,list) and all(isinstance(x,str) for x in value):
        parts=value
    else: return None
    if not parts or len(parts)>12: return None
    cleaned=[]
    for item in parts:
        if not PATTERN.fullmatch(item):return None
        path=(root/item).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_dir():return None
        if item not in cleaned: cleaned.append(item)
    return cleaned


def make_test_signal(data):
    lines=data.splitlines()
    for i,line in enumerate(lines):
        if not TEST_TARGET.match(line.strip()) or line.startswith((" ","\t")):
            continue
        recipe=[]
        for entry in lines[i+1:i+15]:
            if entry.startswith("\t"):
                recipe.append(entry.strip().lstrip("@-"))
            elif not entry.strip() or entry.lstrip().startswith("#"):
                continue
            else:break
        # Structural evidence of a test target, not authorization to execute arbitrary shell.
        if any(re.search(r"(?:^|[\s/])pytest(?:\s|$)",r) or re.search(r"python(?:3)?\s+-m\s+pytest(?:\s|$)",r) for r in recipe):
            return {"signal":"MAKEFILE_TEST_TARGET_POINTS_TO_PYTEST","target":"test","recipe_lines":len(recipe)}
    return None


def scan(root):
    root=pathlib.Path(root).resolve()
    evidence={}
    claims=[]
    unknown=[]
    make=None
    for filename in CONFIGS:
        path=root/filename
        if not path.is_file():continue
        if not path.resolve().is_relative_to(root) or path.stat().st_size>MAX_BYTES:
            unknown.append(filename+":unsafe_or_large");continue
        data=path.read_bytes()
        evidence[filename]=hashlib.sha256(data).hexdigest()
        try:s=data.decode("utf-8")
        except UnicodeDecodeError:
            unknown.append(filename+":not_utf8");continue
        if filename=="Makefile":
            make=make_test_signal(s)
            continue
        try:
            if filename=="pyproject.toml":
                obj=tomllib.loads(s)
                config=obj.get("tool",{}).get("pytest",{}).get("ini_options",{})
            else:
                parser=configparser.ConfigParser(interpolation=None,strict=True)
                parser.read_string(s)
                section="pytest" if filename=="pytest.ini" else "tool:pytest"
                config=dict(parser[section]) if parser.has_section(section) else {}
            if "testpaths" in config:
                roots=safe_paths(config["testpaths"],root)
                if roots is None:
                    unknown.append(filename+":invalid_testpaths")
                else:
                    claims.append({"authority_file":filename,"authority_sha256":evidence[filename],
                                   "testpaths":roots,"kind":"SOURCE_CONFIGURED_PYTEST_ROOTS"})
        except (tomllib.TOMLDecodeError,configparser.Error,ValueError,TypeError) as exc:
            unknown.append(filename+":parse_error:"+type(exc).__name__)
    unique={tuple(c["testpaths"]) for c in claims}
    if len(unique)>1:
        status="UNKNOWN_CONFLICTING_PYTEST_ROOTS"
        chosen=None
    elif len(unique)==1:
        status="CANDIDATE_SOURCE_CONFIGURED_PYTEST_ROOTS"
        chosen=sorted(claims,key=lambda c:CONFIGS.index(c["authority_file"]))[0]
    elif make:
        status="CANDIDATE_AUTHOR_MAKE_PYTEST_NO_ROOT_AUTHORITY"
        chosen=None
    else:
        status="UNKNOWN_NO_STRUCTURED_AUTHOR_PYTEST_ROOTS"
        chosen=None
    return {"protocol":"STRUCTURED_PYTEST_SCOPE_V9","status":status,
            "selected":chosen,"claims":claims,"make_signal":make,
            "evidence_files":evidence,"unknowns":unknown,
            "boundary":"Source-declared pytest config roots, NOT full author's native test suite"}


def cookbook(root):
    """Separate conventional expert rulebook; same source/config access, not a human reviewer."""
    root=pathlib.Path(root)
    sources={}
    for name in CONFIGS:
        p=root/name
        if p.exists() and p.is_file() and p.stat().st_size<=MAX_BYTES:
            sources[name]=p.read_bytes()
    findings=[]
    if "pyproject.toml" in sources:
        try:
            cfg=tomllib.loads(sources["pyproject.toml"].decode("utf8"))["tool"]["pytest"]["ini_options"]
            if "testpaths" in cfg:
                x=safe_paths(cfg["testpaths"],root)
                if x is not None:findings.append(("pyproject.toml",x))
        except (KeyError,TypeError,ValueError,tomllib.TOMLDecodeError):pass
    for filename,section in (("pytest.ini","pytest"),("setup.cfg","tool:pytest")):
        if filename not in sources:continue
        try:
            cp=configparser.RawConfigParser()
            cp.read_string(sources[filename].decode("utf8"))
            if cp.has_option(section,"testpaths"):
                x=safe_paths(cp.get(section,"testpaths"),root)
                if x is not None:findings.append((filename,x))
        except (configparser.Error,UnicodeDecodeError,ValueError):pass
    choices={tuple(paths) for _,paths in findings}
    if len(choices)==1:
        which,paths=sorted(findings,key=lambda x:CONFIGS.index(x[0]))[0]
        return {"status":"EXPERT_RULE_SELECTED_STRUCTURED_ROOTS",
                "selected":{"authority_file":which,
                            "authority_sha256":hashlib.sha256(sources[which]).hexdigest(),
                            "testpaths":paths}}
    if len(choices)>1:return {"status":"UNKNOWN_EXPERT_CONFIG_CONFLICT","selected":None}
    return {"status":"UNKNOWN_EXPERT_NO_CONFIGURED_ROOTS","selected":None}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--metadata",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    meta=json.loads(a.metadata.read_text())
    assert re.fullmatch("[0-9a-f]{40}",meta["source_sha"])
    result={"source":meta,"candidate":scan(a.source),"expert_rule":cookbook(a.source)}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("PRE_NATIVE_STRUCTURED_AUTHORITY",result["candidate"]["status"],
          result["expert_rule"]["status"])


if __name__=="__main__":
    main()
