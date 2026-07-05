from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.31"
OUT = Path("artifacts/sorrydb/commented_sorry_filter_v4_4_31")

INPUTS = {
    "lowrisk_summary": Path("artifacts/sorrydb/lowrisk_lean4_scout_v4_4_30/summary.json"),
    "lowrisk_scout": Path("artifacts/sorrydb/lowrisk_lean4_scout_v4_4_30/lowrisk_lean4_scout.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def is_comment_only_sorry(window: dict[str, Any]) -> bool:
    line = window.get("line", "").strip()
    return line.startswith("--") or line.startswith("/-") or line.endswith("-/")

def active_sorry_count(candidate: dict[str, Any]) -> int:
    return sum(1 for w in candidate.get("windows", []) if not is_comment_only_sorry(w))

def score_active_candidate(candidate: dict[str, Any]) -> tuple[int, list[str]]:
    base = int(candidate.get("score", 0))
    active = active_sorry_count(candidate)
    total = int(candidate.get("sorry_count", 0))
    reasons = list(candidate.get("score_reasons", []))

    if active == 0:
        return -999, reasons + ["only commented sorry; not replay target"]

    score = base + 20
    reasons.append("has active sorry")

    if active == 1:
        score += 10
        reasons.append("single active sorry")
    else:
        score -= active * 2
        reasons.append("multiple active sorries")

    if total != active:
        score -= 5
        reasons.append("mixed active/commented sorry lines")

    return score, reasons

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    lowrisk_summary = load_json(INPUTS["lowrisk_summary"])
    scout = load_json(INPUTS["lowrisk_scout"])

    inspected = scout.get("inspected_candidates", [])
    evaluated = []
    for c in inspected:
        active = active_sorry_count(c)
        total = int(c.get("sorry_count", 0))
        replay_score, replay_reasons = score_active_candidate(c)
        status = "ACTIVE_SORRY_REPLAY_CANDIDATE" if active > 0 else "PARKED_COMMENTED_SORRY_ONLY"

        evaluated.append(
            {
                "candidate_id": c.get("candidate_id"),
                "repo": c.get("repo"),
                "path": c.get("path"),
                "html_url": c.get("html_url"),
                "original_score": c.get("score"),
                "active_replay_score": replay_score,
                "total_sorry_count": total,
                "active_sorry_count": active,
                "commented_sorry_count": total - active,
                "status": status,
                "score_reasons": replay_reasons,
                "windows": c.get("windows", [])[:5],
            }
        )

    evaluated.sort(key=lambda x: (-x["active_replay_score"], x["repo"] or "", x["path"] or ""))
    active_candidates = [x for x in evaluated if x["active_sorry_count"] > 0]
    parked = [x for x in evaluated if x["active_sorry_count"] == 0]
    selected = active_candidates[0] if active_candidates else None

    previous_selected = scout.get("selected_candidate") or {}
    previous_selected_id = previous_selected.get("candidate_id", "")
    previous_active = active_sorry_count(previous_selected) if previous_selected else 0

    ledger = {
        "version": VERSION,
        "filter_type": "COMMENTED_SORRY_FILTER_AND_ACTIVE_TARGET_RESELECTOR",
        "input_version": lowrisk_summary.get("version"),
        "previous_selected_candidate_id": previous_selected_id,
        "previous_selected_repo": previous_selected.get("repo", ""),
        "previous_selected_path": previous_selected.get("path", ""),
        "previous_selected_active_sorry_count": previous_active,
        "previous_selected_status": "PARKED_COMMENTED_SORRY_ONLY" if previous_active == 0 else "ACTIVE_SORRY_REPLAY_CANDIDATE",
        "evaluated_candidate_count": len(evaluated),
        "active_candidate_count": len(active_candidates),
        "parked_comment_only_count": len(parked),
        "selected_candidate": selected,
        "evaluated_candidates": evaluated,
        "constraints": {
            "no_clone": True,
            "no_build": True,
            "no_lean_replay": True,
            "no_upstream_contact": True,
            "cached_source_only": True,
        },
    }

    summary = {
        "version": VERSION,
        "status": "COMMENTED_SORRY_FILTER_LEDGERED",
        "input_version": lowrisk_summary.get("version"),
        "previous_selected_candidate_id": previous_selected_id,
        "previous_selected_repo": previous_selected.get("repo", ""),
        "previous_selected_path": previous_selected.get("path", ""),
        "previous_selected_status": ledger["previous_selected_status"],
        "evaluated_candidate_count": len(evaluated),
        "active_candidate_count": len(active_candidates),
        "parked_comment_only_count": len(parked),
        "selected_candidate_id": selected["candidate_id"] if selected else "",
        "selected_repo": selected["repo"] if selected else "",
        "selected_path": selected["path"] if selected else "",
        "selected_active_replay_score": selected["active_replay_score"] if selected else None,
        "clone_attempted": False,
        "build_attempted": False,
        "replay_attempted": False,
        "upstream_contact_performed": False,
        "bounded_claim": [
            "v4.4.31 detects that the v4.4.30 selected sorry is commented out and parks it",
            "it re-ranks cached low-risk candidates by active non-comment sorry lines only",
            "it selects the next active-sorry candidate without cloning, building, replaying, or contacting upstream",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "candidate repairability",
            "that the selected repo builds locally",
            "that selected source still matches after clone",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.32 clone only the selected active-sorry candidate into a bounded temp directory and run manifest/source reconnaissance before replay",
    }

    report_lines = [
        "# SorryDB v4.4.31 — Commented Sorry Filter",
        "",
        "## Result",
        "",
        f"- previous selected candidate: {previous_selected_id}",
        f"- previous selected repo: {previous_selected.get('repo', '')}",
        f"- previous selected path: {previous_selected.get('path', '')}",
        f"- previous selected status: {ledger['previous_selected_status']}",
        f"- evaluated candidate count: {len(evaluated)}",
        f"- active candidate count: {len(active_candidates)}",
        f"- parked comment-only count: {len(parked)}",
        f"- selected candidate: {summary['selected_candidate_id'] or '(none)'}",
        f"- selected repo: {summary['selected_repo'] or '(none)'}",
        f"- selected path: {summary['selected_path'] or '(none)'}",
        "",
    ]

    if selected:
        report_lines.extend([
            "## Selected active candidate",
            "",
            f"- candidate id: {selected['candidate_id']}",
            f"- repo: {selected['repo']}",
            f"- path: {selected['path']}",
            f"- url: {selected['html_url']}",
            f"- active replay score: {selected['active_replay_score']}",
            f"- active sorry count: {selected['active_sorry_count']}",
            f"- total sorry count: {selected['total_sorry_count']}",
            f"- reasons: {', '.join(selected['score_reasons'])}",
            "",
            "## First active sorry window",
            "",
        ])
        active_windows = [w for w in selected["windows"] if not is_comment_only_sorry(w)]
        report_lines.append(active_windows[0]["snippet"] if active_windows else "(none)")
        report_lines.append("")

    report_lines.extend([
        "## Boundary",
        "",
        "No clone, Lean build, Lean replay, upstream modification, or maintainer contact was performed.",
        "",
        "## Next frontier",
        "",
        "Clone only the selected active-sorry candidate into a bounded temp directory and run manifest/source reconnaissance before replay.",
        "",
    ])

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "commented_sorry_filter.json", ledger)
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
