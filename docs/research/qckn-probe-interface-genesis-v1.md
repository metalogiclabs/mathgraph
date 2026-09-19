# QCKN Probe / Interface Genesis V1

## Question

Can the bridge learner decide **what to observe next** when its current observation language is insufficient, synthesize a new probe from a bounded grammar, and only then earn a cross-domain bridge?

This gate extends Verified Bridge Genesis V1. The source event and live opaque target already exist. No bridge is present.

## Frozen setting

Source roles:

`SCAN FILTER FIRST PAIR EXTEND TEMPORAL`

Opaque target tokens:

`zx9 qa2 mn7 rv4 kp1 ht8`

The target is already live and has exhausted cold search through depth 6:

**35,290 verifier calls**

before probe genesis begins.

The source event is already admitted to the GlobalFlashBus with:

**0 cross-domain edges**.

## Initial observation language

The learner initially has only two interface probes:

- `empty`
- `one`

Those observations leave:

**24 possible source-to-target bridge bijections**.

Therefore the observation language is explicitly insufficient.

## Probe grammar

The system is not handed the useful probes as a selected list. It is given a bounded probe-construction grammar:

- `count2(one) -> two`
- `advance(one) -> useful`
- `open(useful) -> opened`
- `temporalize(opened) -> temporal`

The grammar is supplied; the choice of which generated probe to execute is not.

## Active probe selection

Each surviving bridge hypothesis predicts what a proposed new probe would make the target operation vector look like.

Before spending a target probe, the runtime groups current bridge hypotheses by those predicted outcomes.

It scores a candidate probe by:

1. smallest worst-case surviving hypothesis class;
2. smallest collision mass among predicted classes;
3. smaller generated term;
4. deterministic name tie-break.

### First residual

With `empty, one`:

**24 hypotheses remain**.

Generated frontier:

- `two` -> worst-case 6 survivors;
- `useful` -> worst-case 2 survivors.

The runtime therefore synthesizes and executes:

**`useful`**

Hypotheses:

**24 -> 2**

### Second residual

The observation language is still insufficient.

The newly available grammar term:

**`open(useful) -> opened`**

is synthesized and executed.

Hypotheses:

**2 -> 1**

The low-information generated probe `two` is never selected.

Final developmental observation basis:

`empty, one, useful, opened`

## Independent authority

Identification is not certification.

The unique proposed bridge is passed to an independent verifier that evaluates **all six interface cases**, including probes not required for bridge identification.

Authority cost:

- developmental probe executions:
  - 4 selected probes × (6 source roles + 6 target operations)
  - **48 executable evaluations**
- independent full attack:
  - 6 cases × (6 source roles + 6 target operations)
  - **72 executable evaluations**
- attack comparison checks:
  - 6 cases × 36 source/target pairs
  - **216 comparisons**

Total executable bridge-authority evaluations:

**120**

Only after this attack passes is a BridgeCertificate admitted into the GlobalFlashBus.

## Live target effect

Bridge admission retroactively connects the already-present source event to the already-running opaque target.

The target has paid:

**35,290 verifier calls**

before probe genesis.

After bridge admission it needs:

**96 additional target verifier calls**.

Final target work:

**35,386**

Cold:

**222,808**

Avoided target work:

**187,422 verifier calls**

Bridge authority remains separately typed and is not added to target verifier work.

## Controls

### STATIC

No probe-language growth is allowed.

The initial 24 bridge hypotheses remain.

No bridge. Target completes cold.

### SHAM_GRAMMAR

The grammar can generate only `two`.

That reduces:

**24 -> 6**

but never identifies a unique bridge.

No bridge. Target completes cold.

### MISMATCH TARGET

The adaptive learner reaches a unique bridge hypothesis under its selected probes.

However the independent full six-case attack sees the held-out `temporal` mismatch and rejects the bridge.

This separates **identification** from **authority**.

### AMBIGUOUS TARGET

The generated `opened` probe eliminates all bridge hypotheses.

The runtime emits a bridge obstruction rather than forcing a mapping.

### WITHHOLD

Probe genesis and independent authority succeed, but the certificate is withheld from the bus.

No edge materializes and the target remains cold.

### RESTART

The runtime is canonically restarted during bridge development and reruns the deterministic probe-genesis process.

The same bridge certificate, bus edge, and target outcome must result.

## Pass conditions

The gate passes only if:

1. the target is already live at 35,290 calls before probe genesis;
2. the source event initially has zero edges;
3. the initial observation language leaves 24 bridge hypotheses;
4. active selection synthesizes `useful`, then `opened`;
5. the hypothesis curve is exactly 24 -> 2 -> 1;
6. generated low-information `two` is not selected;
7. the proposed six-role mapping is unique;
8. a separate full six-case attack passes;
9. developmental probe work is 48 executable evaluations;
10. full attack work is 72 executable evaluations / 216 comparison checks;
11. bridge admission resolves the target at 35,386 calls;
12. STATIC and SHAM_GRAMMAR remain cold;
13. the mismatch target is rejected only by independent authority;
14. the ambiguous target produces an obstruction;
15. withholding the certificate restores cold;
16. restart reproduces the same certificate and target outcome.

## Claim boundary

A pass establishes bounded **probe/interface genesis** over a supplied finite probe grammar and a supplied bridge-hypothesis family.

The runtime chooses and constructs its own useful probes in response to bridge ambiguity; it is not handed the final observation basis.

It does not establish open-ended invention of probe grammars, natural-language ontology discovery, unrestricted scientific experiment design, or arbitrary semantic transfer.
