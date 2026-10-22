# V3 prospective bounded result — negative control

Source: third-party Pillow==11.3.0, library ImageFile.Parser. CI run: https://github.com/metalogiclabs/mathgraph/actions/runs/39698322525 ; head commit 8861259f06a5d9c64b27cb20c393429eb66bd5cb.

Frozen lexical+signature admission rule: `frozen_admission.py` commit 9d087d55e1f5a9665e750cde9785e9758b0ecd05 (committed before target-specific probe). Only public zero-required-argument callable methods with a positive reading verb and no effect-word may be admitted. This is a heuristic, not a sound source-authority proof.

Third-party target: synthetic PNG with payload corruption; external data oracle recomputes PNG chunk CRC32 without invoking Pillow. The target and corruption generator were designer-chosen, therefore not an untouched hidden task.

Result in CI: `CANDIDATES []`; `SCORES {} WINNERS []`; `RESULT OBSTRUCTED_IN_FROZEN_GRAMMAR`. CI concluded SUCCESS because the program intentionally treats obstruction as a valid audited output. No held-out checks occurred. This MUST NOT be described as a passed acquisition experiment.

Classification: REJECTED — claim that the frozen V3 admission rule acquires a useful observation on this target. WARRANTED (within this runtime boundary) — method-admission produced an obstruction. UNKNOWN — source-authorized acquisition through more general effect-safe action sequences.

Main diagnosis: zero-argument method inspection does not model stateful `feed(...) → close()` parser protocols, nor can a name/docstring denylist establish absence of side effects. A fully informed conventional planner can use the straightforward `zlib.crc32` PNG chunk oracle; no benefit established.

Cheapest next decisive test: freeze a source-derived bounded state machine over stateful APIs including sequence preconditions and effect constraints; compare against a fully informed baseline; keep the current failed policy unchanged as an ablation. A true blind unfamiliar source requires independent pre-registration and source choice after freezing.
