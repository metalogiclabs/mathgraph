# V7 executable CI qualification

Run: https://github.com/metalogiclabs/mathgraph/actions/runs/39778060221
Commit: d1832a10318a923192b7fcde6bf95f62b72dc633
Status: GitHub Actions SUCCESS.

- 80 training cases; parser incorrectly treated 40 of them as acceptable relative to PNG CRC contract.
- 400 held-out cases; repair using zlib CRC32 matches separately implemented bitwise CRC32 on all cases.
- Source rule: hand-selected PNG standards excerpt hashed SHA256 9635afa0c0eb6f8afc8e2c023474e06c1b0fa2486ff6c181804369149a1fbd3e.
- Mutating/removing phrases about CRC coverage and always-present CRC makes the hard-coded rule extractor return false.

**Limitations**
- This is NOT a hash of the complete authenticated W3C document.
- Checker/contract extraction grammar are manually constructed; no independent automatic extraction from a new standards document.
- Independent CRC algorithm is implemented differently but tests, target choice and specification excerpt are co-authored.
- Withdrawal experiment only asserts absence of required phrases; it does not propagate a source-revocation event through persisted warrant lineage.
- No advantage over fully informed direct CRC verifier; baseline ties.
- Does not demonstrate a novel physical observation primitive, general PNG validator, or an untouched scientific-source transfer.

Epistemic status: WARRANTED within synthetic PNG holdout and local source-phrase predicate. General autonomous source-authority discovery UNKNOWN.

Next cheapest decisive experiment: freeze generic extraction grammar, select a new independent standard only afterward; generate obligation from source with no designer-specified repair, certify it with a separately authored verifier and exercise actual warrant withdrawal. Preserve an obstruction when the grammar cannot infer the source obligation.
