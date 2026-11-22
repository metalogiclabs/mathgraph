# Four retained profiles and the 104-prompt catalogue

## Objective and declared boundary

Turn the already witnessed EA01 aggregate-comparison and EA03 false-refusal
mechanisms into retained executable checks, alongside the XML and JUnit status
profiles. Every invocation accounts for all 104 candidate prompts while keeping
bounded observations, missing evidence and unsupported families distinct.

This is known-case engineering qualification. It establishes neither blind
discovery nor a complete failure taxonomy, full-project proof, four-backend
parser agreement, external human utility or a measured 10x improvement.

## Frozen subjects

| Subject | Identity and role |
| --- | --- |
| Original | `14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f`, audited L4YAML integration |
| Outcome candidate | `c06ec22e49c139a47a1ef08c96eb6726bb2b32ee`, published child of the original; independently checked here |
| Outcome tree | `a1d36507b49c60f6734f3450de1e6efe04e9185d` |
| Production library subtree | `4197c0b6f2fb369e9806ca486d38aef87b077c81`, preserved by the outcome and combined candidates |
| Combined candidate | Deterministic actual local child of the outcome candidate, changing only the JUnit error condition in `Tests/SuiteRunner/Reports.lean` |
| Combined Reports SHA-256 | `f9a3e37c8f903787f157a66747291c057a757a9c5c380a014dcc0fe1a197606a` |
| Missing-source control | Deterministic local child removing Reports and Main; all four profiles must return UNKNOWN |

The qualifier uses a private Git index. It records the candidate commit object,
tree, one-file patch and source bytes, and verifies that the caller's branch,
checkout and index are unchanged. These local candidates are not upstream PRs.

## Expected controls, declared before final qualification

| Comparison | XML discrepancies | Status discrepancies | Per-case discrepancies | Refusal discrepancies |
| --- | --- | --- | --- | --- |
| Original → outcome candidate | 0 → 0 | 4 → 4 | 2 → 0 | 13 → 0 |
| Original → combined candidate | 0 → 0 | 4 → 0 | 2 → 0 | 13 → 0 |
| Combined → original withdrawal | 0 → 0 | 0 → 4 | 0 → 2 | 0 → 13 |
| Combined → combined | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| Combined → missing source | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

Counts are fixed input discrepancies, not distinct defects or covered catalogue
families. The partial repair is deliberately insufficient: its remaining JUnit
error discrepancies must prevent an all-profile agreement. The two EA01 failures
are an equal-total swap across presets and a nondefault-preset-only swap.
Identical, reordered and different-total controls prevent an always-reject
comparator from qualifying. EA03 retains actual process exits, missing program,
signal and elapsed-deadline controls plus exact and contradictory marker cases.

## Replay

Fetch the exact original from `nasa-jpl/L4YAML` and outcome candidate from
`metalogiclabs/L4YAML`, then use a clean committed MathGraph checkout:

```bash
python3 experiments/check-catalogue-v1/qualify.py \
  --repo /path/to/local/L4YAML \
  --out /path/to/new-qualification-directory \
  --lean /path/to/lean-4.35.0/bin/lean
```

The Actions workflow installs the exact Lean version, runs contract tests,
replays the previous XML/status qualifications and then this campaign. Artifacts
include progress summaries even on ordinary failures, every profile's fresh
receipts, raw observations and a SHA-256 inventory. No method or expectation is
retuned based on qualification outcomes.

## Result status

**WARRANTED within the finite execution boundary:** all five declared campaigns
completed on frozen executable implementation
`e032401ff6099492f4c0f252af8d3123f330512f`, tree
`423718962be52449022059512b418a3245366943`, with exactly the expected discrepancy
vectors above. The local campaign took 208.533 seconds; its combined comparison
took 54.570 seconds. Independent review verified 2,012 inventory hashes, 20
profile receipts, 400 individual observations and 144 raw process records.
Profile methods were unchanged across all five campaigns; runtime identities
were unchanged within each profile across the four executed comparisons.

The actual combined candidate is `845873be23f6603530bd434d1b91a7409eb92239`, tree
`ff47e3a4244a7b7b103b233114baef41ff28522d`. The missing-source child is
`f3854aa8d6ccdc66a2d04c8661e0078d90a2bcd7`.

[Hosted run 44990119580](https://github.com/metalogiclabs/mathgraph/actions/runs/44990119580)
independently reproduced the five outcomes in 162.548 seconds (combined
comparison 40.732 seconds). It also passed 664 Node tests with 16 explicit skips,
74 Python tests and the separate 9/9 and 4/4 native control suites. Those native
suites repeat some tests skipped in the broad job; these are not disjoint totals.

**Artifact-transport correction:** that first hosted catalogue archive
`14741209279` has SHA-256
`4382752949a4f38c4dcab454ae6446b48099c0253c882517bd21968f79392518`, but omitted
136 controlled backend files below `.lake`. All 1,876 present inventory entries
matched; the archive is incomplete and must not be described as fully retained.
The workflow now explicitly includes hidden fixture files. This changes artifact
retention, not the four executable methods, cases, expectations or budgets.
The [PR #285 checks and artifacts](https://github.com/metalogiclabs/mathgraph/pull/285/checks)
identify fresh hosted replays of the corrected workflow, each with its own
source-qualified verifier receipt and complete-inventory requirement.

Every run accounts for 104 prompts, with 16 mapped finite facets and 88
unsupported by this command; no family is promoted to complete coverage. The
partial repair leaves four status discrepancies, withdrawal restores the
original 0/4/2/13 vector, and unavailable source makes all four profiles UNKNOWN.
The original refusal vector consists of 12 false PASS results and one ordinary
FAIL that should instead be an apparatus ERROR, not 13 false-green results.
Model calls were zero. External human utility and comparative value remain
unmeasured and do not block execution.

### Retained prequalification lineage

Review found and closed same-count/wrong-case admission, wrong-revision summaries
inside UNKNOWN results, inaccurate green coverage ledgers, unpropagated native
apparatus errors and a deadline fixture that could naturally return the timeout
code. Their negative controls are retained in the tests. The actual timeout
fixture now naturally exits 0, so only the enforced deadline yields 124.

The first frozen local campaign used local commit
`932a5d025ee4960eafaabac4900c2a7742b15fea`, tree
`73570d0e18e66fc31322e7dfbf9844130c3eaa73` (the same tree is preserved in published
predecessor `f5c4a2903ed86bb8a08aa128e3dd8b68b518111e`). It was deliberately
interrupted with exit 130 during the first comparison after review found that an
empty or contradictory displayed agreement could be accepted from its HTML
class alone. Its progress record remains INCOMPLETE; it supplies no campaign
qualification. The repaired method binds visible terminal, verdict and preset
claims to the supported language and retains the reproducing tests. Later
qualification uses a fresh output directory and an unchanged frozen method.

The initial EA03 observer-development run also returned UNKNOWN on an observer
syntax error. It was corrected before the frozen campaign; no target behavior
was inferred from that setup failure. No expectations or execution budgets were
retuned to erase these failures.
