# QCKN Consequential Representation Equilibration V2

## Purpose

V1 attempted to use Lean LocalDef semantic-context caching as the coarsening half of a bidirectional representation experiment. That replay was not accepted as authority: the historical Arena corpus hash had changed, and the semantic-context cache remained experimental rather than part of the promoted production checker path.

V2 preserves that negative and replaces it with a stronger verified coarsening source already present in MSI: positional addition histories compress to the exact minimum two-state future-behaviour quotient.

## Candidate operator

For a finite carrier X and a complete frozen protected consequence map c : X -> Y, define the consequential representation

E_c(x,y) iff c(x) = c(y).

The QCKN-level equilibration candidate replaces the current representation with exactly E_c.

Relative to the current representation this can be:

- REFINE — remove unjustified identifications;
- COARSEN — erase unjustified distinctions;
- EQUAL — already minimal sufficient;
- REPARTITION — neither nested direction.

V2 qualifies one REFINE and one COARSEN case. It does not modify the frozen conservative QCK/MSI core.

## Refinement world — finite NAND circuit complexity

Pinned source:
- heathsanchez/test @ 4df88a272926126b895c2fb6220c56012949df05
- exact finite P-vs-NP spike evidence

The old representation is the existing 12-scalar structural signature.

It merges 0x8f and 0xea although their exact NAND sizes are 2 and 3. The exact protected consequence map is NAND size on the four retained functions.

Therefore the exact consequence kernel strictly refines the old representation.

Flash arrives after six failed scalar checks. Cold and raw-history arms exhaust twelve. A discrete over-fine sham must be rejected because two projection functions have the same protected consequence and should remain merged.

## Coarsening world — positional addition history

Pinned source:
- heathsanchez/Minimal-Sufficient-Interface @ 5d448c0ecc82ff3945d009963064ebbb67d2f308
- tests/test_arithmetic_base_invariance.py

For decimal two-addend local addition the declared carrier is:

- the empty history;
- every possible one-position digit-pair history.

There are exactly 101 raw histories.

The verified future behaviour of a history is its complete vector of next-digit consequences over all 100 possible next digit pairs.

MSI's adaptive discovery independently recovers exactly two future-behaviour classes in every base 2..16. In base 10, the full 101-history identity representation is therefore over-fine:

101 raw identity classes -> 2 exact consequence classes.

V2 deliberately starts from the over-fine raw-history identity representation so the same operator must move in the opposite direction from the circuit world.

### Arithmetic arms

- COLD: retain all 101 raw history records.
- WARM: exact consequence kernel is available from the start; only 2 representation records are needed.
- FLASH: allocate 20 raw history records, then receive equilibration. The first 20 histories collapse to one already-seen consequence class; one further class appears later. Counting raw allocations plus recompiled/new consequence-class records gives 22 allocations total, final representation size 2.
- RAW_HISTORY: 101 allocations.
- SHAM_ALL_MERGED: propose one class for all 101 histories; exact authority rejects it because the protected future consequence map has two classes.
- ABLATION: valid coarsening is removed before use; final representation returns to 101 raw identity classes.

## V1 Lean negative retained

Run 35409594145 failed during historical Lean replay because the external Arena corpus hash had changed. The P-vs-NP source and pinned Lean source blob both verified before that failure. V2 does not treat the Lean experiment as coarsening authority.

## Pass criteria

V2 passes only if:

1. the same exact consequence-kernel operator selects REFINE for the circuit world and COARSEN for arithmetic;
2. the P-vs-NP metric collision reproduces;
3. circuit Flash resolves after six checks while cold remains unresolved after twelve;
4. the circuit over-fine sham is rejected;
5. decimal arithmetic has 101 raw histories and exactly 2 protected future-behaviour classes;
6. arithmetic WARM uses 2 representation allocations;
7. arithmetic FLASH uses 22 allocations and ends with 2 classes;
8. arithmetic COLD/RAW_HISTORY use 101 allocations;
9. the one-class arithmetic sham is rejected;
10. arithmetic ablation restores the 101-class raw representation.

## Boundary

A pass is evidence for bounded bidirectional consequential representation equilibration under complete frozen consequence maps.

It does not establish safe coarsening when future protected obligations are unknown, universal representation optimality, open-ended self-representation change, or P != NP.
