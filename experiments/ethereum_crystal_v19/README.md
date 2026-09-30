# Ethereum Crystal V19 — authenticated catch-up + Pebble A/B

V19 closes the conjunction left separate by V14 and V18.

V14 proved the frozen Crystal decoder is integrated into the real geth snap/2 catch-up path after BAL authenticity verification. V18 proved the performance advantage survives Pebble-backed batch writes and an explicit durability boundary. V19 measures stock versus Crystal **inside the real `syncerV2.catchUp` control flow** while retaining the storage engine.

## Frozen authority

- geth: `920c07774c65ebb3023536f85df642c44478b540`
- EELS: `84e7d2c266e3319fc3882e72f379282bb1c40f2d`
- corpus: the same 1,112 held-out canonical EIP-7928 BAL records used by V9–V18
- Crystal decoder: unchanged V13/V16 final-state apply consequence

## A/B boundary

Two test binaries are compiled from the same pinned geth source:

- **stock**: unmodified geth catch-up decoder;
- **Crystal**: only the already-qualified V13 decoder and catch-up patch.

The identical V19 harness builds a synthetic linked header chain over the frozen independent BAL records. Every header commits to the canonical BAL hash computed by geth. A real geth test peer serves the raw BALs through `RequestAccessLists`.

The measured path is then the production `syncerV2.catchUp` machinery:

1. resolve the linked gap;
2. schedule bounded BAL requests to the peer;
3. process the peer response;
4. fully decode/hash-check each returned BAL at the authenticity boundary;
5. perform the application decode;
6. execute `applyAccessList`;
7. write the Pebble batch;
8. atomically persist the advanced pivot;
9. continue across real 512-block catch-up windows.

The sync is deliberately in `phaseDownload`, so the benchmark covers flat-state catch-up but does not maintain/check the completed state trie after each synthetic record. The 1,112 held-out BALs are independent official fixtures, not a canonical sequential blockchain.

Seven fresh-process paired trials are run with alternating stock/Crystal order. Performance direction is not precommitted. Promotion requires exact equality of final database digest and final pivot across every arm, plus actual authenticated BAL requests.

## What V19 can warrant

A green result can show whether removing the redundant post-authentication full decode remains useful once real catch-up scheduling/authentication/windowing/pivot persistence and Pebble writes are included.

It cannot establish socket/network transport benefit, completed-trie root parity on a canonical chain, or live-mainnet whole-node speedup.
