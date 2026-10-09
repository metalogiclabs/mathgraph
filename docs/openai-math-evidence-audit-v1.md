# OpenAI mathematics: pinned evidence audit v1

## Authority and objective
Upstream repository: https://github.com/openai/math
Exact upstream commit: fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb

This first audit intentionally separates source provenance, source-reported proof withdrawals, independently checked formal proof, and paper-to-theorem correspondence. A source check is never promoted to a Lean theorem check.

## Three source-reported withdrawals
The published notice for *Algebraicity of Weil classes on split abelian eightfolds* states that a stabilization-trace sign error leaves the signed double-point count -2m rather than 0, for positive m. The cited cancellation theorem requires zero. Its status is SOURCE_REPORTED_WITHDRAWN_PROOF.

Two notices explicitly depend on that flawed construction:
- *Algebraicity of Kuga–Satake Correspondences for K3 Surfaces* — SOURCE_REPORTED_WITHDRAWN_DEPENDENT_PROOF.
- *The rational Hodge conjecture for products of K3 surfaces* — SOURCE_REPORTED_WITHDRAWN_DEPENDENT_PROOF.

The notices date withdrawal October 6, 2026; the repository history records the batch under October 7. Each notice states explicitly that withdrawal concerns the proof, not falsity of the mathematical theorem. Dependency edges in this audit are declared by the publishers, not inferred independently from complete mathematical arguments.

## Independent Logspace formalization boundary
OpenAI's Comparator challenge file lean/ComparatorChallenges/LogspaceEquality.lean defines L, RL, BPL and gives an intentional theorem hole (by sorry).
The candidate solution source lean/OAI/Computability/Logspace/Equality.lean contains the same-named theorem with an explicit proof. The configuration lean/ComparatorChallenges/LogspaceEquality.json maps the theorem and listed definitions and permits only propext, Quot.sound and Classical.choice.

Current status: UNKNOWN_INDEPENDENT_LEAN_REPLAY. A lexical check that the single solution file lacks sorry, and equality of stated top-line theorem signatures, cannot prove its imported dependencies compile or that the paper's definitions faithfully align with the formal definitions.

## Run bounded replay
Offline falsifier controls:
PYTHONPATH=scripts python3 -m unittest discover -s tests -p test_openai_math_audit.py -v

Pinned-source audit, requiring HTTPS access to GitHub:
python3 scripts/openai_math_audit.py --output openai-math-audit.json

The audit fetches six allowlisted files at the exact upstream commit, checks each against its Git blob SHA-1, checks source-claimed withdrawal dependency and Comparator mappings, then emits a JSON evidence report. The GitHub Actions workflow runs both checks and stores the JSON artifact. Only the stated source-boundary is warranted by a green run.

## Smallest next experiment
Use a clean pinned Lean/Mathlib/Comparator environment with the published Comparator workflow:

cd lean
lake update
lake exe cache get
lake env comparator ComparatorChallenges/LogspaceEquality.json

Capture toolchain pins, full command, exit code, logs, declarations checked, imported axioms, and the formal definitions compared against the paper. Do not claim that this external replay has happened until an independently pinned run is green. Independently assess the topological sign derivation before treating OpenAI's withdrawal notice as a mathematical refutation.

Promotion: source-reported withdrawn proofs remain not disproven statements; logspace remains UNKNOWN until independently checked; preserve failed checks and exact provenance.

## Expanded source/model and build-pinning preflight

Source gate v2 also pins two Logspace LaTeX source sections (introduction and model),
the original Lean toolchain file, Lake manifest, and Lake package declaration,
all by Git blob identity at the same immutable upstream commit. It checks the
published model's fresh independent coin bits, time/space bounds, probability
thresholds, and a bounded subset of challenge-side class-definition tokens.
This is a **TEXTUAL_MODEL_CORRESPONDENCE_CANDIDATE_NOT_PROOF**.
It does not establish full mathematical equivalence of paper and formal definitions.

The actual pinned build is Lean 4.34.1 with Mathlib at
d13f23b723b8a846827a245b89c10fc7d3f11612. The current Comparator
repository head ca04cfc72b550331658ec314bf47685281bfd4bf targets
Lean 4.35.0-rc4. A replay must establish compatible versions and must
not silently run lake update, which may change locked dependencies.

## Isolated conditional sign proof

See experiments/openai-math-sign-v1/WeilSignProbe.lean with its
own lean-toolchain (Lean 4.34.1), minimal Lake project and CI
workflow openai-math-sign-witness.yml. It proves the arithmetic
implication that, **assuming** each reverse stabilization trace
contributes -1, a starting signed count -m with m>0 becomes -2m,
which is nonzero. It separately confirms why the obsolete +1
assumption would cancel. **WARRANTED_CONDITIONAL_SIGN_ARITHMETIC** at source commit 6329b71aaa09d7ff203ee4a15d070a52cc961c0c, [CI run 37864060265](https://github.com/metalogiclabs/mathgraph/actions/runs/37864060265), success: pinned Lean 4.34.1 build, bundled Leanchecker replay of WeilSignProbe, and axiom-audit of six declarations (permitted propext, Classical.choice, Quot.sound). The geometric orientation sign premise is still external and unproved here.

The sign/orientation premise itself is external to this tiny arithmetic
formalization. The sign proof must never be promoted as an independently
verified refutation of the original geometric theorem.

## Verification lineage and residual

1. [Expanded source audit run 37863542916](https://github.com/metalogiclabs/mathgraph/actions/runs/37863542916): 12 offline falsifier tests plus 11 exact upstream Git blob pins, paper/model textual preflight, and Lean/Mathlib version locks. This is *not* a Lean theorem check.
2. [Conditional arithmetic Lean build run 37863822633](https://github.com/metalogiclabs/mathgraph/actions/runs/37863822633): first green for the three sign-arithmetic theorems.
3. [Leanchecker run 37863912345](https://github.com/metalogiclabs/mathgraph/actions/runs/37863912345): explicit replay of the small checked environment, green.
4. [Axiom-audit qualification run 37864060265](https://github.com/metalogiclabs/mathgraph/actions/runs/37864060265): green, six declarations audited, no axioms beyond permitted list. This supersedes earlier weaker sign runs as the current independent arithmetic authority.

The previous failed axiom-audit attempt used a theorem namespace instead of the compiled Lean module prefix; preserve that configuration failure in CI lineage without misidentifying it as a mathematical counterexample.

Still UNKNOWN: full OpenAI Logspace Comparator replay; all imported definition and axiom checking under the OAI project; formal-versus-paper semantic correspondence; and independent proof of the geometric cusp-orientation sign. Do not promote a theorem beyond its verified boundary.

## Closed Logspace source import tree (static preflight only)

[Run 37864401230](https://github.com/metalogiclabs/mathgraph/actions/runs/37864401230) passed 20 focused offline falsifier controls, all 11 original source/build locks, and the new imported-source closure check. From the final solution Equality module, **39 of 39** local OAI Logspace modules were reached through transitive imports, and every downloaded UTF-8 source matched its Git blob identity in the immutable upstream release. The static lexical check raised **zero** risk signals after removing line and nested block comments. Machine-readable reports are preserved in GitHub Actions artifact openai-math-pinned-source-audit (artifact 11586939453).

This is **WARRANTED_STATIC_SOURCE_IMPORT_CLOSURE**, not proof checking. The comment stripper is not a full Lean parser; zero lexical signals is not a proof that the Lean environment lacks arbitrary axioms or that its kernel accepts the solution. Imported Mathlib code and trust in the challenge environment remain outside this source preflight.

The declared current main-theorem status is still UNKNOWN_INDEPENDENT_LEAN_REPLAY. A safe independent Comparator execution needs compatible pinned Lean, Comparator, lean4export and landrun versions, a sandbox consistent with comparator's threat model, and a full archived check of definitions and permitted axioms.
