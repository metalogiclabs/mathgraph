from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.36"
ROOT = Path("artifacts/sorrydb/direct_diagnostic_v4_4_36")
DIAG = ROOT / "diagnostic.json"

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def classify(text: str) -> tuple[str, list[str], str]:
    low = text.lower()
    reasons = []

    if "unknown module prefix 'equational_theories'" in low:
        reasons.append("target replay failed because local project library prefix was not built into .lake/build/lib/lean")
    if "no directory 'equational_theories' or file 'equational_theories.olean'" in low:
        reasons.append("Lean search path lacks equational_theories.olean")
    if "lake exe cache get" in low or "downloaded: 8232" in low:
        reasons.append("dependency cache completed, but project-local olean was still missing")
    if "type mismatch" in low or "application type mismatch" in low or "failed to synthesize" in low:
        reasons.append("proof/type error evidence present")

    if any("proof/type" in r for r in reasons):
        return "PROOF_OR_TYPE_REJECTION", reasons, "mine exact Lean error"
    if any("local project library prefix" in r for r in reasons):
        return "LOCAL_PROJECT_OLEAN_NOT_BUILT", reasons, "run targeted lake build for equational_theories.Definability.Law43 or its local library before replay"
    return "UNCLASSIFIED", reasons or ["no known obstruction signature"], "run clearer diagnostic"

def main() -> None:
    if not DIAG.exists():
        raise SystemExit(f"missing {DIAG}")

    diag = load_json(DIAG)
    combined = "\n".join(
        (step.get("stdout_tail", "") + "\n" + step.get("stderr_tail", ""))
        for step in diag
    )

    target_step = diag[-1]
    obstruction_class, reasons, next_action = classify(combined)

    summary = {
        "version": VERSION,
        "status": "DIRECT_DIAGNOSTIC_LEDGERED",
        "input_version": "v4.4.35",
        "repo": "teorth/equational_theories",
        "target_path": "equational_theories/Definability/Law43.lean",
        "selected_patch_id": "patch-001-exact-constructor-four-fields",
        "cache_get_ok": any(step["cmd"] == ["lake", "exe", "cache", "get"] and step["ok"] for step in diag),
        "target_replay_ok": target_step["ok"],
        "target_replay_returncode": target_step["returncode"],
        "target_replay_seconds": target_step["seconds"],
        "obstruction_class": obstruction_class,
        "proof_patch_dead": False,
        "upstream_contact_performed": False,
        "next_action": next_action,
        "bounded_claim": [
            "v4.4.36 records the direct dependency-aware diagnostic run",
            "it identifies the failure as local project olean/module setup, not proof rejection",
            "it keeps the selected patch alive until a target build/replay reaches proof checking",
        ],
        "does_not_claim": [
            "patch acceptance",
            "proof rejection",
            "upstream acceptance",
            "automated external contact",
            "full repository build success",
        ],
    }

    ledger = {
        **summary,
        "diagnostic_steps": diag,
        "obstruction_reasons": reasons,
    }

    report = f"""# SorryDB v4.4.36 — Direct Diagnostic

## Result

- repo: teorth/equational_theories
- target path: equational_theories/Definability/Law43.lean
- selected patch: patch-001-exact-constructor-four-fields
- cache get ok: {summary['cache_get_ok']}
- target replay ok: {summary['target_replay_ok']}
- target replay returncode: {summary['target_replay_returncode']}
- obstruction class: {obstruction_class}
- proof patch dead: false
- upstream contact performed: false

## Obstruction reasons

{chr(10).join("- " + r for r in reasons)}

## Interpretation

The patch has not reached a clean proof/type judgment. `lake exe cache get` succeeded, but `lake env lean equational_theories/Definability/Law43.lean` failed because the local project module prefix `equational_theories` was not built into the local search path as an `.olean`.

## Next action

Run a targeted Lake build/replay path that builds the local project module first, then replay the same patch.

## Boundary

No upstream modification or maintainer contact was performed.
"""

    write_json(ROOT / "summary.json", summary)
    write_json(ROOT / "direct_diagnostic_ledger.json", ledger)
    (ROOT / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
