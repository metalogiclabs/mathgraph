#!/usr/bin/env python3
"""Exact-source RH claimed theorem import census (STATIC ONLY, no proof replay)."""
import argparse
from collections import deque, Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

EXPECTED = "7cbf7a0c32fca1badf05931879a37c3f8a2b03b4"
MATHLIB = "0df444a360eaa60ab8c11dca51a86af692955474"
TOOLCHAIN = "leanprover/lean4:v4.33.1"
KEY = [
    "Main",
    "Statements",
    "Supplements.Kernels.MainTheorems",
    "Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion",
    "Development.AutomorphicArithmetic.CharacterBoxes.EveryCharacter",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.EveryCharacterOfLiteratureOfVWin",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.SiegelEisensteinSecondTermHypotheses",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.VwinOfRow",
    "Development.AutomorphicArithmetic.Foundations.LocalLanglands.LocalCentralUnits.RecTExists",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.RowSrc",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GaloisRepresentationsOfThetaLift",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.ThetaParseval.ThetaKernels.TLiftK",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.LocalTypeDictionary.DiscreteSpectrumResidualClassification",
]
P_IMPORT = re.compile(r"^\s*(?:(?:public|private)\s+)?import\s+([a-zA-Z0-9_.'\u0080-\uffff]+)")
P_DECL = re.compile(r"^\s*(?:(?:noncomputable|private|protected|local|scoped)\s+)*(axiom|constant|opaque)\b")
P_SUSPECT = re.compile(r"\b(?:sorry|admit|native_decide|unsafe|implemented_by|Lean\.ofReduceBool)\b|(?:^|\W)addDecl\b")
P_TRUE = re.compile(r"\b(?:abbrev|def)\s+([^\n:]+):\s*Prop\s*:=\s*True\b")
def strip_comments(text):
    depth, out = 0, []
    for line in text.splitlines():
        i, buf = 0, []
        while i < len(line):
            if line.startswith("/-", i):
                depth += 1; i += 2; continue
            if depth:
                if line.startswith("-/", i): depth -= 1; i += 2
                else: i += 1
                continue
            if line.startswith("--", i): break
            if line[i] == '"':
                i += 1
                while i < len(line):
                    if line[i] == "\\": i += 2
                    elif line[i] == '"': i += 1; break
                    else: i += 1
                buf.append('"STRING"'); continue
            buf.append(line[i]); i += 1
        out.append("".join(buf))
    if depth: raise RuntimeError("unclosed block comment")
    return "\n".join(out)
def path_of(src, module):
    return src.joinpath(*module.split(".")).with_suffix(".lean")
def content(src, module):
    return strip_comments(path_of(src, module).read_text(encoding="utf-8"))
def test_lexer():
    v = strip_comments('import A\n/- import B /- axiom bogus -/ -/\nimport C\n-- sorry\n')
    assert "import A" in v and "import C" in v
    assert "import B" not in v and "axiom" not in v and "sorry" not in v
def audit(src):
    test_lexer()
    sha = subprocess.check_output(["git", "-C", str(src.parent), "rev-parse", "HEAD"],text=True).strip()
    assert sha == EXPECTED, (sha, EXPECTED)
    assert (src.parent / "lean-toolchain").read_text().strip() == TOOLCHAIN
    assert MATHLIB in (src.parent / "lakefile.toml").read_text()
    queue, visited, parent, externals, findings, aliases, checked = deque(["Main"]), set(), {"Main": None}, Counter(), [], [], {}
    edges = 0
    while queue:
        module = queue.popleft()
        if module in visited: continue
        file = path_of(src, module)
        if not file.is_file(): raise RuntimeError("unresolved internal import: " + module)
        visited.add(module)
        code = strip_comments(file.read_text(encoding="utf-8"))
        if module in KEY: checked[module] = hashlib.sha256(file.read_bytes()).hexdigest()
        for i,line in enumerate(code.splitlines(),1):
            match = P_IMPORT.match(line)
            if match:
                child=match.group(1)
                if path_of(src, child).is_file():
                    edges += 1
                    if child not in parent: parent[child] = module; queue.append(child)
                else: externals[child] += 1
            match=P_DECL.match(line)
            if match:
                findings.append({"module":module,"line":i,"kind":"declaration_"+match.group(1)})
            elif P_SUSPECT.search(line):
                findings.append({"module":module,"line":i,"kind":"review_token","sample":line.strip()[:120]})
            match=P_TRUE.search(line)
            if match:
                aliases.append({"module":module,"line":i,"name":match.group(1).strip()})
    missing = sorted(set(KEY) - visited)
    if missing: raise RuntimeError("missing critical source: " + str(missing))
    main=content(src,"Main")
    link=content(src,"Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion")
    assert "theorem riemannHypothesis : RiemannHypothesis := rhOfAll" in main
    assert "UpperTheory.FinalTheorems.everyCharacter_of_row UpperTheory.Gal.Int.galoisLocalGlobalStrong_recParameter" in link
    routes={}
    for item in KEY:
        path=[]; node=item
        while node is not None:
            path.append(node)
            node=parent[node]
        routes[item]=list(reversed(path))
    total=sum(1 for _ in src.rglob("*.lean"))
    return {
        "status":"SOURCE_ONLY_NOT_PROOF_WARRANT",
        "claim_source_commit":sha,
        "mathlib_sha":MATHLIB,
        "lean_toolchain":TOOLCHAIN,
        "total_lean_files":total,
        "root_import_modules":len(visited),
        "root_import_edges":edges,
        "external_import_roots":dict(externals.most_common(30)),
        "critical_routes":routes,
        "critical_file_sha256":checked,
        "surface_trust_findings_count":len(findings),
        "surface_trust_findings":findings[:100],
        "surface_true_aliases_count":len(aliases),
        "surface_true_aliases":aliases[:100],
        "suspected_semantic_placeholder":"GlobalTheory.Published.UnusedSlot72 : Prop := True; field siegelEisensteinSimplePole (NOT a proof flaw by itself)",
        "limitations":["Static source and import traversal, not compiled proof dependency closure",
                       "No theorem typechecking or external kernel acceptance",
                       "String/comment stripping is a source heuristic, not a Lean parser",
                       "Meaning of domain-specific structures requires mathematical review"],
    }
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    result=audit(a.source.resolve() / "src")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:result[k] for k in ["status","claim_source_commit","total_lean_files","root_import_modules","root_import_edges","surface_trust_findings_count","surface_true_aliases_count"]},indent=2))
    print("WARNING: no RH or GRH theorem has been independently checked by this audit")
