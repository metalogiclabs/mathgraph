from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

VERSION = "v4.4.30"
OUT = Path("artifacts/sorrydb/lowrisk_lean4_scout_v4_4_30")
CACHE = OUT / "cache"
RAW_SEARCH = CACHE / "raw_search.json"

INPUTS = {
    "attempt002_recon_summary": Path("artifacts/sorrydb/attempt002_repo_recon_v4_4_29/summary.json"),
    "attempt002_recon": Path("artifacts/sorrydb/attempt002_repo_recon_v4_4_29/repo_recon.json"),
}

QUERIES = [
    'sorry language:Lean extension:lean "by simp"',
    'sorry language:Lean extension:lean "by rfl"',
    'sorry language:Lean extension:lean "Nat"',
    'sorry language:Lean extension:lean "example" "simp"',
    'sorry language:Lean extension:lean "omega"',
]

EXCLUDE_REPOS = {
    "metalogiclabs/mathgraph",
    "leanprover-community/mathlib4",
    "leanprover/lean4",
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def gh_api(endpoint: str, cache_name: str) -> tuple[bool, Any, str]:
    cache_path = CACHE / cache_name
    if cache_path.exists():
        return True, load_json(cache_path), "CACHE_REUSED"

    p = subprocess.run(
        ["gh", "api", endpoint],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        return False, {"error": p.stderr.strip(), "endpoint": endpoint}, "GH_API_FAILED"

    data = json.loads(p.stdout)
    write_json(cache_path, data)
    return True, data, "LIVE_FETCH_CACHED"

def run_search(query: str, idx: int) -> dict[str, Any]:
    endpoint = f"/search/code?q={quote(query)}&per_page=30"
    ok, data, mode = gh_api(endpoint, f"search_{idx:02d}.json")
    return {
        "query": query,
        "ok": ok,
        "mode": mode,
        "total_count": data.get("total_count") if ok else None,
        "incomplete_results": data.get("incomplete_results") if ok else None,
        "items": data.get("items", []) if ok else [],
        "error": data.get("error") if not ok else "",
    }

def endpoint_from_api_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    if parsed.netloc == "api.github.com":
        endpoint = parsed.path
        if parsed.query:
            endpoint += "?" + parsed.query
        return endpoint
    return api_url

def decode_content(data: dict[str, Any]) -> str:
    if data.get("encoding") != "base64":
        return ""
    content = data.get("content", "")
    if not content:
        return ""
    return base64.b64decode(content.encode()).decode("utf-8", errors="replace")

def fetch_candidate_file(candidate: dict[str, Any]) -> tuple[bool, str, str]:
    cid = candidate["candidate_id"]
    endpoint = endpoint_from_api_url(candidate["api_url"])
    ok, data, mode = gh_api(endpoint, f"file_{cid}.json")
    if not ok:
        return False, data.get("error", ""), mode
    return True, decode_content(data), mode

def fetch_repo_file(repo: str, path: str) -> tuple[bool, str, str]:
    safe_repo = repo.replace("/", "__")
    safe_path = path.replace("/", "__")
    endpoint = f"/repos/{repo}/contents/{path}"
    ok, data, mode = gh_api(endpoint, f"repo_{safe_repo}_{safe_path}.json")
    if not ok:
        return False, "", mode
    return True, decode_content(data), mode

def sorry_windows(text: str, radius: int = 3) -> list[dict[str, Any]]:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if "sorry" not in line:
            continue
        start = max(0, i - radius)
        end = min(len(lines), i + radius + 1)
        out.append({
            "line_number": i + 1,
            "line": line,
            "snippet": "\n".join(f"{j+1}: {lines[j]}" for j in range(start, end)),
        })
    return out

def classify_repo(repo: str) -> dict[str, Any]:
    files = {}
    for name in ["lakefile.lean", "lakefile.toml", "lean-toolchain", "leanpkg.toml"]:
        ok, text, mode = fetch_repo_file(repo, name)
        files[name] = {
            "exists": ok and bool(text),
            "mode": mode,
            "head": "\n".join(text.splitlines()[:20]),
        }

    lean4 = files["lakefile.lean"]["exists"] or files["lakefile.toml"]["exists"]
    lean_toolchain = files["lean-toolchain"]["head"]
    if "leanprover/lean4" in lean_toolchain or "stable" in lean_toolchain or "nightly" in lean_toolchain:
        lean4 = True

    lean3 = files["leanpkg.toml"]["exists"] and not lean4

    return {
        "manifest_files": files,
        "lean4_likely": lean4,
        "lean3_likely": lean3,
        "lean_toolchain": lean_toolchain,
    }

def score_candidate(candidate: dict[str, Any], text: str, windows: list[dict[str, Any]], repo_class: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if repo_class["lean4_likely"]:
        score += 15
        reasons.append("lean4 likely")
    if repo_class["lean3_likely"]:
        score -= 12
        reasons.append("lean3 likely")

    if len(windows) == 1:
        score += 8
        reasons.append("single sorry")
    elif 2 <= len(windows) <= 3:
        score += 3
        reasons.append("few sorries")
    else:
        score -= 5
        reasons.append("many/no sorries")

    lines = text.splitlines()
    if len(lines) <= 120:
        score += 4
        reasons.append("small file")
    elif len(lines) <= 300:
        score += 1
        reasons.append("medium file")
    else:
        score -= 3
        reasons.append("large file")

    lower = text.lower()
    target_line = windows[0]["line"].lower() if windows else ""

    if "by simp" in lower or "simp" in target_line:
        score += 6
        reasons.append("simp visible")
    if "by rfl" in lower or "rfl" in target_line:
        score += 5
        reasons.append("rfl visible")
    if "nat" in lower:
        score += 4
        reasons.append("nat visible")
    if "omega" in lower:
        score += 3
        reasons.append("omega visible")
    if "example" in lower:
        score += 2
        reasons.append("example context")
    if "equate" in lower or "†" in lower:
        score -= 8
        reasons.append("custom tactic/notation risk")
    if "begin" in lower and "end" in lower:
        score -= 5
        reasons.append("lean3 tactic-block risk")

    return score, reasons

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    recon29 = load_json(INPUTS["attempt002_recon_summary"])

    if RAW_SEARCH.exists():
        raw = load_json(RAW_SEARCH)
    else:
        raw = {
            "version": VERSION,
            "queries": QUERIES,
            "results": [run_search(q, i) for i, q in enumerate(QUERIES, start=1)],
        }
        write_json(RAW_SEARCH, raw)

    seen = set()
    base_candidates = []
    for result in raw["results"]:
        for item in result.get("items", []):
            repo = item.get("repository", {}).get("full_name", "")
            path = item.get("path", "")
            if repo in EXCLUDE_REPOS:
                continue
            key = (repo, path)
            if key in seen:
                continue
            seen.add(key)
            base_candidates.append({
                "candidate_id": f"lowrisk-lean4-{len(base_candidates)+1:03d}",
                "repo": repo,
                "path": path,
                "html_url": item.get("html_url"),
                "api_url": item.get("url"),
                "query_source": result.get("query"),
            })

    inspected = []
    for candidate in base_candidates[:30]:
        ok, text, file_mode = fetch_candidate_file(candidate)
        if not ok or not text:
            inspected.append({
                **candidate,
                "fetch_ok": False,
                "file_mode": file_mode,
                "status": "FILE_FETCH_FAILED",
                "score": -999,
                "score_reasons": ["file fetch failed"],
            })
            continue

        repo_class = classify_repo(candidate["repo"])
        windows = sorry_windows(text)
        score, reasons = score_candidate(candidate, text, windows, repo_class)

        inspected.append({
            **candidate,
            "fetch_ok": True,
            "file_mode": file_mode,
            "line_count": len(text.splitlines()),
            "sorry_count": len(windows),
            "windows": windows[:5],
            "repo_class": repo_class,
            "score": score,
            "score_reasons": reasons,
            "status": "LOWRISK_LEAN4_CANDIDATE_INSPECTED_NOT_REPLAYED",
        })

    inspected.sort(key=lambda x: (-x["score"], x["repo"], x["path"]))
    selected = inspected[0] if inspected and inspected[0].get("fetch_ok") else None

    scout = {
        "version": VERSION,
        "scout_type": "LOWRISK_LEAN4_ATTEMPT002_REPLACEMENT_SCOUT",
        "input_version": recon29.get("version"),
        "parked_previous_candidate": {
            "repo": recon29.get("repo"),
            "target_path": recon29.get("target_path"),
            "reason": recon29.get("decision"),
            "replay_risk": recon29.get("replay_risk"),
        },
        "query_count": len(QUERIES),
        "raw_result_count": sum(len(r.get("items", [])) for r in raw.get("results", [])),
        "unique_candidate_count": len(base_candidates),
        "inspected_candidate_count": len(inspected),
        "lean4_likely_count": sum(1 for x in inspected if x.get("repo_class", {}).get("lean4_likely")),
        "selected_candidate": selected,
        "inspected_candidates": inspected[:20],
        "constraints": {
            "no_clone": True,
            "no_lean_replay": True,
            "no_build": True,
            "no_upstream_contact": True,
            "github_api_only": True,
        },
    }

    summary = {
        "version": VERSION,
        "status": "LOWRISK_LEAN4_SCOUT_LEDGERED",
        "input_version": recon29.get("version"),
        "parked_repo": recon29.get("repo"),
        "parked_target_path": recon29.get("target_path"),
        "parked_reason": recon29.get("decision"),
        "query_count": scout["query_count"],
        "raw_result_count": scout["raw_result_count"],
        "unique_candidate_count": scout["unique_candidate_count"],
        "inspected_candidate_count": scout["inspected_candidate_count"],
        "lean4_likely_count": scout["lean4_likely_count"],
        "selected_candidate_id": selected["candidate_id"] if selected else "",
        "selected_repo": selected["repo"] if selected else "",
        "selected_path": selected["path"] if selected else "",
        "selected_score": selected["score"] if selected else None,
        "clone_attempted": False,
        "build_attempted": False,
        "replay_attempted": False,
        "upstream_contact_performed": False,
        "bounded_claim": [
            "v4.4.30 parks the medium-high-risk Lean3/equate attempt002 candidate",
            "it scouts lower-risk Lean4/Nat/simp candidates using GitHub API inspection only",
            "it selects one candidate for future bounded clone/recon without running Lean",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "candidate repairability",
            "that the selected repo builds locally",
            "that the selected source still matches after clone",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.31 clone only the selected low-risk Lean4 candidate into a bounded temp directory and run manifest/source reconnaissance before replay",
    }

    report_lines = [
        "# SorryDB v4.4.30 — Low-Risk Lean4 Scout",
        "",
        "## Parked previous candidate",
        "",
        f"- repo: {summary['parked_repo']}",
        f"- target path: {summary['parked_target_path']}",
        f"- reason: {summary['parked_reason']}",
        "",
        "## Result",
        "",
        f"- unique candidate count: {summary['unique_candidate_count']}",
        f"- inspected candidate count: {summary['inspected_candidate_count']}",
        f"- Lean4-likely count: {summary['lean4_likely_count']}",
        f"- selected candidate: {summary['selected_candidate_id'] or '(none)'}",
        f"- selected repo: {summary['selected_repo'] or '(none)'}",
        f"- selected path: {summary['selected_path'] or '(none)'}",
        f"- selected score: {summary['selected_score']}",
        "",
    ]

    if selected:
        report_lines.extend([
            "## Selected candidate",
            "",
            f"- repo: {selected['repo']}",
            f"- path: {selected['path']}",
            f"- url: {selected['html_url']}",
            f"- score: {selected['score']}",
            f"- reasons: {', '.join(selected['score_reasons'])}",
            f"- sorry count: {selected.get('sorry_count')}",
            f"- line count: {selected.get('line_count')}",
            "",
            "## First sorry window",
            "",
            selected["windows"][0]["snippet"] if selected.get("windows") else "(none)",
            "",
        ])

    report_lines.extend([
        "## Boundary",
        "",
        "No clone, Lean build, Lean replay, upstream modification, or maintainer contact was performed.",
        "",
        "## Next frontier",
        "",
        "Clone only the selected low-risk Lean4 candidate into a bounded temp directory and run manifest/source reconnaissance before replay.",
        "",
    ])

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "lowrisk_lean4_scout.json", scout)
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
