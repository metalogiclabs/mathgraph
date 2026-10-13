#!/usr/bin/env python
"""Run a read-only local or Colab-friendly MathGraph test drive."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from _bootstrap import ensure_repo_root_on_path
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
else:
    ensure_repo_root_on_path(__file__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(argv: list[str], *, cwd: Path, env: dict[str, str], timeout: float, name: str, output_path: Path | None = None) -> dict[str, object]:
    started = _now()
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        record = {
            "name": name,
            "argv": argv,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "started_at": started,
            "stdout_excerpt": proc.stdout[-1200:],
            "stderr_excerpt": proc.stderr[-1200:],
        }
    except subprocess.TimeoutExpired as exc:
        record = {
            "name": name,
            "argv": argv,
            "returncode": None,
            "ok": False,
            "started_at": started,
            "stdout_excerpt": str(exc.stdout or "")[-1200:],
            "stderr_excerpt": str(exc.stderr or "")[-1200:],
            "timed_out": True,
        }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return record


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _repo_root(args: argparse.Namespace) -> Path:
    if args.use_current_checkout:
        return Path(__file__).resolve().parents[1]
    work_root = Path(args.work_root)
    repo = Path(args.repo_dir) if args.repo_dir else work_root / "mathgraph_testdrive_repo"
    if args.fresh_clone and repo.exists():
        shutil.rmtree(repo)
    if not repo.exists():
        subprocess.run(["git", "clone", "--branch", args.repo_ref, args.repo_url, str(repo)], check=True)
    return repo.resolve()


def _python_env(repo: Path) -> dict[str, str]:
    env = dict(os.environ)
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo) if not current else str(repo) + os.pathsep + current
    return env


def _markdown(report: dict[str, object]) -> str:
    summary = report["summary"]
    lines = [
        "# MathGraph Colab / Local Test Drive",
        "",
        f"- Commit: `{summary['commit']}`",
        f"- Commands total: `{summary['command_total']}`",
        f"- Commands OK: `{summary['command_ok']}`",
        f"- Commands failed: `{summary['command_failed']}`",
        f"- Lean path: `{summary['lean_path']}`",
        f"- Verifier fixture boundaries: `{summary['verifier_fixture_boundary_count']}`",
        f"- Verified corpus entries: `{summary['verified_corpus_verified_count']}`",
        f"- Lean project verified entries: `{summary['lean_project_verified_count']}`",
        f"- Lean project dependency edges: `{summary['dependency_edge_count']}`",
        f"- Hardening criticals: `{summary['hardening_criticals']}`",
        f"- Roadmap criticals: `{summary['roadmap_criticals']}`",
        "",
        "This report is advisory unless it carries explicit verifier/importer/finite-validator/chain-audit boundary evidence.",
        "",
        "| command | ok | return code |",
        "| --- | --- | --- |",
    ]
    for command in report["commands"]:
        lines.append(f"| {command['name']} | {command['ok']} | {command['returncode']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    default_work = Path("/content") if Path("/content").exists() else Path("./tmp_colab_testdrive")
    p = argparse.ArgumentParser()
    p.add_argument("--repo-url", default="https://github.com/metalogiclabs/mathgraph.git")
    p.add_argument("--repo-ref", default="main")
    p.add_argument("--work-root", default=str(default_work))
    p.add_argument("--repo-dir")
    p.add_argument("--out-dir")
    p.add_argument("--fresh-clone", action="store_true")
    p.add_argument("--use-current-checkout", action="store_true")
    p.add_argument("--install-editable", action="store_true")
    p.add_argument("--run-full-pytest", action="store_true")
    p.add_argument("--allow-live-verifier", action="store_true")
    p.add_argument("--allow-missing-verifier", action="store_true")
    p.add_argument("--quick-smoke", action="store_true")
    p.add_argument("--timeout-sec", type=float, default=420.0)
    p.add_argument("--out-report-json")
    p.add_argument("--out-report-md")
    args = p.parse_args(argv)

    repo = _repo_root(args)
    out_dir = Path(args.out_dir or repo / "tmp_colab_testdrive_outputs").resolve()
    script_outputs = out_dir / "script_outputs"
    script_outputs.mkdir(parents=True, exist_ok=True)
    env = _python_env(repo)
    py = sys.executable
    commands: list[dict[str, object]] = []

    def add(name: str, argv_: list[str], output: str | None = None) -> dict[str, object]:
        rec = _run(argv_, cwd=repo, env=env, timeout=args.timeout_sec, name=name, output_path=(script_outputs / f"{name}.json"))
        commands.append(rec)
        return rec

    commit = add("git_rev_parse", ["git", "rev-parse", "HEAD"])["stdout_excerpt"].strip()
    add("git_status", ["git", "status", "--short"])
    if args.install_editable:
        add("install_editable", [py, "-m", "pip", "install", "-e", ".[dev]"])
    add("py_compile", [py, "-m", "py_compile", "mathgraph/version.py", "mathgraph/demo_release.py", "mathgraph/verifier_execution.py", "mathgraph/verifier_fixtures.py", "mathgraph/verified_corpus.py", "mathgraph/lean_project_subset.py"])
    if args.quick_smoke:
        fixture_path = script_outputs / "fixtures_dry.json"
        add("fixtures_dry", [py, "scripts/run_verifier_fixtures.py", "--ensure-fixtures", "--out-result-json", str(fixture_path)])
        roadmap_path = script_outputs / "roadmap.json"
        add("roadmap_alignment", [py, "scripts/run_roadmap_alignment.py", "--fail-on-critical", "--out-json", str(roadmap_path)])
    else:
        add("focused_pytest", [py, "-m", "pytest", "tests/test_verifier_execution.py", "tests/test_verifier_fixtures.py", "tests/test_verified_corpus.py", "tests/test_lean_project_subset.py", "tests/test_api_service.py", "tests/test_e2e_testdrive.py", "tests/test_hardening.py", "tests/test_public_terms.py"])
        add("fixtures_dry", [py, "scripts/run_verifier_fixtures.py", "--ensure-fixtures", "--out-result-json", str(script_outputs / "fixtures_dry.json")])
        add("corpus_dry", [py, "scripts/run_verified_corpus.py", "--ensure-micro-corpus", "--out-report-json", str(script_outputs / "corpus_dry.json")])
        add("project_dry", [py, "scripts/run_lean_project_subset.py", "--ensure-micro-project", "--out-report-json", str(script_outputs / "project_dry.json")])
        add("e2e_advisory", [py, "scripts/run_e2e_testdrive.py", "--out-report-json", str(script_outputs / "e2e_advisory.json")])
        add("hardening", [py, "scripts/run_hardening.py", "--out-report-json", str(script_outputs / "hardening.json")])
        add("roadmap_alignment", [py, "scripts/run_roadmap_alignment.py", "--fail-on-critical", "--out-json", str(script_outputs / "roadmap.json")])
        if args.allow_live_verifier:
            live_flag = ["--allow-missing-verifier"] if args.allow_missing_verifier else []
            add("fixtures_live", [py, "scripts/run_verifier_fixtures.py", "--allow-execution", *live_flag, "--out-result-json", str(script_outputs / "fixtures_live.json")])
            add("corpus_live", [py, "scripts/run_verified_corpus.py", "--allow-execution", *live_flag, "--out-report-json", str(script_outputs / "corpus_live.json")])
            add("project_live", [py, "scripts/run_lean_project_subset.py", "--allow-execution", *live_flag, "--out-report-json", str(script_outputs / "project_live.json")])
            add("e2e_live", [py, "scripts/run_e2e_testdrive.py", "--mode", "live-verifier", "--allow-execution", *live_flag, "--out-report-json", str(script_outputs / "e2e_live.json")])
        if args.run_full_pytest:
            add("full_pytest", [py, "-m", "pytest"])
    if args.quick_smoke and args.allow_live_verifier:
        live_flag = ["--allow-missing-verifier"] if args.allow_missing_verifier else []
        add("fixtures_live", [py, "scripts/run_verifier_fixtures.py", "--allow-execution", *live_flag, "--out-result-json", str(script_outputs / "fixtures_live.json")])

    fixture_live = _read_json(script_outputs / ("fixtures_live.json" if args.allow_live_verifier else "fixtures_dry.json"))
    corpus_live = _read_json(script_outputs / ("corpus_live.json" if (script_outputs / "corpus_live.json").exists() else "corpus_dry.json"))
    project_live = _read_json(script_outputs / ("project_live.json" if (script_outputs / "project_live.json").exists() else "project_dry.json"))
    hardening = _read_json(script_outputs / "hardening.json")
    roadmap = _read_json(script_outputs / "roadmap.json")
    lean_path = shutil.which("lean")
    summary = {
        "command_total": len(commands),
        "command_ok": sum(bool(x["ok"]) for x in commands),
        "command_failed": sum(not bool(x["ok"]) for x in commands),
        "lean_path": lean_path,
        "commit": commit,
        "verifier_fixture_boundary_count": fixture_live.get("summary", {}).get("boundary_evidence_total", 0),
        "verified_corpus_verified_count": corpus_live.get("summary", {}).get("verified_entry_total", 0),
        "lean_project_verified_count": project_live.get("summary", {}).get("verified_entry_total", 0),
        "dependency_edge_count": project_live.get("summary", {}).get("dependency_edge_total", 0),
        "hardening_criticals": hardening.get("summary", {}).get("critical_total", 0),
        "roadmap_criticals": roadmap.get("critical_count", 0),
        "advisory_only": True,
    }
    report = {"created_at": _now(), "repo_root": str(repo), "out_dir": str(out_dir), "commands": commands, "summary": summary}
    report_json = Path(args.out_report_json) if args.out_report_json else out_dir / "colab_testdrive_report.json"
    report_md = Path(args.out_report_md) if args.out_report_md else out_dir / "colab_testdrive_report.md"
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    report_md.write_text(_markdown(report), encoding="utf-8")
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")
    return 1 if summary["command_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
