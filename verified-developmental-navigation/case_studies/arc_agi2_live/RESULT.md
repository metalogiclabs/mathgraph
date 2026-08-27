# ARC live navigation — result

This sequence tested Verified Developmental Navigation prospectively on pinned public ARC data. Routing was learned only from training tasks; evaluation outputs were used only after commitment for scoring.

## V1 — ARC-AGI-2 frozen base language

Source: `arcprize/ARC-AGI-2` at `f3283f727488ad98fe575ea6a5ac981e4a188e49` (1,000 training, 120 public evaluation tasks).

Frozen families: geometry, recoloring, single-color crops, complement crops, cell scaling, grid tiling, and uniform-block downsampling. The fallback extension was geometry followed by recoloring.

Result: no candidate in the frozen language fit all demonstrations for any of the 120 evaluation tasks. GLOBAL and VDN therefore both solved 0/120. This is a representation/language obstruction, not evidence against routing.

## V2 — residual-driven structural expansion

The V1 residual justified expanding the candidate language with connected-component extraction, separator-tile extraction, symmetry concatenation, and a fallback structural-transform-then-recolor family.

Result: again, no candidate fit all demonstrations for any of the 120 ARC-AGI-2 evaluation tasks. GLOBAL and VDN both solved 0/120. The enlarged search attempted 13,912 verifier candidates across the evaluation set before exhausting the bounded language.

The correct conclusion is narrow: this hand-built bounded DSL is far below the representation complexity required by ARC-AGI-2. More routing cannot repair that boundary.

## V3 — unchanged language/routing transferred to ARC-AGI-1

To test navigation in a real regime with nonzero language reach, V2 was transferred unchanged to `fchollet/ARC-AGI` at `399030444e0ab0cc8b4e199870fb20b863846f34` (400 training, 400 public evaluation tasks). The V3 transfer was precommitted before scoring.

The frozen language exactly solved 1/400 evaluation tasks under both GLOBAL and VDN. On that common reachable task:

- GLOBAL needed 41 candidate verifications before commitment.
- VDN needed 1 candidate verification.
- Exact solve count remained 1/400 for both arms.

So the precommitted bounded navigation criterion passed: **41x fewer verifier checks on the common-solved set with no loss of exact solves**.

Across all 400 evaluation tasks, GLOBAL used 39,903 candidate checks and VDN used 39,863. The overall reduction is small because 399/400 tasks are outside the frozen language. The fallback structural-recolor extension produced no new exact solves, so no developmental phase change was observed.

## What this decides

The experiment separates two failure modes on real data.

1. **Navigation can matter conditional on reachability.** When the correct continuation exists in the current language, retained residual state can materially reduce the verifier search needed to reach it; the ARC-AGI-1 reachable case was 41 checks versus 1.
2. **Representation dominates when reachability is absent.** ARC-AGI-2 produced a clean bounded obstruction even after one residual-driven language expansion: none of 120 evaluation demonstration sets were representable by the tested DSL.

The next move should therefore be representation learning / operator construction from residuals, not another routing tweak. The target is to increase the set of demonstration-consistent reachable tasks first, then re-measure navigation on that enlarged capability boundary.

## Reproduction

Workflow: `.github/workflows/vdn-arcagi2-live.yml`

Protected successful combined run: `33037441971`

Artifact: `vdn-arc-live-v3` (`9632535088`).
