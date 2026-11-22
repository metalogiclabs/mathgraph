# Axiom admission: bounded candidate (v0)

This experiment is **not** yet wired into the 104-row catalogue dispatcher.
It is a controlled test of whether a Lean theorem's reported dependency set
agrees with an explicit admission contract. It makes no claim about all Lean
projects, independent kernel soundness, or all transitive trust boundaries.

Run:

```sh
python3 -m unittest discover -s experiments/check-axiom-admission-v0 -p 'test_*.py' -v
python3 experiments/check-axiom-admission-v0/run.py --lean lean --out /tmp/new-axiom-receipt
```

The second command requires Lean and an output directory that does not exist.
The result is `result.json`. The script records fixture SHA-256, stdout/stderr
SHA-256, exit status and observed axiom names. It does not currently retain
the complete raw output or Lean executable digest, and does not bind to a
checked-out Git revision of an external project.

Controls: benign; explicitly declared extra axiom; unauthorized private axiom;
repaired source; withdrawal of the repair. Each source is a fixed standalone
fixture; the repair and withdrawal are controlled fixture variants, not a
patch/revert of a production implementation. Lean's `#print axioms` output is
the trusted evidence source. The private declaration's generated name is
not assumed in advance.

Promotion requirements:

1. Hosted Lean 4.35.0 execution and independently inspected receipt.
2. Capture raw output, toolchain identity and exact source revision.
3. Establish an actual production before/after/withdrawal witness, not only
   distinct synthetic fixtures.
4. Wire a fifth profile with fixed case IDs into `catalogue.mjs`,
   `run.mjs`, method identity and dispatcher tests.
5. Requalify the existing four profiles and retain their prior boundaries.
6. Map catalogue prompts editorially, without implying whole-family coverage.

If any tool, output format or dependency evidence is missing, return UNKNOWN.
