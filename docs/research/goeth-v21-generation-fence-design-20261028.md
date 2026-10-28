# GOETH V21: late FCU generation-fence falsifier (research only)

Pre-registered on 2026-10-28 against the separately observed source-native V20
negative [Actions run 40659468285](https://github.com/metalogiclabs/mathgraph/actions/runs/40659468285),
the unmodified Geth experimental fork adapter at
`metalogiclabs/go-ethereum@be33043dc27407a62471bfde1d50b6f99bfc9e6b`,
and the exact official upstream merge input
`3a6c2e3b35ef8caa3d39dcbea3fe9f09099cca8c`.

## Existing negative and new counterfactual

V20 independently showed an older authenticated FCU, paused at the native
ancestry-qualified *beforeAdmit* hook, restore a pending finalized witness
after a newer authenticated invalid zero-head FCU cleared it. Its serial
positive control passed and its concurrent safety test failed. The source is
fork-only test code, not production Geth and not two valid competing FCUs.

V21 changes exactly the pending-witness **admission generation**. A request
captures a monotonically advancing service-local FCU generation at entry. A
brief mutex makes generation advancement plus pending clear atomic relative
to the later checked pending admission. Header fetching stays outside the
mutex; the existing independent JWT Engine V4 test clients remain unchanged.
No canonical finalized pointer or production code will be changed.

## RED: new test before any guard

`TestBALV21ConcurrentStaleFCUDoesNotReinstatePending` fails if an older
authenticated request reaches ancestry-qualified preadmission, pauses, a
newer invalidating request completes and leaves empty pending state, and
the older request resumes to restore a stale pending witness. A genuine
valid same-fork serial positive is independently retained by
`TestBALV20SerialInvalidFCUClearsPending`. The RED workflow MUST inspect
actual `go test` nonzero exit and an exact stale-restoration marker, together
with ordered interleaving markers; a compile error, timeout, missing control
or arbitrary failure is UNKNOWN, not an expected red result.

**Observed RED on the untouched adapter (after preregistration):**
[Actions #40660706170](https://github.com/metalogiclabs/mathgraph/actions/runs/40660706170),
job `122722737262`, exact MathGraph commit
`f600f5dc0ca633518f40642b2d8172b764789866` / tree
`793da7b5f338497ab1cc3f3988671a3579e6a0e0`, Geth original merged
tree `a61594923136563d50964d7aa96a44c778bf9441` and Go 1.27.3.
The native test logged `MG_BAL_V21_RED_STALE_REINSTALL` with exact stale
finalized hash `0x5a8c82459a56bd92a4f5621981651586ef30bd3af84711bd17c899563136dcb2`
and 1 stale admission, then failed. Serial/V17/V18/V19 controls all passed.
The workflow classified the expected failing Go test as `EXPECTED_RED` only
after checking both ordering markers and positive controls. [Artifact
12803831097](https://github.com/metalogiclabs/mathgraph/actions/runs/40660706170),
GitHub-reported ZIP SHA-256
`26ed68251db4814d59f4afc44b6e674713a298487656fd78b04c57f918b2bf9a`
(not independently rehashed). That RED commit and artifact remain immutable.

## GREEN: minimum repair and decisive controls

Only after observed RED, apply a byte-pinned, test-only patch to
`eth/catalyst/bal_pending_engine_witness_v13_test.go` adding a
service-local `sync.Mutex` and generation to serialize (1) entry clear and
generation advance with (2) late admission conditioned on its captured
generation. Run the exact same V21 concurrent test plus:

- authenticated serial valid-then-invalid positive control;
- `TestBALInvalidFCUV17MalformedAttributesCannotAdmitPendingAuthority`;
- `TestBALV18CompetingForkFinalityFailsClosed`;
- `TestBALV19CrossForkAdmissionPredicate`.

The green test must record zero pending witness and zero stale admission
callbacks after the older FCU finishes. The pre-existing V20 failed test
does not run on the repaired overlay because its last assertion demands the
*pre-repair* stale admission callback. Its exact failing source and native
artifact remain independently preserved. No comparison may infer broad
concurrent FCU safety from this single invalidating interleaving.

## Boundary

At most `WARRANTED_BOUNDED_TEST_ADAPTER_SUPERSESSION_REPAIR` for this precise
service-local two-client schedule. Remote two-fork pending-gate V20 is a
separate bounded positive; full import/restart parity, two valid conflicting
FCUs, CL consensus, actual production source, owner grant and release
authority remain UNKNOWN. Publish only to a draft research branch and
retain source identity, formatted overlay blob, native log and classifier.
