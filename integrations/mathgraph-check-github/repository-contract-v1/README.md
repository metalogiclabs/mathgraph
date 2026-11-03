# Fixed L4YAML repository contract

Research qualification of one unchanged contract across independently pinned,
multi-file owned-fork PRs. This is separate from the deployed Ledger-only App.

The runner discovers changed Scripts modules and their transitive Scripts
imports, builds them in a clean trusted Lake project, and runs the same frozen
1,367-case regression corpus on base and head. All other changed paths are
reported as uncovered. The new CLI may compile without its runtime behavior
being tested. No whole-PR correctness or scientific intent claim is made.

## Reproduce

Use a clean checkout of the qualified controller revision, Linux Docker and the
`leanprover/lean4:v4.35.0` toolchain installed by elan. No OpenAI key or GitHub
write permission is needed. Public GitHub reads occur before isolated execution.
Each output path must be new.

```bash
GITHUB_SHA="$(git rev-parse HEAD)" python3 integrations/mathgraph-check-github/repository-contract-v1/run.py \
  --pr 19 \
  --base 809014dd314dbcf0ccf1dd23ec9cbf84ee4830df \
  --head 815695d634e50d4c336919aa9e60392dba81f1e9 \
  --output contract-results-19
```

For another public `metalogiclabs/L4YAML` PR, change only the PR number, exact
base/head inputs and output directory. Do not change the contract or expected
corpus. The tool currently rejects other repositories.

`result.json` gives source/controller identities, contract/corpus hashes,
compiled roots, both-arm observations and uncovered paths. Exit zero means
the audit completed; it can include `NEW_FROZEN_PROBE_FAILURE`. It does **not**
mean the PR passes. UNKNOWN or stale source exits nonzero. The workflow is an
audit execution workflow, not the source PR's approval gate.

## Boundaries

- The contract was frozen at `5e8db3da8bdf2d082b89af107f1da2e219f0b5e9`
  before the fresh PR213 diff was inspected.
- The reference corpus construction comes from controller
  `528aa7d4d60651afab4efafb3a00425794ba56fe`; `corpus.sha256` binds the exact
  previously verified corpus. References are finite prior-behavior candidates,
  not independent authority on intended semantics.
- Fixed native commands, original source, external probes and trusted Lake
  configuration cannot be selected or edited by the source PR. Containers have
  no network or credentials; source/probe/Lakefile mounts are read-only. These
  tests do not qualify arbitrary hostile-source sandbox security.
- Diffs are acquired by exact Git revisions, not the live PR file list.
  Incomplete comparisons (300+ files or more than 250 commits), missing required
  modules and unsupported imports remain UNKNOWN. Renames retain base paths.
- The fresh snapshot is fork PR19. PR20 is a deliberate two-file regression
  that preserves existing source guards; PR21 withdraws it. These are labelled
  sensitivity controls, not discovered upstream defects or blind comparisons.
- The current hosted App's admission/deployment are unchanged. External
  installation and broader scientific proof audit remain unqualified.
