# Ethereum Crystal V16 — geth snap apply end-to-end benchmark

V16 moves the performance claim beyond decoder-only timing. On the frozen 1,112 held-out BAL corpus it runs the real geth `snap.applyAccessList` state-mutation path and commits its batches to an in-memory database.

The control decodes each canonical BAL with geth's full production decoder. The Crystal arm uses the frozen V13 final-state decoder. Both then execute the identical `applyAccessList` and batch-write code.

Qualification first applies the entire corpus with each path and requires the final database key/value digest to match exactly. Only then are full versus compact corpus passes benchmarked.

This is an end-to-end **BAL decode + snap state application + DB batch write** benchmark inside geth. It is still not a live p2p/mainnet sync benchmark; peer/network and disk-I/O latency are deliberately excluded.
