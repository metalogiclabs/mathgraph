#!/usr/bin/env python3
"""Static import closure of OpenAI Logspace solution at a fixed commit.

This is deliberately NOT Lean, Comparator, or a sound axiom audit.
"""
import argparse
import json
import re
import urllib.request
from pathlib import Path

from openai_math_audit import PIN, REPO, git_blob_sha

PREFIX = "OAI.Computability.Logspace."
ROOT = "Equality"
DIR = "lean/OAI/Computability/Logspace/"
API = f"https://api.github.com/repos/{REPO}/contents/{DIR}?ref={PIN}"
RAW = f"https://raw.githubusercontent.com/{REPO}/{PIN}/{DIR}"
FLAG = re.compile(r"\b(axiom|sorry|admit|unsafe|opaque|native_decide)\b")


def strip_comments(source):
    """Erase Lean line and nested block comments; preserve newlines and offsets."""
    out = []
    depth = 0
    i = 0
    while i < len(source):
        two = source[i:i+2]
        if depth:
            if two == "/-":
                depth += 1
                out.extend("  ")
                i += 2
            elif two == "-/":
                depth -= 1
                out.extend("  ")
                i += 2
            else:
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
        elif two == "/-":
            depth = 1
            out.extend("  ")
            i += 2
        elif two == "--":
            stop = source.find("\n", i)
            if stop < 0:
                out.extend(" " * (len(source) - i))
                i = len(source)
            else:
                out.extend(" " * (stop - i))
                i = stop
        else:
            out.append(source[i])
            i += 1
    if depth:
        raise ValueError("UNTERMINATED_BLOCK_COMMENT")
    return "".join(out)


def load_manifest():
    with urllib.request.urlopen(API, timeout=40) as resp:
        listing = json.load(resp)
    assert isinstance(listing, list)
    return {entry["name"][:-5]: entry["sha"] for entry in listing
            if entry.get("type") == "file" and entry["name"].endswith(".lean")}


def load_module(name):
    with urllib.request.urlopen(RAW + name + ".lean", timeout=45) as resp:
        return resp.read()


def audit(manifest, loader, root=ROOT):
    """Compute transitive OAI Logspace source imports; fail closed on unknown local import."""
    seen = {}
    pending = [root]
    external = set()
    warnings = []
    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        if name not in manifest:
            raise ValueError("MISSING_PINNED_MODULE: " + name)
        raw = loader(name)
        actual = git_blob_sha(raw)
        if actual != manifest[name]:
            raise ValueError("BLOB_SHA_MISMATCH: " + name)
        stripped = strip_comments(raw.decode("utf-8"))
        imports = []
        for line in stripped.splitlines():
            match = re.match(r"^\s*import\s+(.+?)\s*$", line)
            if match:
                imports.extend(match.group(1).split())
        local = set()
        for dep in imports:
            if dep.startswith(PREFIX):
                child = dep[len(PREFIX):]
                local.add(child)
                if child not in seen:
                    pending.append(child)
            else:
                external.add(dep)
                if dep != "Mathlib" and not dep.startswith("Mathlib."):
                    warnings.append({"module": name, "unrecognized_external_import": dep})
        flags = [{"line": stripped.count("\n", 0, x.start()) + 1, "token": x.group(1)}
                 for x in FLAG.finditer(stripped)]
        if flags:
            warnings.append({"module": name, "lexical_risk_signals": flags})
        seen[name] = {
            "path": DIR + name + ".lean",
            "blob_sha": actual,
            "local_imports": sorted(local),
            "external_imports": sorted(set(imports) - {PREFIX + x for x in local}),
            "lexical_risk_signals": flags,
        }
        if len(seen) > 80:
            raise ValueError("UNEXPECTED_IMPORT_CLOSURE_SIZE")
    return {
        "upstream": {"repository": REPO, "commit": PIN},
        "root_solution_module": PREFIX + root,
        "modules_in_import_closure": len(seen),
        "modules_in_directory": len(manifest),
        "unreached_directory_modules": sorted(set(manifest) - set(seen)),
        "external_imports": sorted(external),
        "modules": {key: seen[key] for key in sorted(seen)},
        "warnings": warnings,
        "status": "STATIC_IMPORT_CLOSURE_WITH_RISK_SIGNALS" if warnings else "STATIC_IMPORT_CLOSURE_NO_LEXICAL_RISK_SIGNALS",
        "verification_boundary": "Only source comments stripped and lexical tokens scanned; not a parser, kernel replay, transitive axiom audit, or proof of paper correspondence",
        "main_theorem_status": "UNKNOWN_INDEPENDENT_LEAN_REPLAY",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output")
    opts = ap.parse_args()
    result = audit(load_manifest(), load_module)
    report = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if opts.output:
        Path(opts.output).write_text(report, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "modules"}, indent=2))
    # Gate only well-scoped material risks. Lexical flags require review, not theorem rejection.
    if result["warnings"]:
        raise SystemExit("REVIEW_REQUIRED: static import preflight produced signals")


if __name__ == "__main__":
    main()
