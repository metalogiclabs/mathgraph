# Exact Frozen LeanEval Sturm — Verified

## Result

The exact frozen LeanEval `sturm` benchmark theorem compiled successfully in the generated frozen challenge workspace.

### Deciding evidence

- MathGraph proof commit: `91247b2e18de9a554a192aa3134cbff680a2f142`
- Pull-request merge commit compiled by CI: `4485fe1940ef359099bf4d8bb28e8e106c4a9ec0`
- Frozen LeanEval commit: `9b82c4083e71e93c7d6aa43a960cd492ae53a35d`
- Pinned mathlib commit: `6f1ef4e5dd604a435bddba4747b13970cd65d2a1`
- Workflow run: `33237385635`
- Job: `99060640689`
- Artifact: `9710378791`
- Artifact SHA-256: `634bc65b6aa98c14def5d06542140bb099ab1f273affdfe2f562aa43f031261f`

Decisive log lines:

```text
⚠ [8708/8709] Built Submission (8.4s)
Build completed successfully (8709 jobs).
sturm_probe_exit=0
```

The warning marker on `Built Submission` is from linter warnings (unused simp arguments / variable), not a proof failure. Lean exited successfully.

## Exact target

```lean
theorem sturm (p : ℝ[X]) (hp : Squarefree p) {a b : ℝ} (hab : a < b)
    (ha : p.eval a ≠ 0) (hb : p.eval b ≠ 0) :
    ((p.roots.toFinset).filter (fun x => a < x ∧ x < b)).card =
      sigma p a - sigma p b := by
  ...
```

This is the exact frozen benchmark shape, not a surrogate theorem.

## Proof architecture

The final global representation is the compensated quantity

```text
C_p(x) = sigma p x + #{r ∈ roots(p) | r ≤ x}.
```

Away from roots, both terms are locally constant. At a squarefree root, `sigma` drops by exactly one from left to right while the prefix root count increases by exactly one. Thus `C_p` is locally constant everywhere. Connectedness of `ℝ` makes it globally constant, and endpoint subtraction yields the exact interval root count.

## Verified capability chain

The proof developed through reusable verified interfaces rather than a single monolithic search:

1. remainder evaluation at a root;
2. zero deletion for `signChanges`;
3. simple-root crossing law;
4. analytic derivative/sign bridge;
5. squarefree root derivative nonvanishing;
6. three-window sign-change separator;
7. arbitrary-context middle-state elimination;
8. pointwise no-common-zero preservation;
9. terminal-safe `SturmRegularAt` after the weaker interface failed;
10. arbitrary-fuel local variation constancy;
11. structural `SturmComplete`;
12. degree-bounded Euclidean completion;
13. benchmark `sigma` local constancy away from roots;
14. root-local sigma profile and finite-root prefix profile;
15. globally constant compensated invariant;
16. exact frozen `sturm` theorem.

## Residual collapse / MSI observation

A genuine representation residual occurred when the earlier active-adjacency safety interface failed to account for an observable terminal zero at fuel exhaustion. The minimal repair was to move from the weaker safety condition to terminal-safe `SturmRegularAt`.

After that representation change, several downstream obligations became reachable without another architectural invention: arbitrary-fuel constancy, degree completion, benchmark sigma local constancy, root profiles, the compensated invariant, and finally the exact theorem.

The final integration frontier also collapsed sharply:

```text
run #51: multiple integration residual classes
→ run #54: one proof-shape normalization residual
→ run #55: exact frozen benchmark build succeeds
```

This is consistent with the cross-domain Minimal Sufficient Interface hypothesis: progress can become discontinuous after the representation preserves exactly the distinctions needed for future verified behavior.

## Trust / audit notes

The generated submission stack imports `ChallengeDeps`, not `Challenge`. The exact theorem is proved in `Global.lean`. The verified source inspected at the green commit contains no `sorry` or `admit` in the final proof file; an independent reproduction should be retained as additional evidence before external submission packaging is frozen.
