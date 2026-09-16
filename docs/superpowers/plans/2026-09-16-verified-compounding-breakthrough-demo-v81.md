# V81 Verified Compounding Intelligence Breakthrough Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one self-contained GitHub Actions demo that validates the authoritative MathGraph developmental evidence lineage, runs a fresh prospective V81 developmental chain, and emits bounded machine-readable verdicts for verified development, autonomous reuse/expansion, global optimality, and compounding economics.

**Architecture:** Add a small canonical artifact layer for `VerifiedCapabilityBlock`, `VerifiedObstruction`, and `VerifiedDevelopmentTransition`; add one V81 runner that composes historical-evidence validation with a fresh ten-operation prospective developmental controller; add tests that freeze all trust and compounding gates; add one workflow that runs the tests and then the full demo and uploads the resulting evidence pack. Existing V72–V80 experiment code is reused rather than copied, and historical experiments are validated by immutable identifiers rather than mislabeled as fresh reruns.

**Tech Stack:** Python 3.12, stdlib dataclasses/hashlib/json/pathlib/importlib, pytest, existing MathGraph verifier/experiment modules, cvc5==1.3.1 in CI, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-16-verified-compounding-breakthrough-demo-v81-design.md`

## Global Constraints

- No PR creation.
- Every accepted claim remains behind a verifier/checker boundary; advisory memory cannot promote truth.
- Historical runs must be labeled as historical validation, not fresh reruns.
- V81 source generation must occur only after protocol freeze.
- Fresh V81 source grammar must be structurally outside all previous synthetic streams: exactly ten binary operations per source.
- Retained budget remains exactly 5.
- Developmental action grammar remains exactly one retained-node swap.
- No retraining, budget change, or action-language widening after fresh generation.
- Each claimed endpoint must equal the exact fixed-budget global optimum.
- A larger horizon with zero residual must produce `REUSE`, not forced change.
- A positive residual may be repaired only by strict positive verifier-delta moves; if one-swap cannot reach global, emit `ACTION_LANGUAGE_EXPANSION_REQUIRED` and fail the fresh developmental-cycle gate.
- Compounding is awarded only when the warm path reaches the same exactly certified endpoint with fewer verifier checks and an exact counterfactual establishes causal responsibility for at least one saving.
- If compounding gates fail but developmental gates pass, emit an accumulation-only verdict rather than forcing the stronger claim.

---

### Task 1: First-class developmental artifact schemas

**Files:**
- Create: `mathgraph/developmental_artifacts.py`
- Create: `tests/test_developmental_artifacts.py`

**Interfaces:**
- Produces: `VerifiedCapabilityBlock`, `VerifiedObstruction`, `VerifiedDevelopmentTransition`, `stable_artifact_hash(obj) -> str`, `validate_capability_block(...)`, `validate_obstruction(...)`, `validate_transition(...)`.
- Consumes: stdlib only.

- [ ] **Step 1: Write failing schema tests**

```python
from mathgraph.developmental_artifacts import (
    VerifiedCapabilityBlock,
    VerifiedObstruction,
    VerifiedDevelopmentTransition,
)


def test_capability_block_hash_is_stable_and_scope_is_explicit():
    block = VerifiedCapabilityBlock(
        capability_id="cap:test",
        applicability={"source_family": "fresh_v81"},
        action={"kind": "retain_round1_node", "node_id": 7},
        verifier_boundary="replay_verified_critical_pair",
        certificate_refs=("sha256:abc",),
        provenance=("v81:fresh:source:1",),
        dependencies=("source",),
        scope={"horizon": 2, "budget": 5},
        causal_evidence=("warm_cold_counterfactual",),
        persistence_hash="sha256:def",
    )
    assert block.stable_hash() == block.stable_hash()
    assert block.to_dict()["scope"]["budget"] == 5


def test_obstruction_requires_positive_residual():
    with pytest.raises(ValueError):
        VerifiedObstruction(
            obstruction_id="obs:test",
            prior_state=(1, 2, 3, 4, 5),
            prior_scope={"horizon": 2},
            extended_scope={"horizon": 3},
            exact_global_old=100,
            persistent_value_new=120,
            exact_global_new=120,
            residual=0,
            provenance=("v81",),
        )


def test_transition_rejects_admitted_nonpositive_delta():
    with pytest.raises(ValueError):
        VerifiedDevelopmentTransition(
            transition_id="dev:test",
            from_state=(1, 2, 3, 4, 5),
            proposal={"drop": 1, "add": 6},
            verifier="exact_frontier",
            delta=0,
            admitted=True,
            to_state=(2, 3, 4, 5, 6),
            causal_witnesses=(),
            exact_optimality_status="unknown",
        )
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `pytest tests/test_developmental_artifacts.py -q`

Expected: import failure because `mathgraph.developmental_artifacts` does not exist.

- [ ] **Step 3: Implement immutable schemas and stable hashing**

Implement frozen dataclasses with `to_dict()` and `stable_hash()` methods. Validation rules must include nonempty IDs/provenance, positive obstruction residuals, and `admitted=True => delta>0`.

- [ ] **Step 4: Run schema tests**

Run: `pytest tests/test_developmental_artifacts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mathgraph/developmental_artifacts.py tests/test_developmental_artifacts.py
git commit -m "Add verified developmental artifact schemas"
```

### Task 2: Historical evidence lineage validator

**Files:**
- Create: `mathgraph/breakthrough_lineage.py`
- Create: `tests/test_breakthrough_lineage.py`

**Interfaces:**
- Consumes: exact immutable identifiers for V66, V72–V80 and canonical SAIR pack metadata.
- Produces: `historical_lineage_manifest() -> dict`, `validate_historical_lineage(repo_root: Path) -> dict`.

- [ ] **Step 1: Write failing lineage tests**

Test that the manifest includes stages `trust_boundary`, `sair_official_pack`, `v66`, `v72`, `v73`, `v74`, `v75`, `v76`, `v77`, `v78`, `v79`, `v80`; that V80 identifiers equal run `35058339100`, commit `6cf0db1455e517899fc76dbb4bde6087f8ca1204`, artifact `10432568044`, protocol SHA `9eb6155def95e3a6cedc324ed31decc49434e1956fe54da730703c36d2b3be2e`, developer SHA `82a884cf7b233b305f5fe3f7ec7f79e652cfd63ea0ad9e370bf0f53acbf92eed`; and that V79 is classified as post-hoc negative calibration rather than a pass for action-language expansion.

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/test_breakthrough_lineage.py -q`

Expected: module import failure.

- [ ] **Step 3: Implement the lineage manifest**

Store exact run IDs, commit SHAs, artifact IDs, verdicts, freshness classification, claim boundaries, and whether each stage is `authoritative_historical`, `posthoc_calibration`, or `prospective`.

- [ ] **Step 4: Implement repo-local validation**

Validate that canonical files referenced by the lineage exist on the branch and that embedded authoritative hashes in V77/V78/V80 scripts still match the manifest. Missing external artifacts are reported as `UNVERIFIED_IN_THIS_RUN`, never silently promoted.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_breakthrough_lineage.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add mathgraph/breakthrough_lineage.py tests/test_breakthrough_lineage.py
git commit -m "Add authoritative breakthrough lineage validator"
```

### Task 3: Fresh V81 prospective developmental experiment

**Files:**
- Create: `experiments/verified_compounding_breakthrough_v81/run.py`
- Create: `tests/test_verified_compounding_breakthrough_demo.py`

**Interfaces:**
- Consumes: V80 controller primitives and V72 frozen proposer via importlib; `VerifiedCapabilityBlock`, `VerifiedObstruction`, `VerifiedDevelopmentTransition`.
- Produces: `run_v81(opened_laws: Path, out_dir: Path) -> dict` and emitted JSON/JSONL artifacts.

- [ ] **Step 1: Write failing protocol-freeze and freshness tests**

Test constants: `FRESH_OPERATION_COUNT == 10`, `START_HORIZON == 2`, `MAX_HORIZON == 7`, `RETAINED_BUDGET == 5`, one-swap action grammar, deterministic new seed distinct from V73/V77/V78/V80. Test `build_protocol()` stable hash and that `generate_fresh_bases()` is called only after the freeze record is created.

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/test_verified_compounding_breakthrough_demo.py -q`

Expected: missing V81 module.

- [ ] **Step 3: Implement fresh ten-operation generator and layered controller**

Reuse V80 graph generation, replay verification, exact global enumeration, and one-swap gated repair semantics. Extend deterministic layer caps through horizon 7 without changing state budget or action grammar. Emit explicit `REUSE_STATE_UNDER_EXTENDED_VERIFIER`, `EXPAND_VERIFIER_ONLY`, or `ACTION_LANGUAGE_EXPANSION_REQUIRED` decisions.

- [ ] **Step 4: Implement capability/obstruction/transition materialization**

For each admitted endpoint, emit capability blocks for retained state members; for each positive exact residual, emit a `VerifiedObstruction`; for every admitted swap, emit a `VerifiedDevelopmentTransition` with strict positive delta and causal witness references.

- [ ] **Step 5: Implement persistence restart check**

Serialize each source endpoint to stable JSON, hash it, reload it, and assert exact state/hash equality before revealing the next horizon.

- [ ] **Step 6: Implement exact global endpoint gates**

At every horizon enumerate every fixed-budget retained state and require the selected endpoint to equal the exact global optimum. On failure, stop that source and set the fresh developmental verdict to FAIL.

- [ ] **Step 7: Run focused tests**

Run: `pytest tests/test_verified_compounding_breakthrough_demo.py -q`

Expected: protocol/freshness/schema integration tests PASS.

- [ ] **Step 8: Commit**

```bash
git add experiments/verified_compounding_breakthrough_v81/run.py tests/test_verified_compounding_breakthrough_demo.py
git commit -m "Add V81 fresh prospective developmental chain"
```

### Task 4: Frozen warm-vs-cold compounding economics and causal ablation

**Files:**
- Modify: `experiments/verified_compounding_breakthrough_v81/run.py`
- Modify: `tests/test_verified_compounding_breakthrough_demo.py`

**Interfaces:**
- Produces: `compare_compounding_economics(...) -> dict` with exact endpoint equality, cold/warm checks, savings, aggregate classification, and causal ablation evidence.

- [ ] **Step 1: Add failing equal-endpoint economics tests**

Construct a small deterministic graph fixture where warm starts from a previously persisted globally certified state and cold starts from the declared baseline. Assert comparisons are invalid unless both end at the same exact global value/state-equivalence class.

- [ ] **Step 2: Add failing causal-ablation test**

Require at least one predeclared comparison where removing the retained warm state or reverting to the generic proposal order restores additional verifier checks while endpoint quality stays equal.

- [ ] **Step 3: Implement the economics function**

Return `cold_checks_to_certified_endpoint`, `warm_checks_to_same_certified_endpoint`, `check_savings`, `endpoint_equal`, `ablation_restores_cost`, and aggregate classification `VERIFIED_COMPOUNDING_SIGNAL`, `ACCUMULATION_ONLY`, or `FAIL`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_verified_compounding_breakthrough_demo.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/verified_compounding_breakthrough_v81/run.py tests/test_verified_compounding_breakthrough_demo.py
git commit -m "Add causal warm-cold compounding economics"
```

### Task 5: Canonical breakthrough runner and evidence manifest

**Files:**
- Create: `scripts/run_verified_compounding_breakthrough_demo.py`
- Modify: `tests/test_verified_compounding_breakthrough_demo.py`

**Interfaces:**
- Consumes: `validate_historical_lineage`, `run_v81`.
- Produces: final files required by the spec and terminal verdict.

- [ ] **Step 1: Write failing CLI/output contract test**

Test that `build_parser()` supports `--opened-laws`, `--out-dir`, and `--quick`; that the runner emits all ten required artifacts; and that `artifact_hashes.json` hashes every emitted artifact except itself before writing its own final stable digest.

- [ ] **Step 2: Verify test failure**

Run: `pytest tests/test_verified_compounding_breakthrough_demo.py -q`

Expected: missing script/module.

- [ ] **Step 3: Implement orchestration**

Run trust-boundary/release checks that are dependency-safe in CI, historical lineage validation, then fresh V81. Compose separate verdicts: `TRUST_BOUNDARY_PASS`, `HISTORICAL_LINEAGE_VALIDATED`, `FRESH_DEVELOPMENTAL_CYCLE_PASS`, `AUTONOMOUS_REUSE_EXPAND_PASS`, `GLOBAL_OPTIMALITY_GATES_PASS`, and compounding classification.

- [ ] **Step 4: Implement bounded top-level verdict selection**

Emit `PASS_VERIFIED_COMPOUNDING_INTELLIGENCE_BREAKTHROUGH_DEMO_V81` only when all mandatory gates pass and compounding is `VERIFIED_COMPOUNDING_SIGNAL`; otherwise use the bounded accumulation-only or fail verdict from the spec.

- [ ] **Step 5: Implement report rendering**

Generate concise `breakthrough_report.md` explaining demonstrated facts, historical-vs-fresh distinction, negative V79 evidence, V80 endpoint, V81 results, and explicit non-goals.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_developmental_artifacts.py tests/test_breakthrough_lineage.py tests/test_verified_compounding_breakthrough_demo.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/run_verified_compounding_breakthrough_demo.py tests/test_verified_compounding_breakthrough_demo.py
git commit -m "Add canonical verified compounding breakthrough runner"
```

### Task 6: GitHub Actions end-to-end demonstration

**Files:**
- Create: `.github/workflows/verified-compounding-breakthrough-demo-v81.yml`
- Create: `docs/evidence/verified_compounding_breakthrough_demo_v81.md`

**Interfaces:**
- Produces: one manually/push-triggerable workflow and uploaded evidence artifact `v81-verified-compounding-breakthrough-demo`.

- [ ] **Step 1: Add workflow with pinned setup**

Workflow must checkout the V81 branch, compile new Python, install `cvc5==1.3.1`, fetch the same pinned opened training universe and verify its git blob hash, run the three focused test files, run the V81 breakthrough script, and upload the entire output directory with `if: always()`.

- [ ] **Step 2: Add evidence documentation**

Document the exact command, claim boundary, expected artifact names, and how to interpret compounding vs accumulation-only outcomes.

- [ ] **Step 3: Trigger by committing the workflow**

Commit:

```bash
git add .github/workflows/verified-compounding-breakthrough-demo-v81.yml docs/evidence/verified_compounding_breakthrough_demo_v81.md
git commit -m "Run V81 verified compounding breakthrough demo"
```

- [ ] **Step 4: Inspect workflow result**

Require workflow conclusion `success`, all focused tests green, and the scientific step complete. Download/read logs and artifact metadata before reporting results.

- [ ] **Step 5: If CI fails, use systematic debugging**

Do not weaken scientific gates. Diagnose implementation/infrastructure issues, patch only the defect, rerun the same frozen V81 protocol when freshness has not been scientifically spent by a completed fresh run. If a completed fresh run reaches scientific FAIL, do not rewrite that stream to force a pass; preserve it as evidence and create a separately frozen successor only when justified.

### Task 7: Verification before completion

**Files:**
- No new files unless a defect is found.

**Interfaces:**
- Consumes: final workflow run, logs, artifacts.
- Produces: completion report with exact run/job/artifact links and bounded scientific verdict.

- [ ] **Step 1: Run/inspect full test gate**

Confirm all V81 focused tests pass in GitHub Actions.

- [ ] **Step 2: Inspect all scientific summary fields**

Verify exact values for fresh source count, horizons reached, states enumerated, obstruction/recovery totals, reuse/expand/action-expansion counts, learned/generic/warm/cold checks, causal witnesses, endpoint gaps, protocol SHA, developer SHA, and final classification.

- [ ] **Step 3: Verify artifact integrity**

Confirm uploaded artifact exists and reported digest matches GitHub metadata. Confirm `artifact_hashes.json` self-consistency according to its documented convention.

- [ ] **Step 4: Report without overclaiming**

State exactly which historical stages were validated, which V81 evidence is fresh/prospective, whether compounding was actually demonstrated or only accumulation/development, and the explicit claim boundary.
