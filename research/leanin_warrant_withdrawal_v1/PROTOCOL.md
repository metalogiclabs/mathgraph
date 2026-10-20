# LeanIn native contract withdrawal — frozen protocol v1

## Objective

Test whether MathGraph's **unchanged** bounded resolver retracts precisely the
source-documented consequences of withdrawing an explicitly named native
assumption, without incorrectly withdrawing valid *conditional* Lean theorems.
Exercise real pinned Lean proof output and a native compile-negative
perturbation; do not represent any of this as verification of Lean's C++/libuv
runtime or a source-authorized operational guarantee.

## Pins and sources

* Exact upstream source: scidonia/leanin@a7e8e9ca4fef75b6eff665925ff17aaf9ff35029.
* Source toolchain: leanprover/lean4:v4.35.0.
* Upstream CI reference: [run 39486730021](https://github.com/scidonia/leanin/actions/runs/39486730021):
  gate succeeded; scenarios failed at SC18, blocking later benchmarks
  and bridge trace scenarios. This run is NOT a successful full CI receipt.
* Same-repo pinned MathGraph implementation:
  mathgraph_check/warrant_resolution.py; no changes to its algorithm.
* LeanIn/Theory/Bridge.lean names the assumed operation contracts.
  LeanIn/Model/Service.lean and LeanIn/Theory/World.lean contain independent
  pure-model proofs. See upstream docs/proof-strategy.md §2 and §6.

## Preregistered proof selection and falsifiers

The exact #print axioms fingerprints must be replayed natively:

* LeanIn.lock_wait_unlock_postcondition: lock_spec, unlock_spec, wait_spec.
* LeanIn.readings_monotone_across_a_call: clock_spec, lock_spec.
* LeanIn.wait_cycle_reachable: propext, Quot.sound.
* LeanIn.notifyOne_no_additions: propext, notifyOne_spec.
* LeanIn.Model.reachable_noDrop: propext, Classical.choice, Quot.sound.

Failures are decisive: missing/extra fingerprint or source declaration,
mis-scoped relation admitted, an unrelated documentary claim withdrawn, a
conditional kernel proof retracted by documentary withdrawal, imperfect
restoration, or no native compile error following an exact axiom symbol
quarantine. Do not reinterpret source CI SC18 failure as a theorem failure.

The test separately performs a **symbol-removal experiment**: rename only
axiom wait_spec on a disposable pinned source checkout. The bridge module
must fail to compile due to the now-missing original name; the pure model and
service modules must still compile. Restore byte-for-byte, rebuild and compare.
This is a syntactic source perturbation and NOT evidence that withdrawing
operational authority physically changes the native runtime.

## Epistemic boundaries

The resolver's WARRANTED_BOUNDED state for a Lean theorem here means
*conditional Lean proof accepted under the declared axiom list*. It is not an
unconditional assertion that the corresponding native operation obeys that
axiom.

SOURCE_DOCUMENTED marks source-derived conditional descriptions and
publication/CI observations, not verified native correctness.

native.model_refines_runtime must remain UNKNOWN before and after
contract withdrawal. Neither proof presence, a symbol named wait_spec,
passing trace examples, nor a qualifying-looking bridge string can create
the absent independently verified model-to-native correspondence.

Receipt construction and source identity are external trusted inputs. Native
axiom transcripts and GitHub Actions metadata can be authenticated at pinned
revision/run. The explicit source/CI provenance and negative controls limit
—but do not eliminate—those assumptions. The model is an exposed public
case, NOT an untouched G2 observer-genesis experiment and not evidence
of advantage over an equally informed expert.

## Native reproduction

Run the workflow .github/workflows/leanin-warrant-withdrawal-v1.yml on this
research branch. The workflow checks out the exact upstream commit, builds
Lean in the official toolchain, obtains independent native #print axioms
output, checks frozen public CI metadata, executes
python -m research.leanin_warrant_withdrawal_v1.run,
performs the native mutation and restoration, and archives proof logs,
graph results, perturbation logs and source hashes. The workflow succeeds
only if every control passes.

The independent verifier still required for external operational warrant
would need to verify the semantic relation from native I/O executions to the
modeled transition system, with explicit admissible assumptions and
test/trace coverage. Merely passing this experiment must not promote that
bridge.
