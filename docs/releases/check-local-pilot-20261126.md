# MathGraph Check — local pilot candidate

**CANDIDATE / ADVISORY ONLY.** This packages existing retained checks and one
source-native telemetry conversion profile behind a single operator command.
Qualification belongs to the exact commit and run linked from the candidate PR.
Independent external operation, customer requirement approval and commercial
advantage remain unestablished.

## Inspect the supported scopes

Requirements: Node 24, Git, Python 3.10 or later, and GNU timeout for the L4YAML
adapters. L4YAML additionally requires the exact Lean 4.35.0 binary. The telemetry
profile uses only the Python standard library and does not require Lean.

```sh
node bin/mathgraph-check.mjs --capabilities
node bin/mathgraph-check.mjs --source-map
node bin/mathgraph-check.mjs --help
```

Use a detached checkout of the commit named by a successful qualification run.
A branch name is a locator and can move. Run output records the verifier commit,
entry-point hashes and whether the entry files match that commit. Check those
fields before relying on a candidate's qualification.

## Run one numerical boundary

For reviewed local OpenC3 source containing the documented Accessor interface:

```sh
node bin/mathgraph-check.mjs --profile telemetry-integer-identity-v1 \
  --repo /path/to/local/cosmos --base BASE_COMMIT --head HEAD_COMMIT \
  --out /path/to/new-result-directory
```

The 108 fixed cases exercise exact INT/UINT integer values, decimal strings and
arrays, plus specified fractional/None compatibility and invalid-input refusals.
The integer reference uses Python integers; large values are encoded as strings
in observations so JavaScript/JSON number parsing cannot round them.

Actual committed `openc3/python/openc3/accessors/accessor.py` bytes are loaded.
Only its ConfigParser import is removed and replaced by a refusing stub; all
function bodies are unchanged and source/projection hashes are retained. The
BOOL branch, full package/packet paths, wire/range enforcement, hostile-source
isolation and all-input correctness are outside the profile. This supplied
contract does not automatically establish customer or mission intent.

Known calibration: OpenC3/cosmos [PR #4433](https://github.com/OpenC3/cosmos/pull/4433),
original `791b3492ed8d6a7f39bd240837fc601ac491278e`, repaired
`429c784f7267ce6b8a0b03c90c213b397282644b`. Acquire and review source before
checking; the operator command does not clone repositories or install packages.
Qualification replays original, repair, withdrawal, unchanged, missing-revision
and missing-tool controls. These are known-source controls, not blind discovery.

## Run the five existing L4YAML profiles

```sh
node bin/mathgraph-check.mjs --profile l4yaml-retained-v1 \
  --repo /path/to/local/L4YAML --base BASE_COMMIT --head HEAD_COMMIT \
  --out /path/to/new-result-directory --lean /path/to/lean-4.35.0/bin/lean
```

This calls the existing catalogue dispatcher: 19 XML acceptance cases, eight
JUnit status cases, five keyed-agreement cases, 18 refusal/apparatus cases and
four capstone-axiom controls. Its 104 rows are candidate-prompt accounting;
17 prompts have finite mappings and 87 have no executable connected to that
dispatcher. They are not 104 qualified detectors. Explicit `--profiles` omissions
remain NOT_RUN and prevent a complete all-profile result.

## Read the result and recheck changes

- `report.md`: the requirement, observations, source revisions, witness and limits.
- `result.json`: source/method identities, observations, dependencies, costs and
  raw-evidence hashes. An identity is not an independently authorized requirement.
- Profile evidence: exact acquired source/projection, requests, receipts and logs.

Exit 0 means finite head agreement, 1 a completed discrepancy, and 2 UNKNOWN,
incomplete/omitted checks or an invocation error. Output must be a new directory;
earlier failures and historical results are not overwritten. An observation from
one source or requirement does not qualify a changed one. Rerun the same command
against the new exact pins and preserve both results. The existing pure Monitor
has independent changed-dependency and unaffected-claim tests; it is separate
from the live Worker's monitor path.

No command grants deployment permission, fixes source, publishes GitHub checks,
uses model/App credentials or activates a hosted installation. Execution is for
reviewed local source and is not an untrusted-code sandbox. Local process limits
are not a network or operating-system isolation claim.

## Candidate lineage and hosted boundary

The [source map](check-local-pilot-20261126.source-map.json) reconciles public
main, the observed live Worker annotation, the self-serve controller pin, RC1 and
the retained-profile head. The candidate starts from
`dd3369c772c77fb5dd5db1056cf7f13032525dfa`, which already has the same pure Monitor
and trust-boundary tests as RC1 `70733f1...`; it does not merge unrelated research.
Main, hosted source pins, Worker deployment and App permissions are unchanged.
The existing read-only retained-profile workflow qualifies this candidate and
archives the local-operator and L4YAML-operator evidence separately.

## External operator handoff

The next test requires a consenting external engineering owner and an explicit
requirement on a fresh change. Record setup/review/requalification minutes,
compute costs, failed attempts, false alarms, unresolved scope, the actual decision
and whether the operator wants to use Check again. Compare with that team's
strong conventional process with matching information and coverage. Assistance
must be recorded; a second checkout or another machine is not an independent
human-operator trial. No outreach or customer installation is included here.
