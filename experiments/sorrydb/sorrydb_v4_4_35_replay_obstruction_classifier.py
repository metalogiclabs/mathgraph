from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.35"
OUT = Path("artifacts/sorrydb/replay_obstruction_classifier_v4_4_35")

INPUTS = {
    "replay_summary": Path("artifacts/sorrydb/bounded_replay_v4_4_34/summary.json"),
    "replay_result": Path("artifacts/sorrydb/bounded_replay_v4_4_34/bounded_replay_result.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def classify(stderr: str, stdout: str, replay_status: str) -> tuple[str, list[str], str]:
    text = (stderr + "\n" + stdout).lower()
    reasons = []

    if "cloning https://github.com" in text and "error:" not in text:
        reasons.append("stderr shows dependency acquisition/bootstrap logs, not a Lean type error")
    if "downloading https://releases.lean-lang.org" in text:
        reasons.append("Lean toolchain installation occurred during replay")
    if "mathlib: cloning" in text:
        reasons.append("mathlib dependency clone occurred during replay")
    if "unknown module" in text or "object file" in text or "olean" in text:
        reasons.append("module/olean availability obstruction")
    if "type mismatch" in text or "application type mismatch" in text:
        reasons.append("type mismatch evidence present")
    if "unknown identifier" in text:
        reasons.append("unknown identifier evidence present")
    if "failed to synthesize" in text:
        reasons.append("typeclass synthesis evidence present")
    if "error:" in text:
        reasons.append("Lean error marker present")
    if replay_status == "TIMEOUT":
        reasons.append("prior replay timed out")

    has_proof_error = any(
        x in text for x in [
            "type mismatch",
            "application type mismatch",
            "unknown identifier",
            "failed to synthesize",
            "unsolved goals",
        ]
    )
    has_bootstrap = any(
        x in text for x in [
            "downloading https://releases.lean-lang.org",
            "mathlib: cloning",
            "checking out revision",
            "cloning https://github.com",
        ]
    )

    if has_bootstrap and not has_proof_error:
        return "DEPENDENCY_BOOTSTRAP_INCOMPLETE_NOT_PROOF_REJECTION", reasons, "RUN_CACHE_OR_BUILD_DIAGNOSTIC_BEFORE_PATCH_JUDGMENT"
    if has_proof_error:
        return "LEAN_PROOF_OR_TYPE_OBSTRUCTION", reasons, "MINE_ERROR_AND_TRY_NEXT_PATCH_OR_REPAIR"
    if replay_status.startswith("ACCEPTED"):
        return "LOCAL_REPLAY_ACCEPTED", reasons, "PACKAGE_UPSTREAM_PATCH"
    return "UNCLASSIFIED_REPLAY_OBSTRUCTION", reasons, "RUN_STRICTER_DIAGNOSTIC"

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)

    replay_summary = load_json(INPUTS["replay_summary"])
    replay_result = load_json(INPUTS["replay_result"])
    step = replay_result.get("replay_step", {})
    stderr = step.get("stderr", "")
    stdout = step.get("stdout", "")
    status = replay_result.get("replay_status", "")

    obstruction_class, reasons, next_action = classify(stderr, stdout, status)

    ledger = {
        "version": VERSION,
        "classifier_type": "REPLAY_OBSTRUCTION_CLASSIFIER",
        "input_version": replay_summary.get("version"),
        "repo": replay_result.get("repo"),
        "commit": replay_result.get("commit"),
        "target_path": replay_result.get("target_path"),
        "selected_patch_id": replay_result.get("selected_patch_id"),
        "prior_replay_status": status,
        "prior_replay_reasons": replay_result.get("replay_reasons", []),
        "obstruction_class": obstruction_class,
        "obstruction_reasons": reasons,
        "next_action": next_action,
        "proof_patch_dead": False,
        "upstream_contact_performed": False,
        "rerun_performed": False,
        "bounded_claim": [
            "v4.4.35 classifies the v4.4.34 replay failure without rerunning Lean",
            "it separates dependency/bootstrap obstruction from proof/type obstruction",
            "it prevents incorrectly marking the selected patch dead from setup-only evidence",
        ],
        "does_not_claim": [
            "new Lean replay",
            "patch acceptance",
            "proof rejection",
            "full repository build",
            "upstream acceptance",
            "automated external contact",
        ],
    }

    summary = {
        "version": VERSION,
        "status": "REPLAY_OBSTRUCTION_CLASSIFIED",
        "input_version": replay_summary.get("version"),
        "repo": replay_result.get("repo"),
        "target_path": replay_result.get("target_path"),
        "selected_patch_id": replay_result.get("selected_patch_id"),
        "prior_replay_status": status,
        "obstruction_class": obstruction_class,
        "proof_patch_dead": False,
        "rerun_performed": False,
        "upstream_contact_performed": False,
        "next_action": next_action,
        "bounded_claim": ledger["bounded_claim"],
        "does_not_claim": ledger["does_not_claim"],
        "next_frontier": "v4.4.36 run a dependency-aware cache/build diagnostic, then replay the same patch only if the environment is ready",
    }

    report = f"""# SorryDB v4.4.35 — Replay Obstruction Classifier

## Result

- repo: {ledger['repo']}
- target path: {ledger['target_path']}
- selected patch: {ledger['selected_patch_id']}
- prior replay status: {status}
- obstruction class: {obstruction_class}
- proof patch dead: false
- rerun performed: false
- upstream contact performed: false
- next action: {next_action}

## Obstruction reasons

{chr(10).join("- " + r for r in reasons)}

## Interpretation

The v4.4.34 result should not be treated as a clean proof/type rejection. The stderr tail mostly shows toolchain and dependency acquisition. The patch remains unjudged until the repo environment is made replay-ready or a clearer Lean error is captured.

## Boundary

No Lean rerun, build, upstream modification, or maintainer contact was performed.
"""

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "replay_obstruction_classifier.json", ledger)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
