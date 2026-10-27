#!/usr/bin/env python3
"""Reject public PR content that resembles private working correspondence.

This is a pre-publication guard, NOT a secrets scanner or a privacy guarantee.
Print only names and rule IDs, never the matching text.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

PATTERNS = (
    ("private_workspace_link", re.compile(r"https?://(?:www\.)?(?:app\.notion\.com/(?:p/|[^ \t/]*/)|overleaf\.com/project/)", re.I)),
    ("email_header", re.compile(r"(?m)^\s*(?:to|from|cc|bcc)\s*:\s*[^\n]{0,150}@[\w.-]+\.[a-z]{2,}", re.I)),
    ("private_handoff", re.compile(r"(?i)\b(?:personal|private|internal|unsent|not.sent|not.yet.sent)\b[^\n]{0,110}\b(?:research notes?|collaborat(?:ion|or)|correspondence|co.author|handoff|email|outreach|strategy|draft)\b")),
    ("private_handoff_reverse", re.compile(r"(?i)\b(?:co.author|collaborat(?:ion|or)|correspondence|handoff|email|outreach|strategy|draft)\b[^\n]{0,110}\b(?:private|internal|unsent|not.sent|not.yet.sent)\b")),
    ("communications_status", re.compile(r"(?i)\b(?:already sent|not yet sent|do not resend|awaiting (?:a |their |his |her )?reply|has not been sent)\b")),
    ("direct_message_copy", re.compile(r"(?m)^\s*(?:on \d{4}-\d{2}-\d{2}.*wrote:|sent:\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))", re.I)),
)
EXTENSIONS = (".md", ".mdx", ".txt", ".rst", ".tex", ".py", ".lean", ".js", ".ts", ".tsx", ".jsx", ".yaml", ".yml", ".toml", ".json", ".sh")
DIRECT_ATTACHMENTS = (".eml", ".msg", ".pdf", ".docx", ".zip", ".tar.gz")


def check_text(source: str) -> list[str]:
    """Return only rule identifiers, not matching confidential text."""
    return [name for name, rule in PATTERNS if rule.search(source)]


def check_path(path: pathlib.Path, status: str, root: pathlib.Path) -> list[str]:
    # This checker contains intentionally suspicious strings for its self-tests.
    # Its own code changes still require ordinary human code review.
    if path.as_posix() == "scripts/publication_boundary_guard.py":
        return []
    name = str(path).lower()
    if status == "A" and name.endswith(DIRECT_ATTACHMENTS):
        return ["unreviewed_binary_attachment"]
    if status == "A" and re.search(r"(?i)(?:^|[/_-])(?:confidential|coauthor|private-notes|personal-handoff|unsent-draft)(?:[/_.-]|$)", name):
        return ["private_artifact_path"]
    if not name.endswith(EXTENSIONS):
        return []
    source = root / path
    if not source.is_file():
        return []
    if source.stat().st_size > 2_000_000:
        return ["text_file_too_large_to_audit"]
    try:
        content = source.read_text(encoding="utf-8")
    except UnicodeError:
        return ["non_utf8_text_file"]
    return check_text(content)


def changed_files(base: str, head: str, root: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    args = ["git", "-C", str(root), "diff", "--no-ext-diff", "--name-status",
            "-z", f"{base}...{head}"]
    raw = subprocess.check_output(args)
    chunks = [x.decode("utf8") for x in raw.split(b"\0") if x]
    result = []
    i = 0
    while i < len(chunks):
        kind = chunks[i][0]
        i += 1
        if kind in ("R", "C"):
            i += 1  # original path
        if i >= len(chunks):
            raise RuntimeError("MALFORMED_GIT_DIFF")
        path = chunks[i]
        i += 1
        if kind != "D":
            result.append((kind, pathlib.Path(path)))
    return result


def run(base: str, head: str, root: pathlib.Path, event: pathlib.Path | None) -> list[tuple[str, str]]:
    found = []
    for kind, path in changed_files(base, head, root):
        for rule in check_path(path, kind, root):
            found.append((path.as_posix(), rule))
    if event is not None and event.is_file():
        payload = json.loads(event.read_text(encoding="utf8"))
        pr = payload.get("pull_request") or {}
        title = pr.get("title") or ""
        body = pr.get("body") or ""
        for rule in check_text(title + "\n" + body):
            found.append(("(PR description)", rule))
    return found


def selftest() -> None:
    assert not check_text("Machine-checkable proof of a fixed Boolean theorem.")
    assert not check_text("Public software tests pass on the pinned source revision.")
    assert "private_workspace_link" in check_text("Draft: https://app.notion.com/p/example")
    assert "private_workspace_link" in check_text("https://www.overleaf.com/project/example")
    assert "communications_status" in check_text("The original email was already sent.")
    assert "private_handoff" in check_text("Private collaboration handoff for review")
    assert "email_header" in check_text("To: somebody@example.org")
    assert "direct_message_copy" in check_text("On 2026-10-10 person wrote:")
    print("PUBLICATION_BOUNDARY_GUARD_SELFTEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--event", type=pathlib.Path)
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.base or not args.head:
        parser.error("--base and --head are required")
    violations = run(args.base, args.head, args.repo, args.event)
    for path, rule in violations:
        # Do not print the content, URL, email or personal names.
        print(f"PUBLICATION_REVIEW_REQUIRED {path} [{rule}]", file=sys.stderr)
    if violations:
        print(f"PUBLICATION_BOUNDARY_REFUSED: {len(violations)} flagged locations", file=sys.stderr)
        return 1
    print("PUBLICATION_BOUNDARY_GUARD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
