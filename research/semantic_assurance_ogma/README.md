# Real-source Ogma native semantic-assurance adapter

This isolated research experiment connects a source-specific native verifier to
the unchanged `mathgraph_check.warrant_resolution` module. It tests an authentic,
previously known NASA FRET/Ogma case, not a newly discovered defect or a blinded
benchmark. The protocol was committed before the adapter's implementation and
execution, after the historical case and expected boundary behavior were known.

The independently authored source is FRET commit
`cf0f913cc15c41705e803593297e89cd6056b839`, requirement `LPC_KIAS_0`:
"The vehicle shall always satisfy kias >= 0.0". Its published FRETish text and
structured semantics fix the restricted interpretation used here. They are
case-study authority, not evidence of an approved operational requirement.

Original Ogma-generated C uses `> 0`; corrected C uses `>= 0`. Both are recovered
byte-for-byte from source-pinned, digest-checked historical Actions archives.
The original FRET example has four blank Copilot assignments. Both native
monitors used the same diagnostic input supplying those assignments without
changing the requirement. This experiment does not claim that the unmodified
whole original project compiles.

Fresh GCC compilation executes each of 2,800 traces independently for each
monitor. The domain comprises seven binary32 values, including signed zeros and
the smallest positive/negative subnormals, and lengths one through four. A C
harness reports actual input bits and cumulative callbacks. An independent
Python history oracle provides expected callbacks. Every saved native
certificate row is verified by executing a fresh monitor process again;
self-hashes and claimed success labels are insufficient.

The adapter admits only its exact source, artifact, signal, finite domain and
observation frame. Evidence withdrawal disables the affected routes. A
counterexample establishes `REJECTED_TRANSFER`; missing evidence gives
`UNKNOWN`, without inferring a refutation. Valid bounded observations do not
authorize deployment. No claims enter MathGraph's terminal-form kernel.

The direct ledger receives exactly the same externally qualified evidence and
revocations. A separate prefix-based oracle is checked during shared evidence
qualification. Both decision arms may reuse the resulting qualified fact; the
ledger does not call the graph resolver. Both arms share acquisition deliberately; costs
reported are shared native acquisition and separate post-acquisition decision
time. Human investigation, adaptive discovery, implementation effort, and
economic superiority are unmeasured. A verdict tie must be retained.

## Replay

Place the three original inputs in a directory:

- `LPC_full_reqts_and_vars.json` from the pinned FRET source.
- `fret_ogma_postcensus_native_44435948686.zip` (artifact 14489079218).
- `ogma_greater_boundary_fixed_44439625075.zip` (artifact 14491054038).

All input digests and source authorities are frozen in `protocol.json`.

```bash
python3 research/semantic_assurance_ogma/replay.py --inputs /path/to/inputs --out /path/to/results
python3 -m pytest tests/test_mathgraph_warrant_resolution_core.py research/semantic_assurance_ogma/test_replay.py -q
```

This is a finite native replay under declared compiler/runtime assumptions,
not an unbounded proof about C, a Lean proof of the adapter, fresh native
Ogma/Haskell/Copilot generation, sensor correspondence, or mission approval.
