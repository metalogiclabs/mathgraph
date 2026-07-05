from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.27"
OUT = Path("artifacts/sorrydb/attempt002_source_scout_v4_4_27")
RAW = OUT / "raw_github_code_search.json"

QUERIES = [
    'sorry language:Lean extension:lean "example"',
    'sorry language:Lean extension:lean "theorem"',
    'sorry language:Lean extension:lean "by"',
    'sorry language:Lean extension:lean "Nat"',
    'sorry language:Lean extension:lean "simp"',
]

EXCLUDE_REPOS = {
    "metalogiclabs/mathgraph",
    "leanprover-community/mathlib4",
    "leanprover/lean4",
}

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run_gh_search(query: str) -> dict[str, Any]:
    cmd = [
        "gh", "api",
        "--method", "GET",
        "-H", "Accept: application/vnd.github+json",
        "/search/code",
        "-f", f"q={query}",
        "-f", "per_page=20",
    ]
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return {
            "query": query,
            "ok": False,
            "error": p.stderr.strip(),
            "items": [],
        }
    data = json.loads(p.stdout)
    return {
        "query": query,
        "ok": True,
        "total_count": data.get("total_count"),
        "incomplete_results": data.get("incomplete_results"),
        "items": data.get("items", []),
    }

def score_item(item: dict[str, Any]) -> tuple[int, list[str]]:
    repo = item.get("repository", {}).get("full_name", "")
    path = item.get("path", "")
    name = item.get("name", "")
    html_url = item.get("html_url", "")

    score = 0
    reasons: list[str] = []

    if repo not in EXCLUDE_REPOS:
        score += 5
        reasons.append("not excluded repo")
    if path.endswith(".lean"):
        score += 3
        reasons.append("lean file")
    if any(x in path.lower() for x in ["example", "examples", "tutorial", "test", "scratch"]):
        score += 4
        reasons.append("educational/test/example path")
    if any(x in path.lower() for x in ["archive", "deprecated", "old"]):
        score -= 2
        reasons.append("possibly stale path")
    if "mathlib" in repo.lower():
        score -= 4
        reasons.append("mathlib-like repo avoided for now")
    if "lake-packages" in html_url or ".lake" in html_url:
        score -= 5
        reasons.append("dependency cache path avoided")
    if name.endswith(".lean"):
        score += 1
        reasons.append("lean filename")

    return score, reasons

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    if RAW.exists():
        raw = json.loads(RAW.read_text(encoding="utf-8"))
    else:
        raw = {
            "version": VERSION,
            "queries": QUERIES,
            "results": [run_gh_search(q) for q in QUERIES],
        }
        write_json(RAW, raw)

    source_mode = "CACHED_RAW_SEARCH_REUSED"

    seen: set[tuple[str, str]] = set()
    candidates: list[dict[str, Any]] = []

    for result in raw.get("results", []):
        for item in result.get("items", []):
            repo = item.get("repository", {}).get("full_name", "")
            path = item.get("path", "")
            key = (repo, path)
            if key in seen:
                continue
            seen.add(key)

            score, reasons = score_item(item)
            candidates.append(
                {
                    "candidate_id": f"attempt002-candidate-{len(candidates)+1:03d}",
                    "repo": repo,
                    "path": path,
                    "name": item.get("name"),
                    "html_url": item.get("html_url"),
                    "api_url": item.get("url"),
                    "score": score,
                    "score_reasons": reasons,
                    "query_source": result.get("query"),
                    "status": "SCOUTED_NOT_CLONED_NOT_REPLAYED",
                    "next_action": "inspect exact source snippet before any clone or replay",
                }
            )

    candidates.sort(key=lambda x: (-x["score"], x["repo"], x["path"]))
    selected = candidates[:20]
    top5 = selected[:5]

    scout = {
        "version": VERSION,
        "scout_type": "ATTEMPT002_SOURCE_SCOUT",
        "source_mode": source_mode,
        "query_count": len(QUERIES),
        "raw_result_count": sum(len(r.get("items", [])) for r in raw.get("results", [])),
        "unique_candidate_count": len(candidates),
        "selected_candidate_count": len(selected),
        "top_candidate_count": len(top5),
        "selected_candidates": selected,
        "top_candidates": top5,
        "constraints": {
            "no_clone": True,
            "no_lean_replay": True,
            "no_upstream_contact": True,
            "no_heavy_build": True,
            "must_inspect_exact_source_before_replay": True,
        },
    }

    summary = {
        "version": VERSION,
        "status": "ATTEMPT002_SOURCE_SCOUT_LEDGERED",
        "source_mode": source_mode,
        "query_count": len(QUERIES),
        "raw_result_count": scout["raw_result_count"],
        "unique_candidate_count": len(candidates),
        "selected_candidate_count": len(selected),
        "top_candidate_count": len(top5),
        "attempt001_status": "SENT_AWAITING_RESPONSE",
        "attempt001_url": "https://github.com/siddhartha-gadgil/MetaExamples/issues/1",
        "attempt002_status": "SCOUTED_NOT_SELECTED_FOR_REPLAY",
        "replay_attempted": False,
        "clone_attempted": False,
        "upstream_contact_performed": False,
        "bounded_claim": [
            "v4.4.27 scouts possible attempt002 Lean sorry targets using bounded GitHub code search",
            "it ranks candidates for cheap exact-source inspection",
            "it does not clone, replay Lean, modify upstream, or contact maintainers",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "candidate validity",
            "that any candidate is repairable",
            "that any candidate source still matches after inspection",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.28 inspect the top candidates for exact source snippets and select one tiny replay candidate",
    }

    report_lines = [
        "# SorryDB v4.4.27 — Attempt 002 Source Scout",
        "",
        "## Result",
        "",
        f"- source mode: {source_mode}",
        f"- query count: {len(QUERIES)}",
        f"- raw result count: {scout['raw_result_count']}",
        f"- unique candidate count: {len(candidates)}",
        f"- selected candidate count: {len(selected)}",
        f"- top candidate count: {len(top5)}",
        "",
        "## Top candidates",
        "",
    ]
    for c in top5:
        report_lines.extend(
            [
                f"### {c['candidate_id']}",
                "",
                f"- repo: {c['repo']}",
                f"- path: {c['path']}",
                f"- score: {c['score']}",
                f"- url: {c['html_url']}",
                f"- reasons: {', '.join(c['score_reasons'])}",
                "",
            ]
        )

    report_lines.extend(
        [
            "## Boundary",
            "",
            "No clone, Lean replay, upstream modification, or maintainer contact was performed.",
            "",
            "## Next frontier",
            "",
            "Inspect the top candidates for exact source snippets and select one tiny replay candidate.",
            "",
        ]
    )

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "source_scout.json", scout)
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
