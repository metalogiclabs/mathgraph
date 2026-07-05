# SorryDB v4.4.32 — Active Target Recon

v4.4.32 clones the selected active-sorry target into a bounded temporary directory for reconnaissance.

## Bounded claim

- v4.4.32 clones the selected active-sorry target into a bounded temporary directory for reconnaissance.
- it records manifest files, Lean toolchain, target exactness, imports, and active-sorry count.
- it does not build, replay Lean, patch the target, modify upstream, or contact maintainers.

## Does not claim

- new proof discovery
- new Lean replay
- candidate repairability
- that the repo builds locally
- that a patch exists
- upstream acceptance
- automated external contact

## Next frontier

v4.4.33 run a bounded source-only patch experiment on the exact target file, then replay only if the patch is syntactically plausible.
