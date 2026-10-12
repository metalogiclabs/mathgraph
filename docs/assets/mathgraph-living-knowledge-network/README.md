# MathGraph living knowledge network — visual evidence

This directory is the small committed index for release-candidate visual and
browser evidence. Generated PNGs, traces and JSON reports are not stored in Git
under repository policy. They are written only to `BROWSER_EVIDENCE_DIR` and,
for final qualification, retained as GitHub Actions or other approved external
artifacts.

## Current checkpoint

- branch: `codex/living-knowledge-network`
- exact release identity: the commit containing this index, recorded by Git
  and the associated CI run rather than embedded recursively in these bytes
- local accessibility result: 48/48 route-viewports, zero axe violations and
  zero incomplete findings; generated `aria-hidden` source-neighbourhood SVGs
  are excluded while the same nodes, relations and links are tested through
  adjacent semantic HTML and dedicated browser tests
- local performance result: settled search p95 30.8 ms normally and 29.1 ms
  under 4× CPU slowdown; maximum bounded graph 277.6 ms to interactive,
  with 7.2 ms selection and 0.8 ms traversal p95 under 4× slowdown
- draft pull request: **PENDING**
- exact-head CI artifact: **PENDING**
- protected Vercel preview: **PENDING**
- production change: **NOT_PERFORMED**

No preview screenshot or external artifact identity is claimed before it
exists. The final evidence set should contain:

- desktop 1440×900, tablet 768×900 and mobile 390×844 review captures;
- the 48-route/viewport accessibility report and optional captures;
- static size and deterministic-gzip report;
- search and graph timing report, including the 4× CPU workload;
- exact commit, CI run, artifact and protected-preview identities; and
- hashes for any representative captures cited by the release report.

The local browser runner can produce the accessibility evidence without
writing inside the repository:

```sh
cd website
BROWSER_EVIDENCE_DIR=/absolute/external/path npm run test:accessibility-browser
```

Performance evidence uses the same boundary:

```sh
cd website
BROWSER_EVIDENCE_DIR=/absolute/external/path npm run test:performance-browser
```

Screenshots demonstrate selected rendered states only. They do not establish
mathematical truth, source authenticity, universal accessibility, production
capacity or outside-owner adoption. The interactive maps remain presentation
projections with authority `NONE`; immutable record bytes and committed
catalogue bytes remain the machine-readable artifacts from which those
projections are derived within their declared scopes.
