# Verified Capability Calculus

Status: qualification pending on branch crystal-chess-capability-calculus-v8.

## 1. Purpose

The calculus is the minimal strategic thin waist extracted from the MathGraph
Research OS. It is intended for domains in which a system has:

- protected goal states;
- protected forbidden/failure states;
- certified capabilities with explicit applicability/support;
- adversarial or nondeterministic outcomes after a chosen capability; and
- an independent authority that qualifies capability consequences.

Discovery may use search, ML, LLMs, engines, tablebases, theorem provers, or
human proposals. None of those mechanisms becomes authority merely by
proposing a capability.

## 2. Semantic objects

A capability step is

c = (s, id, O, W, pi)

where:

- s is the source consequential state;
- id is the stable capability identity;
- O is the nonempty set of possible protected successor states after the
  chosen capability and represented environmental/adversarial response;
- W is the set of live supports required for execution;
- pi is an external evidence/provenance pointer.

A capability is live iff all supports in W are live.

The controllable predecessor of a state set K is:

Pre(K) = {s : exists live c at s, for every t in O(c), t is in K}.

This is the central exists-controller / forall-environment operator.

## 3. Forced-goal semantics

For protected goal set G and forbidden set B:

W0 = G

W(n+1) = Wn union (Pre(Wn) minus B).

The forced-goal region is the least fixed point:

W* = mu W. G union (Pre(W) minus B).

A newly admitted state receives rank

r(s) = 1 + min_c max_{t in O(c)} r(t).

Therefore every compiled goal-progress decision strictly decreases worst-case
rank under every represented adversarial outcome. This is a finite strategy
certificate, not an evaluation score.

## 4. Safety / draw semantics

For forbidden set B and explicitly safe terminal set D, the greatest protected
viability region is:

K* = nu K. (not B) intersect (D union Pre(K)).

Cycles are permitted in K*. This is intentional: drawing/safety behaviour is a
greatest-fixed-point property, whereas forced conversion is a least-fixed-point
property.

## 5. Arbitration

At state s:

1. if s is in G, stop;
2. else if s is in W*, execute a live capability whose every outcome has
   strictly lower goal rank;
3. else if s is in K*, execute a live capability whose every outcome remains
   in K*;
4. else emit a typed residual:
   no_live_capability_forced_to_goal_or_preserving_safety.

No guessed action is licensed at a residual.

## 6. Learning / refinement

Learning changes the certified transition system, not the epistemic rule:

- a new capability may add a guarded step;
- a counterexample may tighten a guard or reject a step;
- a future separator may split a consequential state;
- revocation may disable steps whose supports are no longer live;
- reclosure recomputes W*, K*, decisions and residuals.

The persistent knowledge object is the smallest live certified capability /
quotient refinement required to preserve protected continuation.

## 7. Chess instantiation

For chess, a capability can be a symbolic move constructor. Its outcomes are
the states after the chosen move and all represented opponent replies.

- Exact wins use the forced-goal attractor.
- Exact draws use the safety kernel.
- Tablebases or independently checked proofs may discharge already-solved
  external basins.
- A search engine or learned policy can propose capabilities, but does not
  authorize them.
- Failure on a richer position is a residual requiring a new distinction or
  capability, not a reason to relearn the complete game state space.

The V8 qualification gate tests this calculus on the complete declared KPvK
boundary using a compact Syzygy WDL+DTZ policy and universal legal Black
replies.

## 8. Non-claims

This calculus does not by itself prove that a finite small capability basis
covers standard chess. That is an empirical/formal coverage obligation.

It does not establish the game-theoretic value of the standard starting
position until a qualified capability cover reaches that position and all
required adversarial continuations.

It is deliberately independent of any particular decision-tree, neural,
engine, tablebase, or prover implementation.
