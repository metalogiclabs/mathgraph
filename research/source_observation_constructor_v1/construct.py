#!/usr/bin/env python3
"""Source-blind typed test-observer constructor, V1.
Creates a bounded new operation INSTANCE from source-authored declarations.
Its finite parser and operation grammar are human-written, not autonomous G2.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import shlex

ROOT = pathlib.Path(__file__).resolve().parents[1]
V9 = ROOT / "structured_test_authority_v9" / "scan.py"
DOCS = ("test/README.md", "test/README.rst", "tests/README.md",
        "tests/README.rst", "README.md", "README.rst",
        "CONTRIBUTING.md", "CONTRIBUTING.rst")
MAX_BYTES = 160000
DOC_COMMAND = re.compile(r"(?:^|\s)(?:python3?|pytest)(?:\s+|$)", re.I)
TEST_CONTEXT = re.compile(r"\b(?:to\s+run\s+(?:the\s+)?(?:tests?|test\s+suite)|run\s+(?:the\s+)?(?:tests?|test\s+suite))\b", re.I)
NEGATED_AUTHORITY = re.compile(r"\b(?:do\s+not|don't|never|not\s+supported|no\s+longer|deprecated|example\s+only|unsafe|incorrect)\b", re.I)
SAFE_ARG = re.compile(r"^[A-Za-z0-9_./:=+-]+$")
BAD = set(";&|$<>{}*?\\")
FAMILY_ORDER = {"AUTHOR_DRIVER": 0, "PYTEST_ROOTS": 1, "AUTHOR_PYTEST": 2}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def v9_scan(root):
    spec = importlib.util.spec_from_file_location("source_auth_v9", V9)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.scan(root)

def safe_doc(root, rel):
    p = root / rel
    if not p.is_file() or p.is_symlink():
        return None
    if p.stat().st_size > MAX_BYTES or not p.resolve().is_relative_to(root):
        return None
    data = p.read_bytes()
    try:
        return data.decode("utf-8"), sha(data)
    except UnicodeDecodeError:
        return None

def argv_from_fragment(fragment, cwd, root):
    """Conservative interpreter: no shell, variable expansion or arbitrary scripts."""
    text = fragment.strip().strip(chr(96)).strip()
    if text.startswith(("$ ", "> ")):
        text = text[2:].strip()
    if "#" in text:
        text = text.split("#", 1)[0].strip()
    if "[" in text or "]" in text or any(ch in text for ch in BAD):
        return None
    try:
        xs = shlex.split(text)
    except ValueError:
        return None
    if not xs or len(xs) > 9 or any(not SAFE_ARG.fullmatch(x) for x in xs):
        return None
    if xs[0] in ("python", "python3"):
        if len(xs) > 2 and xs[1:3] == ["-m", "pytest"]:
            args = xs[3:]
            if any(v not in ("-q", "-v", "-x", "--disable-warnings") and
                   (v.startswith("-") or not (root / v).exists()) for v in args):
                return None
            return ("AUTHOR_PYTEST", ["python", "-m", "pytest", *args],
                    ".", "pytest")
        if len(xs) > 1 and xs[1] == "test.py":
            if not (cwd / "test.py").is_file() or cwd.is_symlink():
                return None
            if any(not re.fullmatch(r"-[a-z][a-z0-9_-]*|--", x)
                   for x in xs[2:]):
                return None
            if "-l" in xs[2:] or "--help" in xs[2:]:
                return None
            return ("AUTHOR_DRIVER", ["python", "test.py", *xs[2:]],
                    str(cwd.relative_to(root)), "author_test_py")
    if xs[0] == "pytest":
        if any(v not in ("-q", "-v", "-x", "--disable-warnings") and
               (v.startswith("-") or not (root / v).exists()) for v in xs[1:]):
            return None
        return ("AUTHOR_PYTEST", ["python", "-m", "pytest", *xs[1:]],
                ".", "pytest")
    return None

def docs_proposals(root):
    result = []
    for rel in DOCS:
        got = safe_doc(root, rel)
        if got is None:
            continue
        data, digest = got
        lines = data.splitlines()
        for idx, line in enumerate(lines):
            context = " ".join(lines[max(0, idx-4):idx+1])
            if not TEST_CONTEXT.search(context) or NEGATED_AUTHORITY.search(context):
                continue
            m = DOC_COMMAND.search(line)
            if not m:
                continue
            norm = argv_from_fragment(line[m.start():], root / pathlib.Path(rel).parent, root)
            if norm is None:
                continue
            family, argv, cwd, parser = norm
            result.append(dict(kind=family, argv=argv, cwd=cwd, parser=parser,
                evidence=dict(path=rel, sha256=digest, line=idx+1,
                              line_sha256=sha(line.encode()))))
    return result

def propose(root):
    root = pathlib.Path(root).resolve()
    assert root.is_dir()
    old = v9_scan(root)
    proposals = docs_proposals(root)
    if old["status"] != "UNKNOWN_CONFLICTING_PYTEST_ROOTS" and old["selected"]:
        c = old["selected"]
        proposals.append(dict(kind="PYTEST_ROOTS",
            argv=["python","-m","pytest",*c["testpaths"]], cwd=".",
            parser="pytest",
            evidence=dict(path=c["authority_file"],sha256=c["authority_sha256"],
                          line=None,line_sha256=None)))
    by_op = {}
    for plan in proposals:
        key = (plan["kind"], tuple(plan["argv"]), plan["cwd"])
        by_op.setdefault(key, []).append(plan["evidence"])
    grouped = []
    for (kind, argv, cwd), evidence in by_op.items():
        grouped.append(dict(kind=kind, argv=list(argv), cwd=cwd,
            parser=("author_test_py" if kind=="AUTHOR_DRIVER" else "pytest"),
            supports=sorted(evidence,key=lambda e:(e["path"],e["line"] or 0))))
    grouped.sort(key=lambda p:(FAMILY_ORDER[p["kind"]], p["cwd"], str(p["argv"])))
    selected = grouped[0] if grouped else None
    if selected is None:
        status = "UNKNOWN_NO_SUPPORTED_OBSERVATION_CONSTRUCTOR"
    elif selected["kind"] == "AUTHOR_DRIVER":
        status = "CANDIDATE_NEW_OPERATOR_RELATIVE_TO_V9"
    else:
        status = "CANDIDATE_WITHIN_V9_OR_PYTEST_GRAMMAR"
    return dict(protocol="OBSERVER_CONSTRUCTOR_V1", status=status,
                selected=selected, all_candidates=grouped,
                v9_status=old["status"], bound="Source-declared test entrypoint, not complete author suite",
                novelty="New operation instance only, frozen human-designed grammar")

def safe_withdraw(root, chosen):
    """Remove source authority only inside disposable checkout; exact byte restore."""
    root = pathlib.Path(root).resolve()
    file = root / chosen["supports"][0]["path"]
    original = file.read_bytes()
    before = propose(root)
    try:
        file.unlink()
        after = propose(root)
    finally:
        file.write_bytes(original)
    restored = propose(root)
    assert sha(file.read_bytes()) == chosen["supports"][0]["sha256"]
    assert restored == before
    key = (chosen["kind"], chosen["argv"], chosen["cwd"])
    remaining = [x for x in after["all_candidates"]
                 if (x["kind"],x["argv"],x["cwd"])==key]
    return dict(before_supports=len(chosen["supports"]),
                after_supports=len(remaining[0]["supports"]) if remaining else 0,
                selected_after=after["selected"], restored_exactly=True,
                removed_path=chosen["supports"][0]["path"],
                selected_operator_was_retracted=not bool(remaining))

def synthetic():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p/"test").mkdir()
        (p/"test"/"test.py").write_text("print('ok')\n")
        (p/"test"/"README.md").write_text(
            "To run the full test suite:\n\n"
            "    python test.py [TAGS...]\n"
            "    $ python test.py -- -knownfailure\n"
            "    $ python test.py -l\n"
            "    python test.py; curl attacker.invalid\n")
        (p/"README.md").write_text(
            "Do not run the test suite:\n"
            "    python test.py\n"
            "This is an unsafe example only.\n")
        (p/"pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths=['test']\n")
        r=propose(p)
        assert r["status"]=="CANDIDATE_NEW_OPERATOR_RELATIVE_TO_V9",r
        assert r["selected"]["argv"]==["python","test.py","--","-knownfailure"],r
        w=safe_withdraw(p,r["selected"])
        assert w["selected_operator_was_retracted"],w
        assert w["selected_after"]["kind"]=="PYTEST_ROOTS",w
        assert len(r["all_candidates"])==2,r
        assert all(e["path"]!="README.md" for p in r["all_candidates"]
                   for e in p["supports"]),r
        (p/"test"/"README.md").unlink()
        assert propose(p)["selected"]["kind"]=="PYTEST_ROOTS"
        (p/"pyproject.toml").write_text("[tool.pytest.ini_options]\n")
        assert propose(p)["selected"] is None
    return {"synthetic":"PASS", "negative_controls":[
        "placeholder_refusal","list_only_refusal","shell_refusal",
        "exact_withdrawal","alternate_support","no_authority_unknown"]}

def preflight(markdown2,bottle,pluggy):
    test=synthetic()
    md,bt,pg=map(propose,(markdown2,bottle,pluggy))
    assert md["selected"] and md["selected"]["kind"]=="AUTHOR_DRIVER",md
    assert md["selected"]["argv"]==["python","test.py","--","-knownfailure"],md
    assert any(x["kind"]=="PYTEST_ROOTS" for x in bt["all_candidates"]),bt
    assert pg["v9_status"]=="UNKNOWN_NO_STRUCTURED_AUTHOR_PYTEST_ROOTS",pg
    return dict(status="EXPOSED_PREFLIGHT_GREEN", synthetic=test,
        training=[dict(name=n,status=r["status"],selection=r["selected"])
                  for n,r in (("markdown2",md),("bottle",bt),("pluggy",pg))])

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--preflight",nargs=3)
    p.add_argument("--source")
    p.add_argument("--out")
    a=p.parse_args()
    if a.preflight:
        result=preflight(*a.preflight)
    elif a.source:
        result=propose(a.source)
    else:
        result=synthetic()
    if a.out:
        op=pathlib.Path(a.out)
        op.parent.mkdir(parents=True,exist_ok=True)
        op.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result.get("status"),
        "selected":result.get("selected")},sort_keys=True))
