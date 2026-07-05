from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VERSION = "v4.4.28"
OUT = Path("artifacts/sorrydb/attempt002_snippet_inspection_v4_4_28")
RAW_FILES = OUT / "raw_files"

INPUTS = {
    "source_scout_summary": Path("artifacts/sorrydb/attempt002_source_scout_v4_4_27/summary.json"),
    "source_scout": Path("artifacts/sorrydb/attempt002_source_scout_v4_4_27/source_scout.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def endpoint_from_api_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    if parsed.netloc == "api.github.com":
        endpoint = parsed.path
        if parsed.query:
            endpoint += "?" + parsed.query
        return endpoint
    return api_url

def fetch_content(candidate: dict[str, Any]) -> tuple[bool, str, str]:
    cid = candidate["candidate_id"]
    cache_path = RAW_FILES / f"{cid}.lean"

    if cache_path.exists():
        return True, cache_path.read_text(encoding="utf-8", errors="replace"), "CACHED_FILE_REUSED"

    api_url = candidate.get("api_url") or candidate.get("url")
    if not api_url:
        return False, "", "NO_API_URL"

    endpoint = endpoint_from_api_url(api_url)
    p = subprocess.run(
        ["gh", "api", endpoint],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        return False, p.stderr.strip(), "GH_API_FETCH_FAILED"

    data = json.loads(p.stdout)
    encoded = data.get("content", "")
    encoding = data.get("encoding", "")
    if encoding != "base64" or not encoded:
        return False, p.stdout, "UNSUPPORTED_CONTENT_ENCODING"

    text = base64.b64decode(encoded.encode()).decode("utf-8", errors="replace")
    RAW_FILES.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    return True, text, "LIVE_FETCH_CACHED"

def sorry_windows(text: str, radius: int = 4) -> list[dict[str, Any]]:
    lines = text.splitlines()
    windows = []
    for i, line in enumerate(lines):
        if "sorry" not in line:
            continue
        start = max(0, i - radius)
        end = min(len(lines), i + radius + 1)
        windows.append(
            {
                "line_number": i + 1,
                "line": line,
                "window_start": start + 1,
                "window_end": end,
                "snippet": "\n".join(f"{j+1}: {lines[j]}" for j in range(start, end)),
            }
        )
    return windows

def candidate_replay_score(candidate: dict[str, Any], text: str, windows: list[dict[str, Any]]) -> tuple[int, list[str]]:
    lines = text.splitlines()
    score = 0
    reasons: list[str] = []

    sorry_count = len(windows)
    line_count = len(lines)
    lower = text.lower()

    if sorry_count == 1:
        score += 10
        reasons.append("single sorry")
    elif 2 <= sorry_count <= 3:
        score += 6
        reasons.append("few sorries")
    else:
        score -= min(sorry_count, 10)
        reasons.append("many sorries")

    if line_count <= 120:
        score += 5
        reasons.append("small file")
    elif line_count <= 300:
        score += 3
        reasons.append("medium file")
    else:
        score -= 2
        reasons.append("large file")

    if "example" in lower:
        score += 4
        reasons.append("example context")
    if "theorem" in lower:
        score += 2
        reasons.append("theorem context")
    if "nat" in lower:
        score += 2
        reasons.append("nat context")
    if "simp" in lower:
        score += 1
        reasons.append("simp visible")
    if "begin" in lower and "end" in lower:
        score -= 2
        reasons.append("lean3 tactic block likely")
    if "sorry" in candidate.get("path", "").lower():
        score -= 1
        reasons.append("path name includes sorry")

    return score, reasons

def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)
    RAW_FILES.mkdir(parents=True, exist_ok=True)

    scout_summary = load_json(INPUTS["source_scout_summary"])
    scout = load_json(INPUTS["source_scout"])

    top_candidates = scout.get("top_candidates", [])
    inspections: list[dict[str, Any]] = []

    for candidate in top_candidates:
        ok, content_or_error, fetch_status = fetch_content(candidate)
        if not ok:
            inspections.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "repo": candidate["repo"],
                    "path": candidate["path"],
                    "html_url": candidate["html_url"],
                    "fetch_ok": False,
                    "fetch_status": fetch_status,
                    "error": content_or_error[:1000],
                    "sorry_count": 0,
                    "line_count": 0,
                    "windows": [],
                    "replay_selection_score": -999,
                    "score_reasons": ["fetch failed"],
                    "status": "INSPECTION_FETCH_FAILED",
                }
            )
            continue

        text = content_or_error
        windows = sorry_windows(text)
        replay_score, reasons = candidate_replay_score(candidate, text, windows)
        inspections.append(
            {
                "candidate_id": candidate["candidate_id"],
                "repo": candidate["repo"],
                "path": candidate["path"],
                "html_url": candidate["html_url"],
                "fetch_ok": True,
                "fetch_status": fetch_status,
                "sorry_count": len(windows),
                "line_count": len(text.splitlines()),
                "windows": windows[:10],
                "replay_selection_score": replay_score,
                "score_reasons": reasons,
                "status": "EXACT_SOURCE_SNIPPETS_INSPECTED_NOT_REPLAYED",
            }
        )

    inspections.sort(key=lambda x: (-x["replay_selection_score"], x["repo"], x["path"]))

    selected = inspections[0] if inspections and inspections[0]["fetch_ok"] and inspections[0]["sorry_count"] > 0 else None

    inspection = {
        "version": VERSION,
        "inspection_type": "ATTEMPT002_TOP_CANDIDATE_SNIPPET_INSPECTION",
        "input_version": scout_summary.get("version"),
        "inspected_candidate_count": len(inspections),
        "fetch_ok_count": sum(1 for x in inspections if x["fetch_ok"]),
        "candidate_with_sorry_count": sum(1 for x in inspections if x["sorry_count"] > 0),
        "selected_candidate": selected,
        "inspections": inspections,
        "constraints": {
            "no_clone": True,
            "no_lean_replay": True,
            "no_upstream_contact": True,
            "no_heavy_build": True,
            "exact_source_inspection_only": True,
        },
    }

    summary = {
        "version": VERSION,
        "status": "ATTEMPT002_SNIPPET_INSPECTION_LEDGERED",
        "input_version": scout_summary.get("version"),
        "inspected_candidate_count": inspection["inspected_candidate_count"],
        "fetch_ok_count": inspection["fetch_ok_count"],
        "candidate_with_sorry_count": inspection["candidate_with_sorry_count"],
        "selected_candidate_id": selected["candidate_id"] if selected else "",
        "selected_repo": selected["repo"] if selected else "",
        "selected_path": selected["path"] if selected else "",
        "selected_sorry_count": selected["sorry_count"] if selected else 0,
        "selected_replay_selection_score": selected["replay_selection_score"] if selected else None,
        "clone_attempted": False,
        "replay_attempted": False,
        "upstream_contact_performed": False,
        "bounded_claim": [
            "v4.4.28 inspects exact source snippets from the v4.4.27 top candidates",
            "it selects one candidate for possible future replay based on simple source-shape heuristics",
            "it does not clone, replay Lean, modify upstream, or contact maintainers",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "candidate repairability",
            "that selected source will replay locally",
            "that the selected repo is active",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.29 clone only the selected attempt002 candidate repo into a bounded temp directory and run source/Lean-version reconnaissance before replay",
    }

    report_lines = [
        "# SorryDB v4.4.28 — Attempt 002 Snippet Inspection",
        "",
        "## Result",
        "",
        f"- inspected candidate count: {inspection['inspected_candidate_count']}",
        f"- fetch ok count: {inspection['fetch_ok_count']}",
        f"- candidate with sorry count: {inspection['candidate_with_sorry_count']}",
        f"- selected candidate: {summary['selected_candidate_id'] or '(none)'}",
        f"- selected repo: {summary['selected_repo'] or '(none)'}",
        f"- selected path: {summary['selected_path'] or '(none)'}",
        f"- replay attempted: false",
        "",
        "## Selected candidate",
        "",
    ]

    if selected:
        report_lines.extend(
            [
                f"- candidate id: {selected['candidate_id']}",
                f"- repo: {selected['repo']}",
                f"- path: {selected['path']}",
                f"- url: {selected['html_url']}",
                f"- sorry count: {selected['sorry_count']}",
                f"- line count: {selected['line_count']}",
                f"- replay selection score: {selected['replay_selection_score']}",
                f"- reasons: {', '.join(selected['score_reasons'])}",
                "",
                "## First sorry window",
                "",
                selected["windows"][0]["snippet"] if selected["windows"] else "(none)",
                "",
            ]
        )
    else:
        report_lines.append("No candidate selected.")

    report_lines.extend(
        [
            "## Boundary",
            "",
            "No clone, Lean replay, upstream modification, or maintainer contact was performed.",
            "",
            "## Next frontier",
            "",
            "Clone only the selected repo into a bounded temp directory and run source/Lean-version reconnaissance before replay.",
            "",
        ]
    )

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "snippet_inspection.json", inspection)
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
