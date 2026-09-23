#!/usr/bin/env python
"""Patch the live MathGraph.org static page with the qualified epistemic-status section.

Designed for Namecheap/cPanel shared hosting. It is intentionally fail-closed:
- searches only supplied roots,
- requires exactly one live-page match,
- writes a timestamped backup,
- injects one idempotent marked section,
- never changes verifier/truth metadata.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
from pathlib import Path

LIVE_PHRASE = "Verifiers decide what is true. MathGraph remembers how truth was proved"
SECTION_MARKER = "MATHGRAPH_EPISTEMIC_STATUS_V0"
INSERT_BEFORE_RE = re.compile(
    r"<h([1-6])\b[^>]*>\s*AI\s+RELIABILITY\s+LAYER\s*</h\1>",
    re.IGNORECASE,
)

SECTION = f"""
<!-- {SECTION_MARKER}:BEGIN -->
<section id="epistemic-status" data-mathgraph-surface="{SECTION_MARKER}">
  <h3>EPISTEMIC STATUS</h3>
  <p>
    MathGraph keeps four questions separate: what has been verified, what humans
    currently understand, how faithfully an informal claim maps to its formal
    statement, and what reusable generalizations have actually been earned.
  </p>
  <div class="epistemic-status-grid">
    <div class="epistemic-status-axis">
      <strong>Verification</strong>
      <span>Verifier-bound. This is the only axis that can carry mathematical truth authority.</span>
    </div>
    <div class="epistemic-status-axis">
      <strong>Human digest</strong>
      <span>Independent explanation/understanding status. It does not upgrade or downgrade truth.</span>
    </div>
    <div class="epistemic-status-axis">
      <strong>Statement fidelity</strong>
      <span>Whether the formal statement matches the intended claim. Qualified independently.</span>
    </div>
    <div class="epistemic-status-axis">
      <strong>Generalization</strong>
      <span>Whether a reusable method or abstraction has been earned. Advisory until independently warranted.</span>
    </div>
  </div>
  <p>
    A valid MathGraph state can therefore be:
    <code>VERIFIED_PROOF</code> · <code>UNDIGESTED</code> ·
    <code>statement fidelity UNKNOWN</code> · <code>generalization UNKNOWN</code>.
    Unknown means unknown—not false—and no non-verification axis can promote truth.
  </p>
</section>
<!-- {SECTION_MARKER}:END -->
""".strip()


def candidate_files(root: Path):
    for suffix in ("*.html", "*.htm", "*.php"):
        yield from root.rglob(suffix)


def find_live_page(roots: list[Path]) -> Path:
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in candidate_files(root):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if LIVE_PHRASE in html.unescape(text):
                matches.append(path.resolve())
    unique = sorted(set(matches))
    if len(unique) != 1:
        detail = "\n".join(str(x) for x in unique) or "(none)"
        raise SystemExit(
            f"Expected exactly one MathGraph.org live-page match; found {len(unique)}:\n{detail}"
        )
    return unique[0]


def patch_text(text: str) -> str:
    if f"{SECTION_MARKER}:BEGIN" in text:
        return text

    match = INSERT_BEFORE_RE.search(text)
    if match:
        return text[: match.start()] + SECTION + "\n\n" + text[match.start() :]

    fallback = re.search(r"AI\s+RELIABILITY\s+LAYER", text, re.IGNORECASE)
    if fallback:
        tag_start = text.rfind("<", 0, fallback.start())
        if tag_start >= 0:
            return text[:tag_start] + SECTION + "\n\n" + text[tag_start:]

    raise SystemExit("Could not find the AI RELIABILITY LAYER insertion boundary; no file changed.")


def verify_text(text: str) -> None:
    required = (
        SECTION_MARKER,
        "Verification",
        "Human digest",
        "Statement fidelity",
        "Generalization",
        "VERIFIED_PROOF",
        "UNDIGESTED",
        "UNKNOWN",
        "only axis that can carry mathematical truth authority",
        "no non-verification axis can promote truth",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Patched page failed verification; missing: {missing}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Hosting root to scan. Repeatable. Defaults to ~/public_html.",
    )
    parser.add_argument("--page", help="Exact live page path; skips scanning.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    page = Path(args.page).expanduser().resolve() if args.page else find_live_page(
        [Path(x).expanduser().resolve() for x in args.root]
        if args.root
        else [(Path.home() / "public_html").resolve()]
    )

    original = page.read_text(encoding="utf-8")
    patched = patch_text(original)
    verify_text(patched)

    if patched == original:
        print(f"already_patched={page}")
        return 0

    if args.dry_run:
        print(f"dry_run_target={page}")
        print(f"would_add_marker={SECTION_MARKER}")
        return 0

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = page.with_name(f"{page.name}.pre-{SECTION_MARKER.lower()}-{timestamp}.bak")
    shutil.copy2(page, backup)

    temp = page.with_name(f".{page.name}.{SECTION_MARKER.lower()}.tmp")
    temp.write_text(patched, encoding="utf-8")
    temp.replace(page)

    verify_text(page.read_text(encoding="utf-8"))
    print(f"patched={page}")
    print(f"backup={backup}")
    print(f"marker={SECTION_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
