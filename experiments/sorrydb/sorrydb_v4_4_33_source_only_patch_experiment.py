from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.33"
OUT = Path("artifacts/sorrydb/source_only_patch_experiment_v4_4_33")
PATCHES = OUT / "patches"
WORK = Path(".tmp_sorrydb_v4_4_33_source_only_patch")

INPUTS = {
    "recon_summary": Path("artifacts/sorrydb/active_target_recon_v4_4_32/summary.json"),
    "recon": Path("artifacts/sorrydb/active_target_recon_v4_4_32/active_target_recon.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "cwd": str(cwd) if cwd else None,
        "returncode": p.returncode,
        "stdout": p.stdout[-4000:],
        "stderr": p.stderr[-4000:],
        "ok": p.returncode == 0,
    }

def find_windows(text: str, needle: str, radius: int = 8) -> list[dict[str, Any]]:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if needle in line:
            start = max(0, i - radius)
            end = min(len(lines), i + radius + 1)
            out.append({
                "line_number": i + 1,
                "line": line,
                "snippet": "\n".join(f"{j+1}: {lines[j]}" for j in range(start, end)),
            })
    return out

def sorry_line_number(text: str) -> int:
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "sorry":
            return i
    return -1

def apply_patch(text: str, patch_body: str) -> str:
    lines = text.splitlines()
    out = []
    replaced = False
    for line in lines:
        if not replaced and line.strip() == "sorry":
            indent = line[: len(line) - len(line.lstrip())]
            body_lines = patch_body.splitlines()
            out.extend([(indent + x) if x.strip() else x for x in body_lines])
            replaced = True
        else:
            out.append(line)
    return "\n".join(out) + "\n"

def plausibility_score(patch_text: str, patched_file: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if "sorry" not in patched_file:
        score += 20
        reasons.append("removes active sorry")
    if "exact" in patch_text:
        score += 8
        reasons.append("uses exact")
    if "refine" in patch_text:
        score += 6
        reasons.append("uses refine")
    if "simpa" in patch_text or "simp" in patch_text:
        score += 4
        reasons.append("uses simp/simpa")
    if "hSymm" in patch_text:
        score += 8
        reasons.append("uses hSymm")
    if "hL2args" in patch_text and "hR2args" in patch_text:
        score += 6
        reasons.append("uses arity hypotheses")
    if "Equiv.swap" in patch_text:
        score += 4
        reasons.append("uses swap witness")
    if "by" in patch_text:
        score += 1
        reasons.append("Lean tactic syntax present")
    if "?_" in patch_text:
        score -= 8
        reasons.append("contains metavariable placeholder")
    if "admit" in patch_text or "sorry" in patch_text:
        score -= 100
        reasons.append("contains forbidden placeholder")

    opens = patched_file.count("(") + patched_file.count("[") + patched_file.count("{")
    closes = patched_file.count(")") + patched_file.count("]") + patched_file.count("}")
    if abs(opens - closes) <= 2:
        score += 2
        reasons.append("rough delimiter balance ok")
    else:
        score -= 5
        reasons.append("rough delimiter imbalance")

    return score, reasons

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)
    PATCHES.mkdir(parents=True, exist_ok=True)

    recon_summary = load_json(INPUTS["recon_summary"])
    recon = load_json(INPUTS["recon"])

    repo = recon["repo"]
    commit = recon["commit"]
    target_path = recon["target_path"]
    clone_url = f"https://github.com/{repo}.git"

    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)

    steps = []
    steps.append(run(["git", "clone", "--filter=blob:none", "--depth", "1", clone_url, "repo"], cwd=WORK, timeout=180))
    repo_dir = WORK / "repo"
    if repo_dir.exists():
        steps.append(run(["git", "fetch", "--depth", "1", "origin", commit], cwd=repo_dir, timeout=180))
        steps.append(run(["git", "checkout", commit], cwd=repo_dir, timeout=120))

    target_file = repo_dir / target_path
    target_text = target_file.read_text(encoding="utf-8", errors="replace") if target_file.exists() else ""

    definability_file = repo_dir / "equational_theories" / "Definability" / "Basic.lean"
    definability_text = definability_file.read_text(encoding="utf-8", errors="replace") if definability_file.exists() else ""

    termdef_windows = find_windows(definability_text, "TermDefinableFrom", 10)
    law43_windows = find_windows(target_text, "Law43.TermDefinableFrom", 8)
    target_sorry_line = sorry_line_number(target_text)

    candidate_patches = [
        {
            "patch_id": "patch-001-exact-constructor-four-fields",
            "body": "exact ⟨fun x ↦ Lf (Equiv.swap 0 1 x), hL2args, hR2args, hSymm⟩",
            "rationale": "try direct constructor witness: swapped variable map plus arity hypotheses plus symmetry equation",
        },
        {
            "patch_id": "patch-002-refine-constructor-four-fields",
            "body": "refine ⟨fun x ↦ Lf (Equiv.swap 0 1 x), ?_, ?_, ?_⟩\n· exact hL2args\n· exact hR2args\n· exact hSymm",
            "rationale": "same as patch 001 but exposes constructor subgoals separately",
        },
        {
            "patch_id": "patch-003-exact-constructor-three-fields",
            "body": "exact ⟨hL2args, hR2args, hSymm⟩",
            "rationale": "try if TermDefinableFrom already fixes witness through Law43 context",
        },
        {
            "patch_id": "patch-004-simpa-using-symmetry",
            "body": "simpa using hSymm",
            "rationale": "try if target reduces directly to the supplied symmetry equality",
        },
        {
            "patch_id": "patch-005-simpa-definability-using-symmetry",
            "body": "simpa [Law43.TermDefinableFrom] using hSymm",
            "rationale": "try unfolding the target definability predicate at Law43",
        },
    ]

    patch_results = []
    for patch in candidate_patches:
        patched = apply_patch(target_text, patch["body"])
        score, reasons = plausibility_score(patch["body"], patched)
        patch_file = PATCHES / f"{patch['patch_id']}.lean"
        patch_diff_file = PATCHES / f"{patch['patch_id']}.patch.txt"
        patch_file.write_text(patched, encoding="utf-8")

        original_lines = target_text.splitlines()
        patched_lines = patched.splitlines()
        start = max(1, target_sorry_line - 4)
        end = min(len(patched_lines), target_sorry_line + len(patch["body"].splitlines()) + 4)

        local_window = "\n".join(f"{i}: {patched_lines[i-1]}" for i in range(start, end + 1))
        patch_diff_file.write_text(local_window + "\n", encoding="utf-8")

        patch_results.append({
            "patch_id": patch["patch_id"],
            "rationale": patch["rationale"],
            "body": patch["body"],
            "plausibility_score": score,
            "plausibility_reasons": reasons,
            "patched_file": str(patch_file),
            "patched_window": local_window,
            "contains_sorry_after_patch": "sorry" in patched,
            "status": "SOURCE_ONLY_PATCH_CANDIDATE_NOT_REPLAYED",
        })

    patch_results.sort(key=lambda x: (-x["plausibility_score"], x["patch_id"]))
    selected = patch_results[0] if patch_results else None

    experiment = {
        "version": VERSION,
        "experiment_type": "SOURCE_ONLY_PATCH_EXPERIMENT_BEFORE_REPLAY",
        "input_version": recon_summary.get("version"),
        "repo": repo,
        "commit": commit,
        "target_path": target_path,
        "target_exists": target_file.exists(),
        "target_sorry_line": target_sorry_line,
        "definability_basic_exists": definability_file.exists(),
        "termdef_window_count": len(termdef_windows),
        "termdef_windows": termdef_windows[:5],
        "law43_windows": law43_windows[:5],
        "patch_candidate_count": len(patch_results),
        "selected_patch": selected,
        "patches": patch_results,
        "steps": steps,
        "clone_attempted": True,
        "build_attempted": False,
        "replay_attempted": False,
        "upstream_contact_performed": False,
        "decision": "SOURCE_ONLY_PATCHES_READY_FOR_BOUNDED_REPLAY_SELECTION",
    }

    summary = {
        "version": VERSION,
        "status": "SOURCE_ONLY_PATCH_EXPERIMENT_LEDGERED",
        "input_version": recon_summary.get("version"),
        "repo": repo,
        "commit": commit,
        "target_path": target_path,
        "target_sorry_line": target_sorry_line,
        "patch_candidate_count": len(patch_results),
        "selected_patch_id": selected["patch_id"] if selected else "",
        "selected_patch_score": selected["plausibility_score"] if selected else None,
        "selected_patch_status": selected["status"] if selected else "",
        "clone_attempted": True,
        "build_attempted": False,
        "replay_attempted": False,
        "upstream_contact_performed": False,
        "decision": experiment["decision"],
        "bounded_claim": [
            "v4.4.33 creates source-only candidate patches for the selected active-sorry target",
            "it records definability context windows and ranks candidate patches by syntactic plausibility",
            "it does not build, replay Lean, modify upstream, or contact maintainers",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "that any patch typechecks",
            "that any patch is mathematically valid",
            "that the repo builds locally",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.34 run bounded Lean replay for the selected source-only patch only, with strict timeout and no upstream contact",
    }

    report_lines = [
        "# SorryDB v4.4.33 — Source-Only Patch Experiment",
        "",
        "## Result",
        "",
        f"- repo: {repo}",
        f"- commit: {commit}",
        f"- target path: {target_path}",
        f"- target sorry line: {target_sorry_line}",
        f"- definability context windows: {len(termdef_windows)}",
        f"- patch candidate count: {len(patch_results)}",
        f"- selected patch: {summary['selected_patch_id']}",
        f"- selected patch score: {summary['selected_patch_score']}",
        f"- build attempted: false",
        f"- replay attempted: false",
        "",
    ]

    if selected:
        report_lines.extend([
            "## Selected patch",
            "",
            f"- patch id: {selected['patch_id']}",
            f"- score: {selected['plausibility_score']}",
            f"- reasons: {', '.join(selected['plausibility_reasons'])}",
            f"- rationale: {selected['rationale']}",
            "",
            "```lean",
            selected["body"],
            "```",
            "",
            "## Patched local window",
            "",
            "```lean",
            selected["patched_window"],
            "```",
            "",
        ])

    report_lines.extend([
        "## TermDefinableFrom context",
        "",
        "```lean",
        termdef_windows[0]["snippet"] if termdef_windows else "(not found)",
        "```",
        "",
        "## Boundary",
        "",
        "No Lean build, Lean replay, upstream modification, or maintainer contact was performed.",
        "",
        "## Next frontier",
        "",
        "Run bounded Lean replay for the selected patch only, with strict timeout and no upstream contact.",
        "",
    ])

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "source_only_patch_experiment.json", experiment)
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    shutil.rmtree(WORK, ignore_errors=True)

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
