# Paired MathGraph assurance pilot — two existing research toolchains (2026-11-20)
Status: FROZEN RETROSPECTIVE MECHANICS PROTOCOL, not a preregistered blind discovery claim.

Objective: apply EXACT SAME separately specified distinction-sufficiency and actual-fidelity diagnostic algorithm to
(i) Nicolas Rouquette's L4YAML Lean 4 Core Schema resolution and
(ii) Kristin Y. Rozier's NASA FRETish -> C2PO -> native R2U2 pipeline.
Both cases and likely failure modes are historically known; successful matched controls DO NOT show competitive superiority.

External normative/source anchors:
A: YAML 1.2.2 §10.3.2 https://yaml.org/spec/1.2.2/#1032-tag-resolution, conditional on deliberately applying Core Schema to an untagged *plain* scalar.
Exact production original reference nasa-jpl/L4YAML@4f31fef1f18e48b2204322b9a257b905340768c6 and
candidate nasa-jpl/L4YAML@d8f9865f222f75a15ffbd766837d340ba627d12a. Only the tag is scored; numeric-value correctness and the full YAML parser remain out of scope.
B: published FRETish example "whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST" and its
explicit FRETish parser-derived original [0,7] temporal formula.
Actual FRET source NASA-SW-VnV/fret@cf0f913cc15c41705e803593297e89cd6056b839,
C2PO/native R2U2 R2U2/r2u2@2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a,
script pinned to metalogiclabs/mathgraph@2b0e21e94e64ca54ff35c1d4572c60b3b6049720.
The [1,7] program is a research-only constructed challenger, not an authorized FRET export or operational repair.

Declared YAML domain X (12 plain scalars, all tag-only):
1_000:str, 1000:int, 0x:str, 0:int, 1.:float, 1.0:float, true:bool,
hello:str, 0x3A:int, null:null, .inf:float, yes:str.
No post-result changes or deletion of hard cases; mismatches are retained.

Declared rocket domain: four exactly eight-sample, complete Boolean traces in original PR #282:
simultaneous BOOST & COAST at t0, next-tick COAST, no COAST, no BOOST.
For each t=0..7 P(trace,t)= (!BOOST[t]) OR (there exists i in [t,min(t+7,7)] with COAST[i]).
This finite-trace interpretation comes from actual source's FRETish [0,7] output;
not an independent mission-owner interpretation of physical rocket behavior.
Source maps and compiled binaries must be rechecked by original pinned native runner.

Common analysis: q is the actual observed output tag for YAML, or full case/time/input trace for FRET.
Test pairwise q(x)=q(y) => P(x)=P(y); test d(q(x))=P(x). Compare original,
source-derived repaired vs research-mutated decisions and a separately programmed
conventional all-pairs/all-points checker with identical P/X/source/raw observations.
Conventional scripts not an independently appointed human reviewer; no acquisition-cost or human advantage can be scored.
Report verified actual mismatches, source-linked witness, repair class, false alarms,
harmless q collisions, negative controls, exact source pins, timings and all restrictions.
Classification: insufficient representation if consequential q fibre conflict is witnessed; otherwise
implementation fidelity mismatch if P fails and finite domain sufficiency passes.
Since q for rocket retains original full trace+temporal position, a wrong [1,7] formula
is a decoder/policy mismatch, not a lost-input collision.

Actions forbidden: upstream changes, private access, collaborators contacted, production deployment, automatic source repair,
owner approval inferred from published examples, paper/claim generalization, new ontology.
Warrant ceilings: "WARRANTED_BOUNDED" only for exact pinned code/output/domain and logged CI;
"Nicolas FGM" is NOT tested; "Kristin's operational mission requirement" NOT approved.
Human oracle adjudicator (2 people) NOT_RUN, independent human conventional investigator NOT_RUN,
publisher/mission owner's action permission UNKNOWN, competitive superiority UNKNOWN.
