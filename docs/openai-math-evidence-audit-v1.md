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

## 2026-10-09 independent main-module kernel check (bounded positive)

[Run 37867638994](https://github.com/metalogiclabs/mathgraph/actions/runs/37867638994) **SUCCESS** (source workflow head e2384bb35837f6fecbb164351b7806af38f0b6ab): exact `openai/math@fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb` 39-module OAI Logspace directory with separately pinned Lean 4.34.1 and Mathlib `d13f23b723b8a846827a245b89c10fc7d3f11612`, in a minimal Mathlib-only Lake package. The runner completed 8962 build jobs, including `OAI.Computability.Logspace.Equality`, and successfully executed `lake env leanchecker OAI.Computability.Logspace.Equality` on the generated module environment.

**WARRANTED_BOUNDED_ISOLATED_LEAN_MODULE_CHECK:** the actual imported solution module compiles and its export environment is accepted by Leanchecker's checked boundary in this isolated environment. This is stronger than source scanning but does **not** establish that Comparator accepts the solution relative to the challenge, nor that the paper's formulation is semantically identical. An explicit target-theorem axiom query is added under [source commit f17a0ef](https://github.com/metalogiclabs/mathgraph/commit/f17a0ef85fc4922923c14e1c74010aef0000e755) and requires its own green qualification before axiom policy is promoted.

**Sandboxed Comparator failure lineage:** [run 37868000488](https://github.com/metalogiclabs/mathgraph/actions/runs/37868000488) failed before judging due to missing Git inside the Ubuntu container after a Mathlib metadata refresh. The [corrective run 37868310604](https://github.com/metalogiclabs/mathgraph/actions/runs/37868310604) is separate; only an explicit Comparator exit zero can qualify challenge/solution correspondence.

## Paper-to-formal-model correspondence ledger (CANDIDATE, not established)

The manuscript source compared is the pinned `build/sections/introduction.tex` and `model.tex`; the challenge-side definitions are at `lean/ComparatorChallenges/LogspaceEquality.lean`. The following dimension-by-dimension matches are **inspection candidates**, not proofs of equivalent mathematical notions:

| Protected dimension | Paper's stated model | Exact challenge definition | Status / residual |
| --- | --- | --- | --- |
| Finite program | Finite control, finite work tapes and input heads | `Machine q w h`, `Fin (q+1)`, transitions over finite scanned-symbol domains | CANDIDATE; finite-table encoding and standard-model simulation unproved |
| Input and boundaries | Endmarked read-only input; head kept between markers | `readInput`, `Fin (x.length+2)` and `Direction.moveInput` | CANDIDATE; edge cases and standard boundary conventions need an equivalence proof |
| Randomness | Fresh independent fair coin bits | `CoinTape := ℕ → Bool`; `run x coins`; uniform finite `Fin t → Bool` sum over `2^t` tapes | CANDIDATE; coincidence with paper's probability law needs a formal bridge |
| Halting and time | Polynomial worst-case time on every random tape | `HaltsBy` universally quantifies over tapes at `polynomialClock c k n` | CANDIDATE; encode all allowed machine conventions |
| Space | All visited writable cells count, even blank; simultaneous registers charged | `spaceThrough` cardinality of visited work-head positions, summed over heads | CANDIDATE; an exact representation/simulation theorem remains absent |
| L | Deterministic O(log(n+2)) space decider | `L` as existential coin-independent `Machine.Deterministic` with `LogSpace` and `Decides` | CANDIDATE; finite-table and uniformity correspondence unproved |
| RL | One-sided polynomial-time bounded error; no-instance acceptance zero and yes at least one half | `RL` with `acceptanceProbability=0` on no and ≥1/2 on yes | CANDIDATE; quantitative constants match |
| BPL | Two-sided probability at most one third on no, at least two thirds on yes | `BPL` with exactly these rational inequalities | CANDIDATE; quantitative constants match |
| Main theorem | `L=RL=BPL` | `L = RL ∧ RL = BPL` under these Lean definitions | Only **formal proposition's surface** matches; mathematical theorem correspondence UNKNOWN |

The dependency and formalization gate does not establish that this chosen finite-machine encoding is extensionally equivalent to the conventional complexity classes. Even a successful Comparator verdict should warrant the theorem **in these formal definitions** first. To promote the broader paper claim, supply independent definitions or a machine-model equivalence/compilation proof, including uniformity and visited-cell accounting. An unusually strong result should not be marketed without this second step.

## 2026-10-09 exact source-level identity of the complete Logspace definitions block

[CI run 37869231597](https://github.com/metalogiclabs/mathgraph/actions/runs/37869231597) **SUCCESS**: 25 Python source/falsifier tests, a pinned Git blob check on the published challenge and solution model, and an exact 4,202-character comparison from `abbrev Word := List Bool` through the closing `BPL` definition. The corresponding block in `lean/ComparatorChallenges/LogspaceEquality.lean` and `lean/OAI/Computability/Logspace/Deterministic.lean` is byte-for-byte equal after decoding UTF-8; no whitespace normalization was required. Qualified status: **WARRANTED_PINNED_MODEL_TEXT_IDENTITY**.

The published Comparator config includes **20** `definition_names` entries, including `L`, `RL`, and `BPL`. In pinned Comparator `d03acab...`, those declarations are checked for type/universe/safety but their definition bodies can vary; its README explicitly warns that definition holes can be exploited. This is an important trust-boundary caveat, even though OpenAI's *actual pinned source block* is textually identical.

[Strict variant source commit a950632](https://github.com/metalogiclabs/mathgraph/commit/a9506325ab8ef262b7907fe4da41f17bd124134c) builds an alternate Comparator config with **zero** definition-hole exemptions and attempts both the publisher config and a strict definition-identity comparison, so the latter can require equality of relevant compiled definition bodies. A strict config file, its issuance, or source identity does not prove a successful Comparator result. The exact formal theorem remains **UNKNOWN_CHALLENGE_SOLUTION_COMPARATOR** until the strict run finishes successfully.

## 2026-10-09 default Comparator exact-theorem acceptance (qualified)

[Run 37868310604](https://github.com/metalogiclabs/mathgraph/actions/runs/37868310604) SUCCESS: sandboxed independent Comparator using exact OpenAI source commit `fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`, Lean 4.34.1, Mathlib `d13f23b723b8a846827a245b89c10fc7d3f11612`, pinned Comparator `d03acab154d269c06e60e4de7e4cc85deebff94b`, lean4export `076e8e57707e813375e8f9da8bf989799ace9680`, and pinned Landrun. The Linux checker execution was containerized with no network, no elevated capabilities, read-only toolchains and the native sandbox. It built the `ComparatorChallenges.LogspaceEquality` challenge with the intentional `sorry`, compiled and exported the candidate 39-module solution, reported `Lean default kernel accepts the solution`, then `Your solution is okay!`.

Status is **WARRANTED_DEFAULT_COMPARATOR_ACCEPTANCE**, narrowly scoped to the published Comparator configuration. This is *not* automatically identical to a strict verification of the challenge's definition bodies, because 20 names including `L`, `RL`, `BPL` are designated definition holes. The 4,202-character model block's source identity is independently checked, but a strict compiled-value check must be performed before promoting definition identities.

An explicit controlled external falsifier [run 37869403430](https://github.com/metalogiclabs/mathgraph/actions/runs/37869403430) SUCCESS confirms the policy boundary: when the definition is designated as a hole, the pinned Comparator accepts a self-authored `False`→`True` change; with an empty definition-hole list it rejects that change (`Const does not match ... Probe.Meaning`). This canary uses only self-authored files and a Comparator development shim lacking real sandboxing; it was **not** used to judge OpenAI's sources.

Strict all-definition Comparator and explicit main-theorem transitive axiom query have been launched but have not yet received terminal verified results at this checkpoint. The paper's equivalence to standard textbook machine models remains UNKNOWN even if both succeed.

## 2026-10-09 — STRICT Comparator and theorem axiom closure qualified

**WARRANTED_STRICT_COMPARATOR_ACCEPTANCE:** [GitHub Actions run 37869086450](https://github.com/metalogiclabs/mathgraph/actions/runs/37869086450) **SUCCESS**, exact `openai/math@fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`, Lean 4.34.1, Mathlib `d13f23b723b8a846827a245b89c10fc7d3f11612`, pinned Comparator `d03acab154d269c06e60e4de7e4cc85deebff94b` and lean4export `076e8e57707e813375e8f9da8bf989799ace9680`. The containerized native-Landrun checker first accepted the published Comparator config and then the **strict variant with `definition_names=[]`**. Verbatim evidence: `DEFAULT_COMPARATOR_ACCEPTED`, `Lean default kernel accepts the solution`, `Your solution is okay!`, `STRICT_DEFINITION_IDENTITY_ACCEPTED`, `COMPARATOR_DEFAULT_AND_STRICT_DEFINITION_IDENTITIES_BOTH_PASSED`. Thus the previously noted 20 definition-hole exemptions are removed from the *strict* checked boundary.

**WARRANTED_MAIN_THEOREM_AXIOM_CLOSURE:** [run 37869603109](https://github.com/metalogiclabs/mathgraph/actions/runs/37869603109) **SUCCESS**, exact isolated Logspace solution build + Leanchecker; target-specific `#print axioms OAI.ExactDerandomization.exact_logarithmic_space_derandomization` reports precisely `propext`, `Classical.choice`, `Quot.sound`. The previous unbalanced-regex failure in run 37868663392 was corrected before this qualified run.

**Promoted statement (exact boundary):** `OAI.ExactDerandomization.exact_logarithmic_space_derandomization : L = RL ∧ RL = BPL`, *using the challenge's immutable formal definitions*, has an independently checked Lean kernel proof with strict definition agreement and only the permitted axioms. This is a major formal verification result but must not be paraphrased as a separate proof that any particular textbook presentation of L/RL/BPL is extensionally identical to these definitions.

**Remaining mathematical residual — UNKNOWN_STANDARD_MODEL_ADEQUACY:** independently bridge the paper's informal finite-control, endmarked-input, multi-tape, visited-cell logarithmic-space and per-step fair coin semantics to the formal classes. A good next experiment must introduce an independently authored operational model rather than merely restating the challenge's definitions; bounded examples/test vectors cannot establish general model equivalence, but can falsify naive mappings. Also separately check the paper's claimed ancillary approximation and compiler theorems; the Comparator target is the single main equality.

## Quantitative standard-machine adequacy: two-direction simulation obligations

**Status: UNKNOWN, not implied by the strict Comparator PASS.** The *paper* describes uniform finite-control machines with fixed finite numbers of input/work heads, fair independent bits, polynomial all-coin halting time and O(log(n+2)) visited-cell workspace. The Lean challenge defines its own finite-transition-table realization. A full statement about textbook complexity classes requires **both** simulation directions:

1. **Conventional randomized logspace TM to challenge Machine**: choose machine-dependent fixed `q`, `w`, `h`; compile each finite input/work alphabet to constant-size binary work-cell blocks; simulate finite coin alphabets by a bounded number of fresh Boolean flips; preserve read-only input/endmarkers, halting answers, and exact probability thresholds (or amplify when making bounded-probability normalization). Establish a uniform time slowdown bounded polynomial in `n+2` and visited-cell overhead at most a machine-dependent constant factor plus O(1). No per-input advice or unbounded transition tables.
2. **Challenge Machine to conventional randomized logspace TM**: its transition table has a finite domain for any fixed `q,w,h` and can be compiled into fixed finite control. Encode the finitely many bi-infinite Boolean work tapes on conventional semi-infinite tapes by signed-address interleaving at constant-factor space overhead; because head movements are at most one cell per step from initial position zero, the set of previously visited sites on each tape is an interval, allowing visited-cell counts to bound span and actual storage. Simulate each fresh Boolean coin with one unbiased random-bit operation, preserve acceptance/no-acceptance probabilities, and retain the universal per-coin polynomial clock.
3. **Deterministic time bound residual**: the challenge's `L` asks for a halting deterministic logspace decider but no explicit polynomial clock. For a fixed machine, bound reachable configurations by `(q+1)·(n+2)^h · polynomial(S) · 2^{O(S)}` with `S=c·clog₂(n+2)` and fixed `q,w,h,c`; for deterministic halting runs a repeated configuration before halting would loop, so time is polynomial. This is an elementary but still *unformalized model-bridge step*.

These obligations are structural, not satisfied by textual equality, source-only flags, theorem axiom checks, or bounded empirical witnesses. The currently running `ModelSemantics.lean` experiment isolates four prerequisite laws (deterministic coin irrelevance, bounded coin-prefix dependence, absorbing halts); its success, if obtained, should be promoted only as **WARRANTED_BOUNDED_MACHINE_OPERATIONAL_LAWS**, not as both-direction complexity-class equivalence.

## 2026-10-09 — Four independently authored general operational laws qualified

[Run 37871293342](https://github.com/metalogiclabs/mathgraph/actions/runs/37871293342) **SUCCESS**, at bridge source commit [436be379](https://github.com/metalogiclabs/mathgraph/commit/436be3796bc2c87c54e282d705d9a310701a9cd1). The isolated Lean 4.34.1 / pinned Mathlib build imported OpenAI's exact `Deterministic.lean` and checked four general, independently authored lemmas in `ModelSemantics.lean`: deterministic one-step coin irrelevance; deterministic whole-run coin irrelevance; halting-state absorption; and coin-prefix independence up to time `t`. Leanchecker replay green, with each theorem's `#print axioms` reporting exactly `propext` and `Quot.sound`. Artifact `openai-logspace-model-bridge`, ID 11590577434.

**WARRANTED_GENERAL_OAI_OPERATIONAL_LEMMAS** is narrower than an equivalence theorem between this finite-transition-table model and all standard randomized Turing-machine presentations. The next mathematically consequential bridge is a configuration-count and deterministic-halting polynomial-time lemma, followed by two independently formulated, uniform machine simulations. Do not replace this residual with merely testing further examples.

## 2026-10-09 — Six general machine-semantic laws checked in Lean (v2)

[Run 37871611104](https://github.com/metalogiclabs/mathgraph/actions/runs/37871611104) **SUCCESS**, source [a2bebcc](https://github.com/metalogiclabs/mathgraph/commit/a2bebccca3d4c54faea8b8acba6aa374c785dcca). Lean 4.34.1 + exact Mathlib; 8926 build tasks including separately authored ModelSemantics module; independent Leanchecker replay; six target-theorem axiom scans each exactly `[propext, Quot.sound]`. Qualified artifact ID 11590682845, ZIP SHA256 `8171b5f88dfabb3fb10987e7ce0c53e15efe078b6d6ff9cb3ef2886b6e6a0e90`.

The six proved general facts are one-step deterministic coin irrelevance, full-run deterministic coin irrelevance, absorbing halting step, finite coin-prefix dependence, halting persistence for arbitrary subsequent steps, and the fact that equal configurations in deterministic runs imply equal later configurations. Together these **WARRANTED_GENERAL_OAI_OPERATIONAL_LEMMAS_V2** replace the four-lemma V1 qualification.

These lemmas supply an independent semantic foundation inside the published OAI machine model. **They do not bound the total number of reachable configurations or show that the selected machine model is mathematically equivalent to textbook Turing machines.** The cheapest major residual is a machine-dependent polynomial bound on reachable configurations from `M.LogSpace` and fixed input/work-head counts, followed by two-direction compilation into a separately specified standard model.

## 2026-10-09 — Finite envelope and pre-halt injectivity qualified

**WARRANTED_EXACT_FINITE_ENVELOPE:** [CI 37873317630](https://github.com/metalogiclabs/mathgraph/actions/runs/37873317630) SUCCESS at [source 1fd7e5c](https://github.com/metalogiclabs/mathgraph/commit/1fd7e5c81c3157ea6fc73bc23421b9df2577c4be). `FiniteEnvelope.lean` gives an exact finite product encoding of control state, input-head positions, bounded work-head positions and bounded Boolean work-tape values. Its verified cardinality is `(q+1) * (n+2)^h * (2s+1)^w * 2^(w*(2s+1))`. Configurations identical on these components and blank outside the window are proved equal. Independent Leanchecker and target axiom checks passed (cardinality proof permits only the three standard axioms).

**WARRANTED_NO_PREHALT_REPETITION:** [CI 37873397269](https://github.com/metalogiclabs/mathgraph/actions/runs/37873397269) SUCCESS at [source 10808018](https://github.com/metalogiclabs/mathgraph/commit/10808018c385580e13c9cfc9897df72677a96e47). With deterministic transition, first halting at time `H` forbids revisiting any full configuration at distinct `t<u<=H`. Kernel and Leanchecker passed with `propext` and `Quot.sound` only.

**CANDIDATE next frontier:** the source of an additional unvisited-work-cell blankness lemma and a generic finite-code first-halt bound is at [2aa4504](https://github.com/metalogiclabs/mathgraph/commit/2aa4504afbc4797f90df5d1c2c7f26cc303b2fde), currently under [CI 37873819868](https://github.com/metalogiclabs/mathgraph/actions/runs/37873819868). Earlier failed attempt [37873618238](https://github.com/metalogiclabs/mathgraph/actions/runs/37873618238) had an unsplit `Machine.output` case; this was corrected, but no new theorem is promoted before green CI.

**Precise unclosed bridge:** prove a radius bound on `workPos` from `Machine.spaceThrough` using one-step adjacency, plus tape support; instantiate a faithful finite encoding and translate `s=O(log(n+2))` into a polynomial cardinal bound. Only then is the classical finite-configuration-time argument complete in Lean. The exact OAI main theorem's strict Comparator evidence remains independently warranted, but the conventional TM-model equivalence remains UNKNOWN.

## 2026-10-09 — Verified finite-code first-halt bound and work-cell support

**WARRANTED_SOURCE_SUPPORT:** [CI 37873819868](https://github.com/metalogiclabs/mathgraph/actions/runs/37873819868) SUCCESS at [source 2aa4504](https://github.com/metalogiclabs/mathgraph/commit/2aa4504afbc4797f90df5d1c2c7f26cc303b2fde). The new `unvisited_work_cell_is_blank` theorem, proved by induction over the exact `M.run` recurrence and the distinct write-at-head semantics, ensures that any work-tape position never visited before time t still contains the initialized `false` bit at time t. Exact Lean 4.34.1, Mathlib, Leanchecker and target axioms qualified.

**WARRANTED_CONDITIONAL_FINITE_STATE_TIME_BOUND:** Same source and CI verifies `first_halt_lt_card_of_faithful_encoding`: For any finite encoding type α and function from full configurations into α that is provably faithful on the execution's first H+1 configurations, if a deterministic machine first halts at H, then `H < Fintype.card α`. It applies the previously verified no-repeat lemma to derive an injection from the prefix `Fin (H+1)` to α. This is a generic finite-state halting theorem, not an already established OAI LogSpace time bound.

Earlier [CI 37873317630](https://github.com/metalogiclabs/mathgraph/actions/runs/37873317630) independently verified the exact bounded-configuration envelope cardinal `(q+1)*(n+2)^h*(2s+1)^w * 2^(w*(2s+1))`, and [CI 37873397269](https://github.com/metalogiclabs/mathgraph/actions/runs/37873397269) verified full-configuration nonrepetition before the first deterministic halt.

**Unclosed mathematical glue:** (a) use unit-step work-head movement and the cardinal of visited positions (`Machine.spaceThrough`) to prove that every reachable head location is in a window with radius bounded by O(S), (b) derive all tape bits outside it remain false using the new support lemma, (c) construct the actual faithful encoding into the finite envelope and instantiate the first-halt bound, (d) prove the envelope size is polynomial for `S = c*Nat.clog 2 (n+2)`. Model-equivalence with ordinary Turing machines is a separate higher-level theorem; it is still UNKNOWN.
