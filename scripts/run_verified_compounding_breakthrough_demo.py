#!/usr/bin/env python3
"""Run the canonical V81 Verified Compounding Intelligence breakthrough demo."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mathgraph.breakthrough_lineage import historical_lineage_manifest, validate_historical_lineage

P81 = ROOT / "experiments" / "verified_compounding_breakthrough_v81" / "run.py"
S81 = importlib.util.spec_from_file_location("v81_breakthrough", P81)
if S81 is None or S81.loader is None:
    raise RuntimeError("cannot load V81 experiment")
V81 = importlib.util.module_from_spec(S81)
sys.modules[S81.name] = V81
S81.loader.exec_module(V81)

REQUIRED_OUTPUTS = (
    "breakthrough_manifest.json",
    "breakthrough_report.md",
    "capability_blocks.jsonl",
    "verified_obstructions.jsonl",
    "development_transitions.jsonl",
    "historical_evidence_validation.json",
    "v81_fresh_result.json",
    "compounding_economics.json",
    "claim_boundary.json",
    "artifact_hashes.json",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opened-laws", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--skip-remote-history", action="store_true", help="mark remote history unverified instead of querying GitHub")
    parser.add_argument("--skip-release-check", action="store_true", help="development-only diagnostic; final demo should not use")
    return parser


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _github_json(path: str, token: str | None) -> dict[str, Any]:
    url = f"https://api.github.com/repos/metalogiclabs/mathgraph/{path.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MathGraph-V81-breakthrough-demo",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_remote_history(*, skip: bool = False) -> dict[str, Any]:
    if skip:
        return {
            "status": "UNVERIFIED_IN_THIS_RUN",
            "reason": "remote validation explicitly skipped",
            "run_checks": [],
            "artifact_checks": [],
        }

    token = os.environ.get("GITHUB_TOKEN")
    lineage = historical_lineage_manifest()["stages"]
    run_checks: list[dict[str, Any]] = []
    artifact_checks: list[dict[str, Any]] = []
    errors: list[str] = []

    for stage in lineage:
        run_id = stage.get("run_id")
        if not run_id:
            continue
        try:
            run = _github_json(f"actions/runs/{run_id}", token)
            ok = run.get("status") == "completed" and run.get("conclusion") == "success"
            run_checks.append(
                {
                    "stage": stage["stage"],
                    "run_id": run_id,
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "head_sha": run.get("head_sha"),
                    "ok": ok,
                }
            )
            if not ok:
                errors.append(f"{stage['stage']}: workflow run not successful")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            run_checks.append({"stage": stage["stage"], "run_id": run_id, "ok": False, "error": str(exc)})
            errors.append(f"{stage['stage']}: run metadata unavailable")
            continue

        artifact_id = stage.get("artifact_id")
        if artifact_id:
            try:
                payload = _github_json(f"actions/runs/{run_id}/artifacts?per_page=100", token)
                match = next((a for a in payload.get("artifacts", []) if int(a.get("id", -1)) == int(artifact_id)), None)
                digest_ok = True
                expected_digest = stage.get("artifact_digest")
                if expected_digest:
                    digest_ok = bool(match and match.get("digest") == expected_digest)
                ok = bool(match and not match.get("expired", False) and digest_ok)
                artifact_checks.append(
                    {
                        "stage": stage["stage"],
                        "run_id": run_id,
                        "artifact_id": artifact_id,
                        "found": match is not None,
                        "expired": None if match is None else bool(match.get("expired", False)),
                        "digest": None if match is None else match.get("digest"),
                        "expected_digest": expected_digest,
                        "ok": ok,
                    }
                )
                if not ok:
                    errors.append(f"{stage['stage']}: authoritative artifact unavailable or digest mismatch")
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                artifact_checks.append(
                    {"stage": stage["stage"], "run_id": run_id, "artifact_id": artifact_id, "ok": False, "error": str(exc)}
                )
                errors.append(f"{stage['stage']}: artifact metadata unavailable")

    return {
        "status": "HISTORICAL_REMOTE_VALIDATED" if not errors else "UNVERIFIED_IN_THIS_RUN",
        "run_checks": run_checks,
        "artifact_checks": artifact_checks,
        "errors": errors,
    }


def run_trust_boundary(out_dir: Path, *, skip: bool = False) -> dict[str, Any]:
    if skip:
        return {"status": "UNVERIFIED_IN_THIS_RUN", "returncode": None, "skipped": True}
    report_path = out_dir / "release_check.json"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_release_check.py"),
        "--quick",
        "--include-trust-boundary",
        "--fail-on-critical",
        "--quiet",
        "--out-report-json",
        str(report_path),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    report = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {}
    return {
        "status": "TRUST_BOUNDARY_PASS" if completed.returncode == 0 else "TRUST_BOUNDARY_FAIL",
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-3000:],
        "stderr_tail": completed.stderr[-3000:],
        "report": report,
    }


def _render_report(manifest: dict[str, Any]) -> str:
    fresh = manifest["fresh_v81"]
    economics = manifest["compounding_economics"]
    lines = [
        "# V81 Verified Compounding Intelligence Breakthrough Demo",
        "",
        f"**Top-level verdict:** `{manifest['top_level_verdict']}`",
        "",
        "## What was demonstrated",
        "",
        f"- Trust boundary: `{manifest['verdicts']['trust_boundary']}`",
        f"- Historical evidence lineage: `{manifest['verdicts']['historical_lineage']}`",
        f"- Fresh developmental cycle: `{manifest['verdicts']['fresh_developmental_cycle']}`",
        f"- Autonomous reuse/expand: `{manifest['verdicts']['autonomous_reuse_expand']}`",
        f"- Exact global optimality: `{manifest['verdicts']['global_optimality']}`",
        f"- Compounding economics: `{manifest['verdicts']['compounding']}`",
        "",
        "## Fresh V81 prospective experiment",
        "",
        f"- Sources: {fresh['evaluation']['sources']} fresh ten-operation source laws",
        f"- Consequence horizons: 2 through {fresh['evaluation']['max_horizon']}",
        f"- Exact fixed-budget states enumerated: {fresh['evaluation']['total_states_enumerated']}",
        f"- Exact obstruction units exposed: {fresh['evaluation']['total_obstruction']}",
        f"- Obstruction units recovered: {fresh['evaluation']['total_recovered']}",
        f"- Reuse decisions: {fresh['evaluation']['reuse_decisions']}",
        f"- Verifier-only expansion decisions: {fresh['evaluation']['verifier_expansion_decisions']}",
        f"- Action-language expansions required: {fresh['evaluation']['action_language_expansion_required_count']}",
        f"- Protocol SHA256: `{fresh['protocol_sha256']}`",
        f"- Frozen developer SHA256: `{fresh['developer_sha256']}`",
        "",
        "## Compounding economics",
        "",
        f"- Aggregate cold verifier checks: {economics['aggregate_cold_checks']}",
        f"- Aggregate warm verifier checks: {economics['aggregate_warm_checks']}",
        f"- Aggregate check savings: {economics['aggregate_check_savings']}",
        f"- Exact causal saving comparisons: {economics['causal_saving_count']}",
        f"- Classification: `{economics['classification']}`",
        "",
        "Warm and cold paths use the same learned proposer, exact verifier, action language, and consequence graph. The warm path alone retains the previously admitted globally-certified state; the cold counterfactual deletes that state and restarts from the original baseline.",
        "",
        "## Historical/fresh distinction",
        "",
        "V66–V80 are authoritative historical evidence and are not relabeled as fresh V81 data. This run validates their repository contracts and GitHub run/artifact metadata. The ten-operation V81 stream is the new prospective evidence generated after the V81 protocol freeze.",
        "",
        "## Claim boundary",
        "",
        manifest["claim_boundary"]["bounded_claim"],
        "",
        "This demo does **not** claim AGI, universal self-improvement, unbounded adequacy, universal sufficiency of one-swap actions, or equivalence between synthetic equational transfer and arbitrary real-world intelligence.",
        "",
    ]
    return "\n".join(lines)


def _write_artifact_hashes(out_dir: Path) -> dict[str, Any]:
    hashes: dict[str, str] = {}
    for name in REQUIRED_OUTPUTS:
        if name == "artifact_hashes.json":
            continue
        path = out_dir / name
        if not path.exists():
            raise RuntimeError(f"required output missing before hashing: {name}")
        hashes[name] = _sha256_file(path)
    manifest_digest = hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload = {
        "schema": "mathgraph.breakthrough-artifact-hashes.v81",
        "sha256": hashes,
        "hash_set_digest": manifest_digest,
        "self_hash_policy": "artifact_hashes.json is excluded from its own hash set",
    }
    _json(out_dir / "artifact_hashes.json", payload)
    return payload


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    trust = run_trust_boundary(out_dir, skip=args.skip_release_check)
    local_history = validate_historical_lineage(ROOT)
    remote_history = validate_remote_history(skip=args.skip_remote_history)
    historical = {
        "schema": "mathgraph.breakthrough-historical-evidence-validation.v81",
        "local": local_history,
        "remote": remote_history,
        "status": (
            "HISTORICAL_LINEAGE_VALIDATED"
            if local_history["repo_local_files_ok"] and remote_history["status"] == "HISTORICAL_REMOTE_VALIDATED"
            else "UNVERIFIED_IN_THIS_RUN"
        ),
        "historical_data_reused_as_fresh": False,
    }
    _json(out_dir / "historical_evidence_validation.json", historical)

    fresh = V81.run_v81(Path(args.opened_laws), out_dir, quick=bool(args.quick))
    economics = json.loads((out_dir / "compounding_economics.json").read_text(encoding="utf-8"))

    claim_boundary = {
        "schema": "mathgraph.breakthrough-claim-boundary.v81",
        "bounded_claim": (
            "A verifier-gated developmental system converted replay-verified structure into persistent reusable capability, "
            "certified exact fixed-budget sufficiency, emitted exact obstructions under lawful consequence extensions, "
            "admitted only strictly improving repairs, autonomously chose reuse versus verifier-only expansion, and tested "
            "whether retained admitted capability reduced verifier work to later equally globally-certified endpoints."
        ),
        "non_claims": [
            "AGI",
            "universal self-improvement",
            "unbounded adequacy",
            "universal one-swap sufficiency",
            "synthetic transfer equals arbitrary natural-world transfer",
            "advisory memory verifies truth",
        ],
    }
    _json(out_dir / "claim_boundary.json", claim_boundary)

    verdicts = {
        "trust_boundary": trust["status"],
        "historical_lineage": historical["status"],
        "fresh_developmental_cycle": (
            "FRESH_DEVELOPMENTAL_CYCLE_PASS" if fresh["fresh_developmental_cycle_pass"] else "FRESH_DEVELOPMENTAL_CYCLE_FAIL"
        ),
        "autonomous_reuse_expand": (
            "AUTONOMOUS_REUSE_EXPAND_PASS" if fresh["autonomous_reuse_expand_pass"] else "AUTONOMOUS_REUSE_EXPAND_FAIL"
        ),
        "global_optimality": (
            "GLOBAL_OPTIMALITY_GATES_PASS" if fresh["global_optimality_gates_pass"] else "GLOBAL_OPTIMALITY_GATES_FAIL"
        ),
        "compounding": economics["classification"],
    }

    mandatory_development = all(
        [
            verdicts["trust_boundary"] == "TRUST_BOUNDARY_PASS",
            verdicts["historical_lineage"] == "HISTORICAL_LINEAGE_VALIDATED",
            verdicts["fresh_developmental_cycle"] == "FRESH_DEVELOPMENTAL_CYCLE_PASS",
            verdicts["autonomous_reuse_expand"] == "AUTONOMOUS_REUSE_EXPAND_PASS",
            verdicts["global_optimality"] == "GLOBAL_OPTIMALITY_GATES_PASS",
        ]
    )
    if mandatory_development and economics["classification"] == "VERIFIED_COMPOUNDING_SIGNAL":
        top = "PASS_VERIFIED_COMPOUNDING_INTELLIGENCE_BREAKTHROUGH_DEMO_V81"
    elif mandatory_development and economics["classification"] == "ACCUMULATION_ONLY":
        top = "PASS_VERIFIED_DEVELOPMENT_DEMO_V81_ACCUMULATION_ONLY"
    else:
        top = "FAIL_VERIFIED_COMPOUNDING_BREAKTHROUGH_DEMO_V81"

    manifest = {
        "schema": "mathgraph.verified-compounding-breakthrough-demo.v81",
        "top_level_verdict": top,
        "verdicts": verdicts,
        "trust_boundary": trust,
        "historical_validation": historical,
        "fresh_v81": fresh,
        "compounding_economics": economics,
        "claim_boundary": claim_boundary,
        "required_outputs": list(REQUIRED_OUTPUTS),
    }
    _json(out_dir / "breakthrough_manifest.json", manifest)
    (out_dir / "breakthrough_report.md").write_text(_render_report(manifest), encoding="utf-8")

    hashes = _write_artifact_hashes(out_dir)
    manifest["artifact_hash_set_digest"] = hashes["hash_set_digest"]
    _json(out_dir / "breakthrough_manifest.json", manifest)
    # Manifest changed after recording the hash-set digest, so refresh its hash
    # and rewrite the independent hash set once. The hash file remains excluded.
    _write_artifact_hashes(out_dir)

    print(
        json.dumps(
            {
                "top_level_verdict": top,
                "verdicts": verdicts,
                "fresh_protocol_sha256": fresh["protocol_sha256"],
                "developer_sha256": fresh["developer_sha256"],
                "fresh_sources": fresh["evaluation"]["sources"],
                "states_enumerated": fresh["evaluation"]["total_states_enumerated"],
                "obstruction": fresh["evaluation"]["total_obstruction"],
                "recovered": fresh["evaluation"]["total_recovered"],
                "reuse_decisions": fresh["evaluation"]["reuse_decisions"],
                "verifier_expansions": fresh["evaluation"]["verifier_expansion_decisions"],
                "action_expansions": fresh["evaluation"]["action_language_expansion_required_count"],
                "compounding": economics,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = run_demo(args)
    top = manifest["top_level_verdict"]
    if top in {
        "PASS_VERIFIED_COMPOUNDING_INTELLIGENCE_BREAKTHROUGH_DEMO_V81",
        "PASS_VERIFIED_DEVELOPMENT_DEMO_V81_ACCUMULATION_ONLY",
    }:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
