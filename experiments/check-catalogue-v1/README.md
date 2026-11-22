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

Implementation and native controls are being qualified. No completed campaign
is claimed in this prequalification record. Exact implementation/run/artifact
identities and outcomes will be appended after their evidence is inspected.
