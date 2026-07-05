from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.34"
OUT = Path("artifacts/sorrydb/bounded_replay_v4_4_34")
WORK = Path(".tmp_sorrydb_v4_4_34_bounded_replay")
CACHED = OUT / "bounded_replay_result.json"

INPUTS = {
    "patch_summary": Path("artifacts/sorrydb/source_only_patch_experiment_v4_4_33/summary.json"),
    "patch_experiment": Path("artifacts/sorrydb/source_only_patch_experiment_v4_4_33/source_only_patch_experiment.json"),
}

TIMEOUT_SECONDS = 360

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    try:
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
            "timeout_seconds": timeout,
            "timed_out": False,
            "returncode": p.returncode,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-12000:],
            "ok": p.returncode == 0,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "timeout_seconds": timeout,
            "timed_out": True,
            "returncode": None,
            "stdout": (e.stdout or "")[-12000:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-12000:] if isinstance(e.stderr, str) else "",
            "ok": False,
        }

def replace_first_active_sorry(text: str, patch_body: str) -> tuple[str, bool]:
    lines = text.splitlines()
    out = []
    replaced = False
    for line in lines:
        if not replaced and line.strip() == "sorry":
            indent = line[: len(line) - len(line.lstrip())]
            out.extend([(indent + x) if x.strip() else x for x in patch_body.splitlines()])
            replaced = True
        else:
            out.append(line)
    return "\n".join(out) + "\n", replaced

def classify_replay(step: dict[str, Any], patched_text: str) -> tuple[str, list[str]]:
    reasons = []
    if step["timed_out"]:
        return "TIMEOUT", [f"replay exceeded {step['timeout_seconds']}s timeout"]
    if step["ok"]:
        if "sorry" not in patched_text:
            return "ACCEPTED_NO_SORRY_IN_PATCHED_TARGET", ["lake env lean returned 0", "patched target contains no active sorry"]
        return "ACCEPTED_BUT_SORRY_REMAINS", ["lake env lean returned 0", "patched target still contains sorry text"]
    stderr = step.get("stderr", "")
    stdout = step.get("stdout", "")
    combined = stderr + "\n" + stdout
    if "unknown identifier" in combined:
        reasons.append("unknown identifier")
    if "application type mismatch" in combined:
        reasons.append("application type mismatch")
    if "type mismatch" in combined:
        reasons.append("type mismatch")
    if "failed to synthesize" in combined:
        reasons.append("failed to synthesize instance")
    if "unknown package" in combined or "unknown module" in combined:
        reasons.append("import/module failure")
    if "error:" in combined:
        reasons.append("Lean reported error")
    if not reasons:
        reasons.append("nonzero replay exit")
    return "REJECTED_BY_LOCAL_REPLAY", reasons

def build_fresh_result() -> dict[str, Any]:
    patch_summary = load_json(INPUTS["patch_summary"])
    patch_exp = load_json(INPUTS["patch_experiment"])
    selected = patch_exp["selected_patch"]

    repo = patch_exp["repo"]
    commit = patch_exp["commit"]
    target_path = patch_exp["target_path"]
    clone_url = f"https://github.com/{repo}.git"
    patch_body = selected["body"]

    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)

    steps = []
    steps.append(run(["git", "clone", "--filter=blob:none", "--depth", "1", clone_url, "repo"], cwd=WORK, timeout=180))
    repo_dir = WORK / "repo"

    if repo_dir.exists():
        steps.append(run(["git", "fetch", "--depth", "1", "origin", commit], cwd=repo_dir, timeout=180))
        steps.append(run(["git", "checkout", commit], cwd=repo_dir, timeout=120))

    target_file = repo_dir / target_path
    target_exists = target_file.exists()
    original_text = target_file.read_text(encoding="utf-8", errors="replace") if target_exists else ""
    patched_text, replaced = replace_first_active_sorry(original_text, patch_body) if target_exists else ("", False)

    if target_exists and replaced:
        target_file.write_text(patched_text, encoding="utf-8")

    replay_step = {
        "cmd": ["lake", "env", "lean", target_path],
        "cwd": str(repo_dir),
        "timeout_seconds": TIMEOUT_SECONDS,
        "timed_out": False,
        "returncode": None,
        "stdout": "",
        "stderr": "not run",
        "ok": False,
    }

    if target_exists and replaced:
        replay_step = run(["lake", "env", "lean", target_path], cwd=repo_dir, timeout=TIMEOUT_SECONDS)

    replay_status, replay_reasons = classify_replay(replay_step, patched_text)

    diff_step = run(["git", "diff", "--", target_path], cwd=repo_dir, timeout=30) if repo_dir.exists() else {
        "cmd": ["git", "diff", "--", target_path],
        "cwd": str(repo_dir),
        "timeout_seconds": 30,
        "timed_out": False,
        "returncode": None,
        "stdout": "",
        "stderr": "repo dir missing",
        "ok": False,
    }

    result = {
        "version": VERSION,
        "replay_type": "BOUNDED_SELECTED_PATCH_REPLAY",
        "input_version": patch_summary.get("version"),
        "repo": repo,
        "clone_url": clone_url,
        "commit": commit,
        "target_path": target_path,
        "selected_patch_id": selected["patch_id"],
        "selected_patch_body": patch_body,
        "target_exists": target_exists,
        "active_sorry_replaced": replaced,
        "patched_target_contains_sorry": "sorry" in patched_text,
        "clone_attempted": True,
        "checkout_attempted": True,
        "patch_attempted": True,
        "build_attempted": False,
        "replay_attempted": True,
        "upstream_contact_performed": False,
        "timeout_seconds": TIMEOUT_SECONDS,
        "replay_status": replay_status,
        "replay_reasons": replay_reasons,
        "steps": steps,
        "replay_step": replay_step,
        "diff": diff_step.get("stdout", ""),
        "decision": "PROMOTE_TO_UPSTREAM_PATCH_PACKAGE" if replay_status == "ACCEPTED_NO_SORRY_IN_PATCHED_TARGET" else "REPLAY_REJECTED_OR_TIMED_OUT_NO_UPSTREAM_CONTACT",
    }

    shutil.rmtree(WORK, ignore_errors=True)
    return result

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)

    if CACHED.exists():
        result = load_json(CACHED)
    else:
        result = build_fresh_result()
        write_json(CACHED, result)

    summary = {
        "version": VERSION,
        "status": "BOUNDED_REPLAY_LEDGERED",
        "input_version": result["input_version"],
        "repo": result["repo"],
        "commit": result["commit"],
        "target_path": result["target_path"],
        "selected_patch_id": result["selected_patch_id"],
        "clone_attempted": result["clone_attempted"],
        "checkout_attempted": result["checkout_attempted"],
        "patch_attempted": result["patch_attempted"],
        "build_attempted": result["build_attempted"],
        "replay_attempted": result["replay_attempted"],
        "upstream_contact_performed": result["upstream_contact_performed"],
        "timeout_seconds": result["timeout_seconds"],
        "replay_status": result["replay_status"],
        "replay_reasons": result["replay_reasons"],
        "decision": result["decision"],
        "bounded_claim": [
            "v4.4.34 runs a bounded local Lean replay for the selected v4.4.33 source-only patch",
            "it applies only the selected patch to the pinned target file",
            "it records acceptance, rejection, or timeout without contacting upstream",
        ],
        "does_not_claim": [
            "upstream acceptance",
            "automated external contact",
            "full repository build",
            "general proof discovery",
            "portability beyond the pinned checkout",
        ],
        "next_frontier": "if accepted, package an upstream patch note; if rejected or timed out, record obstruction and choose the next active candidate",
    }

    report_lines = [
        "# SorryDB v4.4.34 — Bounded Replay",
        "",
        "## Result",
        "",
        f"- repo: {result['repo']}",
        f"- commit: {result['commit']}",
        f"- target path: {result['target_path']}",
        f"- selected patch: {result['selected_patch_id']}",
        f"- timeout seconds: {result['timeout_seconds']}",
        f"- clone attempted: {result['clone_attempted']}",
        f"- patch attempted: {result['patch_attempted']}",
        f"- build attempted: {result['build_attempted']}",
        f"- replay attempted: {result['replay_attempted']}",
        f"- replay status: {result['replay_status']}",
        f"- decision: {result['decision']}",
        "",
        "## Replay reasons",
        "",
        "\n".join("- " + r for r in result["replay_reasons"]),
        "",
        "## Patch",
        "",
        "```lean",
        result["selected_patch_body"],
        "```",
        "",
        "## Diff",
        "",
        "```diff",
        result["diff"][:8000],
        "```",
        "",
        "## Replay stderr tail",
        "",
        "```text",
        result["replay_step"].get("stderr", "")[-8000:],
        "```",
        "",
        "## Boundary",
        "",
        "No upstream modification or maintainer contact was performed.",
        "",
    ]

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "bounded_replay_result.json", result)
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
