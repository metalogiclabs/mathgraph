from mathgraph.programme_controller import (
    EpistemicState,
    Experiment,
    Residual,
    select_experiment,
)


def r(campaign, rid, kind="representation"):
    return Residual(
        campaign=campaign,
        protected_objective=f"{campaign}-objective",
        residual_id=rid,
        residual_kind=kind,
        evidence_refs=(f"evidence:{campaign}:{rid}",),
        state=EpistemicState.UNKNOWN,
    )


def e(eid, campaign, rid, contraction, cost, **kw):
    return Experiment(eid, campaign, rid, "decisive_probe", contraction, cost, **kw)


def test_programme_selector_prefers_contraction_per_cost_not_loudest_project():
    decision = select_experiment(
        [r("collatz", "universal-return"), r("nucleus", "app-fn-type")],
        [
            e("collatz-bruteforce", "collatz", "universal-return", 10, 100),
            e("nucleus-separator", "nucleus", "app-fn-type", 3, 2),
        ],
    )
    assert decision.experiment.experiment_id == "nucleus-separator"


def test_repeated_superseded_or_unverifiable_work_cannot_win_ranking():
    decision = select_experiment(
        [r("arc", "applicability-binding")],
        [
            e("whole-game-retune", "arc", "applicability-binding", 1000, 1,
              repeats_superseded_route=True),
            e("binding-ablation", "arc", "applicability-binding", 2, 2),
        ],
    )
    assert decision.experiment.experiment_id == "binding-ablation"


def test_unearned_distinction_forces_fail_closed_extension():
    decision = select_experiment(
        [r("theorem-transport", "target-interface")],
        [
            e("patch-theorem", "theorem-transport", "target-interface", 100, 1,
              requires_unearned_distinction=True),
        ],
    )
    assert decision.route == "EXTEND_EXPERIMENT_LANGUAGE"
    assert decision.experiment is None


def test_no_typed_residual_means_do_nothing():
    closed = Residual(
        campaign="ethereum",
        protected_objective="exact-state consequence",
        residual_id="done",
        residual_kind="closed",
        evidence_refs=("run:green",),
        state=EpistemicState.WARRANTED,
    )
    decision = select_experiment([closed], [])
    assert decision.route == "DO_NOTHING"


def test_missing_evidence_is_not_actionable():
    residual = Residual(
        campaign="x",
        protected_objective="goal",
        residual_id="r",
        residual_kind="unknown",
        evidence_refs=(),
        state=EpistemicState.UNKNOWN,
    )
    assert select_experiment([residual], []).route == "DO_NOTHING"


def test_zero_cost_positive_contraction_is_supported_deterministically():
    decision = select_experiment(
        [r("reuse", "known-capability")],
        [
            e("reuse-existing", "reuse", "known-capability", 4, 0),
            e("new-search", "reuse", "known-capability", 10, 5),
        ],
    )
    assert decision.experiment.experiment_id == "reuse-existing"
