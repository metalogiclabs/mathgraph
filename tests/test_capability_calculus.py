from mathgraph.capability_calculus import (
    CapabilityStep,
    compile_strategy_calculus,
    forced_goal_attractor,
    safety_kernel,
    verify_strategy_calculus,
)


def test_forced_goal_attractor_handles_adversarial_outcomes():
    states = {"start", "a", "b", "goal", "dead"}
    steps = [
        CapabilityStep("start", "fork-safe", ("a", "b"), frozenset({"w"})),
        CapabilityStep("a", "a-goal", ("goal",), frozenset({"w"})),
        CapabilityStep("b", "b-goal", ("goal",), frozenset({"w"})),
        CapabilityStep("dead", "dead-loop", ("dead",), frozenset({"w"})),
    ]
    winning, rank, witness = forced_goal_attractor(
        states, {"goal"}, steps, {"w"}
    )
    assert winning == frozenset({"start", "a", "b", "goal"})
    assert rank == {"goal": 0, "a": 1, "b": 1, "start": 2}
    assert witness["start"].capability_id == "fork-safe"


def test_safety_kernel_retains_draw_cycle_but_excludes_loss():
    states = {"d0", "d1", "loss"}
    steps = [
        CapabilityStep("d0", "cycle-0", ("d1",), frozenset({"w"})),
        CapabilityStep("d0", "blunder", ("loss",), frozenset({"w"})),
        CapabilityStep("d1", "cycle-1", ("d0",), frozenset({"w"})),
    ]
    safe, witness = safety_kernel(states, {"loss"}, set(), steps, {"w"})
    assert safe == frozenset({"d0", "d1"})
    assert witness["d0"].capability_id == "cycle-0"
    assert witness["d1"].capability_id == "cycle-1"


def test_calculus_prioritizes_forced_progress_then_safety_then_residual():
    states = {"win0", "win1", "goal", "draw0", "draw1", "stuck", "loss"}
    steps = [
        CapabilityStep("win0", "progress-0", ("win1",), frozenset({"w"})),
        CapabilityStep("win1", "progress-1", ("goal",), frozenset({"w"})),
        CapabilityStep("draw0", "draw-0", ("draw1",), frozenset({"w"})),
        CapabilityStep("draw1", "draw-1", ("draw0",), frozenset({"w"})),
        CapabilityStep("stuck", "lose", ("loss",), frozenset({"w"})),
    ]
    result = compile_strategy_calculus(
        states=states,
        goals={"goal"},
        forbidden={"loss"},
        safe_terminals=set(),
        steps=steps,
        live_supports={"w"},
    )
    verify_strategy_calculus(
        result,
        states=states,
        goals={"goal"},
        forbidden={"loss"},
        safe_terminals=set(),
        steps=steps,
        live_supports={"w"},
    )

    decisions = result.decision_map
    assert decisions["win0"].mode == "goal_progress"
    assert decisions["win0"].rank_before == 2
    assert decisions["win0"].rank_after_max == 1
    assert decisions["draw0"].mode == "safety"
    assert {res.state for res in result.residuals} == {"stuck", "loss"}


def test_revocation_reopens_exact_strategy_residual():
    states = {"s", "goal"}
    steps = [
        CapabilityStep(
            "s",
            "certified-step",
            ("goal",),
            frozenset({"authority"}),
            ("evidence:1",),
        )
    ]

    live = compile_strategy_calculus(
        states=states,
        goals={"goal"},
        forbidden=set(),
        safe_terminals=set(),
        steps=steps,
        live_supports={"authority"},
    )
    assert live.forced_goal_states == frozenset({"s", "goal"})
    assert live.decision_map["s"].capability_id == "certified-step"

    revoked = compile_strategy_calculus(
        states=states,
        goals={"goal"},
        forbidden=set(),
        safe_terminals=set(),
        steps=steps,
        live_supports=set(),
    )
    assert revoked.forced_goal_states == frozenset({"goal"})
    assert [res.state for res in revoked.residuals] == ["s"]


def test_safe_terminal_needs_no_outgoing_capability():
    states = {"draw-terminal", "loss"}
    result = compile_strategy_calculus(
        states=states,
        goals=set(),
        forbidden={"loss"},
        safe_terminals={"draw-terminal"},
        steps=[],
        live_supports=set(),
    )
    assert result.safety_states == frozenset({"draw-terminal"})
    assert result.decision_map["draw-terminal"].mode == "safe_terminal"


def test_one_bad_adversarial_outcome_blocks_forced_goal():
    states = {"s", "goal", "bad"}
    steps = [
        CapabilityStep("s", "unsafe-fork", ("goal", "bad"), frozenset({"w"})),
        CapabilityStep("bad", "fake-escape", ("goal",), frozenset({"w"})),
    ]
    result = compile_strategy_calculus(
        states=states,
        goals={"goal"},
        forbidden={"bad"},
        safe_terminals=set(),
        steps=steps,
        live_supports={"w"},
    )
    assert result.forced_goal_states == frozenset({"goal"})
    assert "s" not in result.decision_map


def test_forbidden_state_cannot_reenter_goal_attractor_via_outgoing_edge():
    states = {"goal", "forbidden"}
    steps = [
        CapabilityStep(
            "forbidden",
            "outgoing-but-illegal-for-goal-closure",
            ("goal",),
            frozenset({"w"}),
        )
    ]
    winning, _rank, _witness = forced_goal_attractor(
        states,
        {"goal"},
        steps,
        {"w"},
        {"forbidden"},
    )
    assert winning == frozenset({"goal"})
