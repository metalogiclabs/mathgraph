# Ethereum Crystal v5 — held-out EELS family transfer

V5 moves from a synthetic event world to **protocol families named in the pinned EIP-7928 executable-spec test plan**.

The source families include no-op storage writes, delegated reads/writes, cross-index withdrawal/consolidation system calls, zero-value transfers, contract creation, call-target access, and net-zero balance transfers.

Crystal starts only with the structural capabilities warranted in v4. Held-out families are converted to consequence-requirement vectors from their published EELS expectations. The gate asks whether previously learned structural capabilities are reused without reacquisition and whether only genuinely new consequence types become residuals.

This is still not direct EVM execution. It is a source-derived held-out family-transfer test. The next boundary is executable fixture generation/replay.
