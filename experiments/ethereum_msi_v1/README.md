# Ethereum MSI consequential-interface experiment v1

A bounded, exact experiment inspired by the “cryptographic world computer” decomposition.

**Question.** Given an Ethereum-style transition system and a declared protected continuation language, can the MSI quotient remove state that cannot affect any protected future while retaining every distinction that can—and can the same model expose operations that need ordering versus operations that commute?

The experiment exhaustively enumerates a finite state space. It synthesizes equivalence by complete depth-2 continuation signatures, checks that the quotient exactly removes an unrelated storage coordinate `z`, performs deletion ablations showing every retained coordinate is consequential, proves by exhaustive enumeration that disjoint storage updates commute, and requires a concrete witness that opposite transfers do not.

This is deliberately a **bounded model theorem**, not a claim about the EVM or Ethereum as a whole. Its purpose is to test the adapter shape before attaching MSI to executable EVM semantics.

Run: `python experiments/ethereum_msi_v1/run.py`.

Promotion rule: only promote beyond CANDIDATE if CI is green and the reported quotient, ablations, commutativity result, and noncommutativity witness all survive.
