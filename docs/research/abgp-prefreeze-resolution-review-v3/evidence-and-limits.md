# V3 publication revision 1: evidence and limits

Date: 18 September 2026. This is a source-based review, not a new experimental result.

Reviewed source snapshot: `0e37943e3364e8dda671b4fc47ded812c437a56d`.
The preceding implementation commit is `f9764a3696f880e2ec09e8eb7b60054f92b8ac53`.
Paths below identify the implementation reviewed; the excerpts and blob identities are provided here so this public review does not require a link to a personal repository.

## S1. Seed inventory is not independently traced complete ancestry

File: `realitygraph/abgp/freeze_review.py`.
Git blob: `c7c3e03b2f2992eb8cb8b187b9f1a2eb3aab4d6f`.

`audit_a_stochastic_ancestry()` constructs its groups from only:

```python
f"acquisition:{episode.acquisition_seed_digest}"
f"sealed_future:{episode.future_seed_digest}"
```

`audit_p_stochastic_ancestry()` similarly groups the acquisition seed and listed future seeds. `_shared_ancestor_count()` counts reuse of these strings. The saved small DEV matrix reports zero reuse of those listed fields for A/P. The descriptive lists of fixed and sampled objects are supplied by the audit, not independently discovered from a complete generation trace.

**Warranted:** the listed identifiers are unique in the examined DEV records. Fixed protocol definitions are distinguished in the report from episode-specific fields.

**Not established by this check alone:** every relevant stochastic ancestor was recorded, a sampled shared constructor/pool would necessarily be detected, or independence for the intended estimand. Record generation paths and the sampling model must justify those further claims. This does not assert that a hidden shared ancestor definitely exists.

## S2. Executable B demonstrator is not yet the agreed ordinary-explanation separator

File: `realitygraph/abgp/arm_b.py`.
Git blob: `f4e219286cf19caf5a81d7b665eb56a1078210b9`.

The replacement no longer directly assigns `recovered_order = target_order`. It does execute grammar-specific inference and retained predictions. However:

```python
def represent(self, world: DevWorld, intervention: str) -> Any:
    return self.encode_order(_protected_order_slots(world, intervention), intervention)
```

The common adapter also has supplied `slot_tokens`; `_slot_from_surface()` returns `self.slot_tokens.index(token)`. The finite grammar encoders encode an already computed protected order, and the retained `CapabilityOrder.predict()` calls the shared `_apply_intervention()`.

The control currently called bisimulation/Bayes begins:

```python
hidden = _hidden_slot(world)
coarse_signature = hidden % 2
candidate_hiddens = tuple(i for i in range(4) if i % 2 == coarse_signature)
candidate_orders = tuple(_base_order_from_hidden(i) for i in candidate_hiddens)
chosen = CapabilityOrder(candidate_orders[0])
```

It predicts and scores an actual candidate rather than drawing a success bit. But it does not construct a greatest-bisimulation relation from a specified transition/observation system or condition on the complete admissible acquisition history. A parity partition with a separating intervention is not, by that fact alone, the agreed acquisition-posterior/greatest-bisimulation baseline.

**Warranted:** actual finite encoding/decoding and comparison now execute.

**Pending:** independently generated candidate grammars, defensible separation from supplied canonical mappings, the full exact-information boundary of the ordinary control, and end-to-end acceptance. This is not confirmation that B is false; the apparatus is not yet sufficient for that interpretation.

## S3. A symmetric example does not prove the actual G experiment exchangeable

Files: `realitygraph/abgp/arm_g.py` and `realitygraph/abgp/freeze_review.py`.
Git blobs: `9005c98b9a95f7424e9fa1bc2a937ef0cf75ed18` and `c7c3e03b2f2992eb8cb8b187b9f1a2eb3aab4d6f`.

Pair ranks now use unordered member identities. This is genuine progress on selection symmetry.
The extra null check, however, builds each outcome pair from the same function twice:

```python
original = tuple((r.dose, _label_blind_null_flip(r), _label_blind_null_flip(r)) for r in nonzero)
swapped = tuple((dose, irrelevant, relevant) for dose, relevant, irrelevant in original)
null_swap_checks.append(original == swapped)
```

That constructed `(x, x)` pair is invariant by construction. The actual DEV outcome path still uses:

```python
relevant_flip = int(count >= 5)
irrelevant_flip = 0
```

These are explicitly planted outputs, not measured consequences of the real learner and corrupted representation. The complete-schedule/contiguous-index check also does not, by itself, establish the absence of upstream outcome-dependent selection or stopping.

**Warranted:** matched selection bookkeeping and arithmetic checks for chosen examples.

**Pending:** a justified null and exchangeability argument for the complete actual process, including generation, selection and stopping. Do not label the new sharp-null wording as jointly frozen; it is a proposal. A fixed symmetric test example cannot establish the general null required for all admissible data-generating processes.

## S4. P execution boundary still needs acceptance evidence

File: `realitygraph/abgp/arm_p.py`.
Git blob: `35f3c1c8f25226d73e713fa887a897d7872b56c9`.

In `_independent_episode()`, the inspected restart is:

```python
retained_text = acquired.to_text()
retained = RetainedStructure.from_text(retained_text)
restart_byte_exact = retained.to_text() == retained_text and retained.digest == acquired.digest
```

The acquired object, seed and policy remain in the same process. The record then assigns:

```python
cross_restart_state_keys=("retained_object_bytes",)
post_deletion_episode_success=cold_success
future_verifier_calls=0
future_reconstruction_search_count=0
source_distinct=True
```

A canonical round trip can be tested this way, but a declared state-key tuple does not enforce an isolated restart. Assigning the cold score is not execution of causal lineage deletion. Some counters/flags are record values rather than observed access telemetry. These gaps must not be described as already closed.

## S5. Candidate analysis and criteria reconciliation

File: `preregistration/abgp-analysis-plan-v1.json`.
Git blob: `a6c659c63f78d8e236d1d6c69f87c3df65b35214`.

The candidate plan defines B's maximum of 36 component p-values, the four-arm Holm procedure, observed effect floors, B's pooled 0.90 agreement gate, and seven P primary comparisons. Its P ablation wording uses an ordinary/no-retention control envelope. The supplied LinkedIn thread instead specifies performance within two percentage points of cold. That difference needs explicit reconciliation; this release does not change either scientific criterion silently.

The stated q values are finite grids. No result here establishes that a minimum over those grids is also the minimum over an entire continuous feasible range.

## S6. Verified historical evidence, not a new qualification

Historical run: `35251639106` at implementation commit `f9764a3696f880e2ec09e8eb7b60054f92b8ac53`.
Artifact: `10509835364`, named `abgp-dev-qual-v1-evidence`.
Downloaded archive SHA-256, verified against the connector's reported digest:

`df64e32e17acb26760e457bb0015ae1db34b5636a45075814b32a61ebedace10`

Its qualification log reports 21 fixtures, statistical-reference PASS and legacy `QUALIFIED`; the code/records above bound the meaning of that output. This release does not rerun the whole source regression or certify the scientific mechanisms. No confirmation is executed by this review or by its independent power script.

## D1. Independently reproduced component-floor probability

`power_floor_diagnostic.py` computes a finite paired-binomial probability using SciPy, separately from the source implementation. It checks 24 small parameter cases against exhaustive sequence enumeration with rational probabilities. Maximum discrepancy was `1.1102230246251565e-16` in the recorded environment. Full grids, versions, scope and results are in `power-floor-diagnostic.json`.

This is exact-distribution modelling evaluated numerically, not arbitrary-precision evaluation of every large-n probability. It estimates neither the full multi-control joint event nor the actual experiment's power. A zero union-bound lower bound does not mean zero actual joint success probability.

## Publication change log

V1: superseded qualification sheet; V2: provisional design summary.
V3 draft: progress and power-floor analysis, but some implementation acceptance labels remained too strong.
V3 publication revision 1: PDF, Markdown, source excerpts, diagnostic and machine-readable readiness now agree that implementation acceptance and complete-PASS power remain pending. This corrects reporting; it does not revise the scientific study or authorize freezing.
