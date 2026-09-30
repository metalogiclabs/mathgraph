# Ethereum Crystal V21 — complete-trie authenticated catch-up

V21 crosses the last geth-internal semantic boundary left after V20: `phaseComplete` catch-up, where geth must maintain the account/storage tries and reproduce the post-state root committed by every header.

## Chain construction

The 1,112 frozen held-out EELS BAL records are independent fixtures, not an existing sequential blockchain. V21 therefore constructs a separate deterministic sequential test chain **before timing**:

1. start from Ethereum's empty state root;
2. decode each BAL with geth's full production decoder;
3. apply it with the real trie-maintaining `applyAccessList`;
4. commit the generated trie nodes;
5. record the exact resulting post-state root in that block's header;
6. commit the canonical BAL hash in the same header;
7. link the next header to it.

This root-generation oracle is identical for stock and Crystal and is outside the measured region.

## Measured A/B

Stock and frozen-Crystal geth then independently start from the empty completed state on Pebble and traverse the same chain through real `syncerV2.catchUp`.

Every block must pass:

- real peer request scheduling;
- full BAL response decode/hash authentication;
- the application decode;
- flat-state updates;
- storage/account trie maintenance;
- exact post-state-root equality with the pre-generated header;
- Pebble batch commit;
- persisted pivot advancement.

Three alternating fresh-process pairs are used as a qualification/feasibility gate. Performance is observational only in V21; no performance promotion threshold is attached to this run.

## Claim boundary

A green V21 warrants the frozen consequence through geth's completed-state catch-up semantics on a deterministic sequential chain derived from the official held-out BAL corpus. It does not claim that this synthetic chain is canonical Ethereum history, and it does not include socket transport or live-mainnet conditions.
