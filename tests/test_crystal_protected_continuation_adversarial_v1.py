from mathgraph.crystal import (
    AdapterContract, ControlMap, Hyperedge, IntervalDistributionEffect, IntervalOutcome,
    ObservationMap, RateKernelEffect, RateOutcome, SemanticObject,
    compose_adapter_contracts, greatest_viability_kernel,
)
from mathgraph.protected_future import ContinuationStatus, ProtectedContinuation, ProtectedContinuationMachine


def interval_machine(name, effect):
    return ProtectedContinuationMachine(
        "quantitative:interval",
        (name,),
        tuple(
            ProtectedContinuation(
                name, f"probability:{o.target}", (o.lower,o.upper),
                ContinuationStatus.WARRANTED, target=None
            )
            for o in effect.outcomes
        ),
    )


def rate_machine(name, effect):
    return ProtectedContinuationMachine(
        "quantitative:rate",
        (name,),
        tuple(
            ProtectedContinuation(
                name, f"rate:{o.target}", (o.rate,),
                ContinuationStatus.WARRANTED, target=None
            )
            for o in effect.outcomes
        ),
    )


def test_quantitative_intervals_survive_when_qualitative_support_is_identical():
    low=IntervalDistributionEffect((IntervalOutcome("goal","0.4","0.4"),IntervalOutcome("other","0.6","0.6")))
    high=IntervalDistributionEffect((IntervalOutcome("goal","0.6","0.6"),IntervalOutcome("other","0.4","0.4")))
    assert low.qualitative_support==high.qualitative_support
    lm=interval_machine("q",low); hm=interval_machine("q",high)
    assert lm.lower_signature("q") != hm.lower_signature("q")
    assert ("probability:goal",("0.4","0.4"),None) in lm.lower_signature("q")
    assert ("probability:goal",("0.6","0.6"),None) in hm.lower_signature("q")


def test_probability_and_rate_semantics_do_not_collapse():
    probability=IntervalDistributionEffect((IntervalOutcome("x","1","1"),))
    rate=RateKernelEffect((RateOutcome("x","1"),))
    pm=interval_machine("q",probability); rm=rate_machine("q",rate)
    assert pm.lower_signature("q") != rm.lower_signature("q")
    assert pm.lower_signature("q")==(("probability:x",("1","1"),None),)
    assert rm.lower_signature("q")==(("rate:x",("1",),None),)


def observation_machine(name, obs):
    states=tuple(state for state,_ in obs.entries)
    return ProtectedContinuationMachine(
        f"observer:{name}", states,
        tuple(ProtectedContinuation(state,"observe",(value,),ContinuationStatus.WARRANTED) for state,value in obs.entries),
    )


def test_observer_partition_is_exact_future_quotient_view():
    underlying=("s1-h1","s1-h2","s1-h3")
    partial=ObservationMap(tuple((s,"s=1") for s in underlying))
    full=ObservationMap(tuple((s,s) for s in underlying))
    pm=observation_machine("partial",partial); fm=observation_machine("full",full)
    assert set(pm.future_classes().values())=={underlying}
    assert set(fm.future_classes().values())=={(s,) for s in underlying}
    assert pm.id != fm.id


def control_machine(name, control):
    points=tuple(point for point,_ in control.entries)
    return ProtectedContinuationMachine(
        f"control:{name}", points,
        tuple(ProtectedContinuation(point,"controller",(controller,),ContinuationStatus.WARRANTED) for point,controller in control.entries),
    )


def test_local_control_survives_exactly_when_it_changes_protected_future():
    original=ControlMap((("module:host","p1"),("action:send1","p1"),("action:send2","p1"),("module:client","p2")))
    swapped=ControlMap((("module:host","p2"),("action:send1","p2"),("action:send2","p2"),("module:client","p1")))
    om=control_machine("original",original); sm=control_machine("swapped",swapped)
    assert om.lower_signature("module:host") != sm.lower_signature("module:host")
    assert om.id != sm.id


def adapter_machine(contract, requested):
    return ProtectedContinuationMachine(
        f"adapter:{contract.source_space}->{contract.target_space}",
        (contract.source_space,),
        tuple(
            ProtectedContinuation(
                contract.source_space, f"preserve:{interface}", (contract.target_space,),
                ContinuationStatus.WARRANTED if interface in contract.preserves_interfaces else ContinuationStatus.UNKNOWN,
                evidence_refs=contract.evidence_refs if interface in contract.preserves_interfaces else (),
            )
            for interface in requested
        ),
    )


def test_composed_adapter_lineage_is_preserved_without_becoming_state():
    I="i@1"; J="j@1"; K="k@1"
    a=AdapterContract("A",1,"S","M",(I,J),assumption_refs=("a",),evidence_refs=("ev:A",))
    b=AdapterContract("B",1,"M","N",(I,K),assumption_refs=("b",),evidence_refs=("ev:B",))
    c=AdapterContract("C",1,"N","T",(I,J,K),assumption_refs=("c",),evidence_refs=("ev:C",))
    left=compose_adapter_contracts(compose_adapter_contracts(a,b),c)
    right=compose_adapter_contracts(a,compose_adapter_contracts(b,c))
    assert left==right
    lm=adapter_machine(left,(I,J,K)); rm=adapter_machine(right,(I,J,K))
    assert lm==rm
    warranted=[e for e in lm.continuations if e.status is ContinuationStatus.WARRANTED]
    unknown=[e for e in lm.continuations if e.status is ContinuationStatus.UNKNOWN]
    assert [e.continuation for e in warranted]==["preserve:i@1"]
    assert {e.continuation for e in unknown}=={"preserve:j@1","preserve:k@1"}
    assert warranted[0].evidence_refs==left.evidence_refs


def test_revocation_and_resource_mutation_need_no_coordinate_beyond_support_and_target():
    states={"ready","spent"}; failures=("fail",)
    edges=[Hyperedge("ready","spent","fail",frozenset({"repair"}))]
    m=ProtectedContinuationMachine(
        "resource",
        tuple(states),
        (ProtectedContinuation("ready","failure:fail",("repair",),ContinuationStatus.WARRANTED,target="spent",support_refs=("repair",)),),
    )
    assert m.live_signature("ready",{"repair"})==(("failure:fail",("repair",),"spent"),)
    assert m.live_signature("ready",set())==()
    assert greatest_viability_kernel(states,failures,edges,{"repair"})==frozenset()


def test_unknown_future_interface_is_unknown_continuation_not_new_core_type():
    future=SemanticObject("effect.weird.future.physics",1,b"opaque",("future.physics@1",))
    before=ProtectedContinuationMachine(
        "future-interface", (future.id,),
        (ProtectedContinuation(future.id,"interpret:future.physics@1",(future.id,),ContinuationStatus.UNKNOWN),),
    )
    after=ProtectedContinuationMachine(
        "future-interface", (future.id,),
        (ProtectedContinuation(future.id,"interpret:future.physics@1",(future.id,),ContinuationStatus.WARRANTED,evidence_refs=("future-interpreter:v1",)),),
    )
    assert before.unresolved(future.id)
    assert after.unresolved(future.id)==()
    assert before.states==after.states==(future.id,)
    assert future==SemanticObject.from_bytes(future.to_bytes())
