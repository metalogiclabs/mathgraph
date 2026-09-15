# V70 — Adaptive causal budget allocation

V69 counterfactual-value ranking exposed a structural problem: with a 16-rule
round-1 quota, ranking often retained the same entire shallow action set as the
cold developer. The learned value function therefore had no opportunity to
change the reachable capability frontier.

V70 keeps the total derived-lemma budget fixed at 31 but changes its geometry.

- **COLD:** 16 shallow round-1 rules + 15 complexity-ranked round-2 rules.
- **META:** 8 highest-valued source/self seeds, then recursively spends the
  remaining 23 rules on descendants with the greatest verified marginal value.

Marginal value combines the inherited learned seed value, the exact number of
new critical-pair consequences unlocked by retaining a candidate, and structural
compression. The lookahead is source-only and target-independent. Every
counterfactual child, retained equation, and accepted target proof is exactly
replayed.

The Stage2 stream is already opened and is used only for calibration. A fresh
external stream is not licensed unless META creates exclusive structure and
that structure contributes causally to new verified target reach.
