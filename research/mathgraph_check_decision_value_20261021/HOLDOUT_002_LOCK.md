# Prospective holdout 002 — frozen before code / PR inspection

Target selected from GitHub search title alone: `yuin/goldmark-meta` PR #8, "Accept `...` as frontmatter terminator (pandoc syntax)".
No source file, PR patch or PR body had been opened before this lock.

Competing decision procedures:
A. Equal-information ordinary reviewer + repository native tests, assessing YAML-frontmatter terminators, content boundaries, Markdown nesting and literal `...` lines.
B. MathGraph consequence-oriented method: generate paired documents differing only in the termination marker (`---` versus `...`) under the documented input contract, assert frontmatter value equivalence and preservation of post-frontmatter body, and try negative controls with `...` outside the frontmatter region.
Primary outcome: a native-reproducible consequential difference not already tested by the PR/conventional reviewer. Secondary: avoid an invented bug or false PR attribution.
A reviewer can use the same documents, source and tools; the baseline gets credit for all visible tests.
If the PR already tests these obligations, report BASELINE_VISIBLE. The method is fixed before source inspection. No third-party write or review.
