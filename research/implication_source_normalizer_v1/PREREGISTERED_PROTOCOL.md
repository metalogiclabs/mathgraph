# Implication-aware source-only normalization on five unseen Qwen holdouts

This technical protocol and manifest are committed **before** any translated
Rust target has been opened. Input C/ACSL files were inspected; the generated
Rust target paths were identified from directory metadata only. Selection is
hand-picked (not random), which limits extrapolation.

Source revision: ZoneOut12/C2VerifiableRust@6c8b35b5dd8e94473b713b7edcf4bf4142f214e3.

The conservative extractor recognizes:
- scalar max as membership OR plus lower bounds AND;
- array maximum as universally bounded above AND existentially attained;
- all-even Boolean predicate using complete disjoint quantified behaviors;
- even-index zeroing as a guarded quantified implication; it must NOT infer
  unmentioned preservation of odd-index elements or equality of full arrays;
- guarded array doubling, respecting source index preconditions.

The source-only parser can only authorize those exact bounded formula
shapes; unrecognized, weakened, ambiguous or syntactically different
contracts must produce UNKNOWN rather than guessed obligations.

Fixed finite corpus: scalar max all 49 ordered pairs in [-3..3]^2;
three mutable/read-only array family cases each 780 arrays (length 1..4,
values -2..2), plus 5 guarded doubling arrays [0,...,n-1], n=1..5.
Total = 2394 predeclared source-valid inputs, three sparse source-generated
probes per family (15 probes) of which zero are target-informed.

After a separate green source-only run seals the packet, unblind the
corresponding untouched Qwen generated Rust, compile and run native C and
Rust on all declared source-valid inputs. A test is a failure ONLY when the
source-defined postcondition is violated (or specified input frames change);
avoid the converse mistake of rejecting benign unconstrained output.
For mutation cases, partial specifications may admit many valid outputs.
If a translated source is noncompilable without repairs, report UNKNOWN,
not a migration defect. Publish source/proof lineages and retained outputs.

Matched conventional baseline independently checks the original source,
target, full corpus and all necessary postconditions, using manually
specified but equally informed formulas. Compare detection and coverage,
false rejections, wall/CPU time when measured; do not claim superiority
from positive-only data, seeded faults or source-specific test generation.

No JPL/private collaborator details, secrets, credentials or internal
relationship notes should appear in public GitHub.
