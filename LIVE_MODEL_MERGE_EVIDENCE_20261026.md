# Authenticated model-selected evidence for three merge-review decisions
**26 October 2026 — independently source-native qualified; not a repository merge**

## Authority

- **Successful authenticated run:** [GitHub Actions #40289255597](https://github.com/metalogiclabs/mathgraph/actions/runs/40289255597). Isolated workflow trigger commit `79a4afffb65aae842dc4605798f0e1a808d3c4b1`; executed exact verified standalone source commit `7bd3679543b5fd4d67bc4555cd45dcc13876e8e7` (not a mutable branch ref).
- **Independent offline acceptance check:** [GitHub Actions #40289131662](https://github.com/metalogiclabs/mathgraph/actions/runs/40289131662), **54/54 tests** including mocked typed model reply, false obstruction rejection, stale receipts and pinned native source replay.
- **External source:** `pallets/itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd`, exact upstream Git blobs checked. All defects used in testing are **deliberately injected in isolated copies**; no upstream defect is alleged and no upstream files were modified.
- **Authenticated model:** Nebius Token Factory serving `nvidia/nemotron-3-super-120b-a12b` (NVIDIA Nemotron 3 Super).
- **Retained evidence:** [artifact #12635700459](https://github.com/metalogiclabs/mathgraph/actions/runs/40289255597/artifacts/12635700459), ZIP SHA256 `d437c7aaedb567849bd4a43c2edb052b54f8de1af9117a756a1209b8a8484f56`. Contents: model-observation-live-report.json and credential-free status JSON.
- **No credentials** present in uploaded report, HTML or repository. Public GitHub Actions log reflects secret environment only as `***`.

## Model choices and independent outcomes

| Scenario | Nebius request ID | Response SHA256 | Action admitted | Native test outcome | Final permission |
| --- | --- | --- | --- | --- | --- |
| Defective existing-green change | `5f3c3eff58a215b45df8c587f915dbf5` | `ad56608ed3171a60a745be6d0f188f2e1495ece7af5693e5e0077adb9813c26f` | cost-6 basis `00,f80000` | Expanded tests exit 1 — **REJECTED** | NONE |
| Correct reference initially UNKNOWN | `c618b16b1ffc85432176ad4a06b748b5` | `b55ff97daa3d0261f6a0e48a65a1846633e514a8fb4372c5d09611f7906477f5` | cost-6 basis `00,f80000` | Expanded tests exit 0 — **WARRANTED_BOUNDED** | REVIEW_ONLY_BOUNDED |
| Observation forbidden (only 3-byte permitted) | `3cb5457c3d566cc6503566c0b997d898` | `9876db7bc183aba36e891dadcbb82da03d176978a385e175e6f58f5d18469182` | typed OBSTRUCTION — `unstripped_padding` inseparable | No expanded experiment possible, **UNKNOWN** | NONE |

All three authenticated model selections were accepted on their first attempt. The model supplied only a *typed choice identifier* from a small, deterministic menu of source-derived candidate plans. The model could not invent arbitrary code, choose unpermitted probes, or assign final authority. A separate exact solver and native Python execution checked all selections. The successful correct-case receipt became **REJECTED** on a post-test byte change; rerunning tests on restored bytes reacquired **WARRANTED_BOUNDED**.

The successful decision is review-scoped: **no GitHub merge took place**.

## Causal negative evidence retained

- [Earlier live model-selected test #40288064254](https://github.com/metalogiclabs/mathgraph/actions/runs/40288064254): six Nebius attempts returned invalid multi-field plans; the verifier refused all three review cases.
- [Second live #40288583238](https://github.com/metalogiclabs/mathgraph/actions/runs/40288583238): model's initial finite ID request failed response-format admission.
- [Partial live #40288882359](https://github.com/metalogiclabs/mathgraph/actions/runs/40288882359): correct and defective cases passed native decision verification, but the observation-forbidden case returned an inadmissible choice twice.
- The successful version introduced a single semantic `OBSTRUCTION` action. An **independent negative test proves that choosing this action when a separating experiment exists is rejected**, rather than treating the keyword as a warrant. The final model proposal must still be admitted by the exact finite oracle.

These are not independent successful trials and no success-rate estimate is warranted from them.

## Limits and next meaningful transfer

The experiment demonstrates a real model choosing a source-derived observation plan for a three-case, predeclared mutation family and restricted observation grammar. It **does not** demonstrate automatic formation of the hypothesis space from an unfamiliar pull request, independent model generation of new test logic, broader SWE-bench advantage, or actual automated merge. An equally informed conventional mutation-testing selector matches MathGraph's minimum-cost finite basis in the existing controlled benchmark. The distinctive tested integration is **model-selected evidence acquisition + independent source/test-bound qualification + authority withdrawal + an explicit impossibility certificate**.

The next prospectively frozen task should come from an independently pinned unfamiliar project, with a source-native failure and unmodified holdout tests, and should compare equivalent model and test budgets. Do not claim that generalization has already been proved.
