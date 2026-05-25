# Module Map

This map is a practical orientation aid. It does not delete or demote legacy
modules.

## Integrity Spine

- `certificates.py`: terminal forms and certificate records
- `invariants.py`: trust-boundary invariant reports
- `evidence_manifest.py`: replayable evidence manifest records
- `evidence_replay.py`: replay and artifact hash checks
- `lawbook.py`: Lawbook entries, review, and audit helpers
- `lawbook_acceptance.py`: acceptance contract around manifests and invariants
- `lawbook_store.py`: SQLite-backed stores and benchmark persistence surfaces
- `lawbook_schema.py`: canonical Lawbook façade dataclasses and enums
- `lawbook_boundary.py`: terminal admission boundary façade
- `lawbook_ingest.py`: boundary-gated ingest helpers
- `lawbook_query.py`: small query façade
- `lawbook_export.py`: manifest, JSONL, and summary exports
- `lawbook_reuse.py`: reuse and action-change metrics

## Verification Boundaries

- `verifier_execution.py`: local verifier execution contract
- `verification_loop.py`: stable façade over closed, finite, and compounding loops
- `proof_system_integration.py`: proof-system artifacts and boundary contracts
- `proof_verification.py`: proof verification records and traces
- `finite_magma_world.py`: deterministic finite magma checker
- `finite_magma.py`: repo-native finite magma representation and checked FALSE certificates
- `external_certificates.py`: external verifier certificate envelope
- `promotion_gate.py`: boundary gate for terminal candidates

## Claim And Semantic Boundaries

- `kernel.py`: compact claim acceptance kernel
- `verification.py`: certificate verification helpers
- `domain_claims.py`: domain claim IR and adapters
- `semantic_validation.py`: informal/formal validation boundary
- `semantic_intake.py`: advisory natural-language intake

## Routing And Memory

- `reason_atlas.py`: routing memory and verifier-backed outcome metrics
- `reason_atlas_store.py`: persistent advisory Reason Atlas entries
- `reason_atlas_feedback_loop.py`: advisory feedback orchestration
- `reason_atlas_htilt.py`: H-Tilt scoring over Reason Atlas entries
- `route_learner.py`: route learning
- `route_priors.py`: smoothed route priors
- `route_telemetry.py`: route telemetry
- `spectral_htilt.py`: spectral H-Tilt estimates
- `viability_operators.py`: candidate V operators

## SAIR And Finite Countermodel Workflows

- `sair_task_loader.py`: SAIR equation/matrix loading
- `sair_constructor_bank.py`: finite magma constructor bank
- `magma_constructors.py`: deterministic finite magma constructor families
- `sat_cache.py`: constructor/equation satisfaction cache and route evaluation
- `policy_engine.py`: advisory constructor-route policies
- `proof_congruence.py`: bounded proof-producing congruence traces for TRUE candidates
- `true_proof_templates.py`: TRUE proof-template family inventory
- `lean_artifacts.py`: Lean skeleton artifacts and verification status records
- `etp_terms.py`: ETP/SAIR binary magma term parsing and equation features
- `quotient_state.py`: bounded symbolic quotient/congruence state
- `polarized_quotient_ir.py`: quotient-continuation pair features
- `constructor_families.py`: advisory constructor family metadata
- `obstruction_atlas.py`: advisory obstruction and residual queue records
- `sair_breakthrough_runner.py`: SAIR breakthrough loop runner
- `sair_motif_hygiene.py`: clean motif hygiene
- `sair_clean_motif_mining.py`: clean motif mining
- `sair_scheduler_evaluation.py`: held-out scheduler evaluation
- `sair_real_compounding_benchmark.py`: real/fallback compounding benchmark

## Compounding And Artifact Packs

- `compounding_lawbook_engine.py`: fallback compounding engine
- `compounding_engine.py`: canonical baseline versus memory compounding loop
- `autonomous_compounding_engine.py`: autonomous finite-core façade plus native v2 finite recovery/residual repair loop
- `autonomous_finite_recovery.py`: constructor bank, SAT-cache recovery, greedy route, and residual repair adapter
- `scripts/run_mathgraph_compounding_engine.py`: multi-episode ETP constructor/residual/Lawbook runner
- `scripts/run_autonomous_compounding_engine.py`: autonomous façade/native v2 CLI
- `scripts/run_true_side_inventory.py`: bounded TRUE-side proof-template inventory runner
- `recursive_residual_compounding.py`: residual-mined constructor memory and compact atlas benchmark
- `scripts/run_polarized_quotient_ir_demo.py`: lightweight PQ-IR feature demo
- `multi_episode_compounding.py`: multi-episode compounding evaluation
- `real_sair_artifact_pack.py`: real/fallback artifact pack runner
- `lawbook_admission.py`: production admission levels
- `lawbook_promotion.py`: run artifact promotion reports

## Canonical Examples And Checks

- `scripts/run_canonical_finite_countermodel_demo.py`
- `scripts/replay_evidence_manifest.py`
- `scripts/run_reason_atlas_demo.py`
- `scripts/run_trust_boundary_check.py`
- `scripts/run_release_check.py`
- `scripts/run_repo_architecture_audit.py`
- `scripts/run_recursive_residual_compounding.py`
- `scripts/run_mathgraph_compounding_engine.py`
- `scripts/run_autonomous_compounding_engine.py`

## Legacy Surface

The repository includes many experiment and smoke-run modules. Keep them unless
a focused cleanup PR proves they are obsolete and preserves tests. The canonical
spine above is the preferred path for new integrations.
