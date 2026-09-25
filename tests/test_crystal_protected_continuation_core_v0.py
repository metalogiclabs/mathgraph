from mathgraph.crystal import AdapterContract, Hyperedge, greatest_viability_kernel
from mathgraph.finite_falsifier import FiniteFalsifierWitness
from mathgraph.finite_relation import FiniteObservationProfile, FinitePredicateProfile, predicate_equivalent, predicate_implies, predicate_separator, quotient_falsifiers
from mathgraph.graph_invariants import FiniteSimpleGraphPayload, has_isolated_vertex, maximum_matching_number, minimum_edge_cover_number
from mathgraph.math_claim import MathClaimPayload, VerifiedClaimRelation, quotient_by_verified_equivalence
from mathgraph.protected_future import ContinuationStatus, ProtectedContinuation, ProtectedContinuationMachine, equivalence_classes_from_relations, relation_machine

def test_math_claim_relations_are_lossless_relation_view():
    a=MathClaimPayload("a","lean",(),(),"P","src:a").semantic_object()
    b=MathClaimPayload("b","smt",(),(),"P","src:b").semantic_object()
    c=MathClaimPayload("c","lean",(),(),"Q","src:c").semantic_object()
    relations=(
        VerifiedClaimRelation(a.id,b.id,"equivalent",("ev:eq",)),
        VerifiedClaimRelation(c.id,a.id,"implies",("ev:imp",)),
        VerifiedClaimRelation(a.id,c.id,"separated",("ev:sep",),(("x",True),)),
    )
    old=quotient_by_verified_equivalence((a.id,b.id,c.id),relations)
    m=relation_machine((a.id,b.id,c.id),tuple((r.left_object_id,r.right_object_id,r.relation,r.evidence_refs) for r in relations),boundary_ref="claim")
    assert equivalence_classes_from_relations(m)==old
    assert {(e.source,e.continuation,e.outcome[0]) for e in m.continuations}=={(r.left_object_id,f"relation:{r.relation}",r.right_object_id) for r in relations}

def test_finite_relation_operations_are_future_signature_views():
    cases=("00","01","10","11")
    left=FinitePredicateProfile("left",cases,(False,False,True,True))
    eq=FinitePredicateProfile("eq",cases,(False,False,True,True))
    strong=FinitePredicateProfile("strong",cases,(False,False,False,True))
    def pm(profile):
        return ProtectedContinuationMachine("pred",cases,tuple(ProtectedContinuation(c,"evaluate",("true" if t else "false",),ContinuationStatus.WARRANTED) for c,t in zip(profile.cases,profile.truth)))
    ml,me,ms=pm(left),pm(eq),pm(strong)
    assert predicate_equivalent(left,eq)==(tuple(ml.lower_signature(c) for c in cases)==tuple(me.lower_signature(c) for c in cases))
    assert predicate_implies(strong,left)
    assert predicate_separator(left,strong)[0]=="10"
    assert ml.lower_signature("10")!=ms.lower_signature("10")
    rep=FiniteObservationProfile("rep",("a","b","c"),(("x",),("x",),("y",)))
    protected=FiniteObservationProfile("protected",("a","b","c"),(("0",),("1",),("0",)))
    old=quotient_falsifiers(rep,protected)
    def om(p):
        return ProtectedContinuationMachine("obs",p.cases,tuple(ProtectedContinuation(c,"observe",sig,ContinuationStatus.WARRANTED) for c,sig in zip(p.cases,p.signatures)))
    rm,tm=om(rep),om(protected)
    new=[]
    for i,a in enumerate(rep.cases):
        for b in rep.cases[i+1:]:
            if rm.lower_signature(a)==rm.lower_signature(b) and tm.lower_signature(a)!=tm.lower_signature(b):
                new.append((a,b))
    assert tuple(new)==old

def test_graph_invariants_are_protected_observation_view():
    g=FiniteSimpleGraphPayload(4,((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)))
    rho=minimum_edge_cover_number(g); nu=maximum_matching_number(g)
    m=ProtectedContinuationMachine("gallai:K4",("K4",),(
        ProtectedContinuation("K4","edge-cover-defined",(str(rho is not None),),ContinuationStatus.WARRANTED),
        ProtectedContinuation("K4","min-edge-cover",(str(rho),),ContinuationStatus.WARRANTED),
        ProtectedContinuation("K4","max-matching",(str(nu),),ContinuationStatus.WARRANTED),
        ProtectedContinuation("K4","has-isolated",(str(has_isolated_vertex(g)),),ContinuationStatus.WARRANTED),
    ))
    sig={name:outcome for name,outcome,_ in m.lower_signature("K4")}
    assert sig=={"edge-cover-defined":("True",),"has-isolated":("False",),"max-matching":("2",),"min-edge-cover":("2",)}

def test_falsifier_witness_is_excluded_future_view():
    w=FiniteFalsifierWitness("magma","commutative","order2","0,1",b"xy=0,yx=1","finite-enum",("run:1",))
    m=ProtectedContinuationMachine(w.boundary_ref,(w.case_id,),(ProtectedContinuation(w.case_id,f"claim:{w.claim_ref}",("holds",),ContinuationStatus.EXCLUDED,evidence_refs=w.evidence_refs+(w.verifier_ref,)),))
    assert m.lower_signature(w.case_id)==()
    assert m.upper_signature(w.case_id)==()
    assert m.continuations[0].status is ContinuationStatus.EXCLUDED

def test_adapter_contract_is_three_valued_preservation_view():
    c=AdapterContract("a",1,"S","T",("i1","i2"),evidence_refs=("run:adapter",))
    requested=("i1","i2","i3")
    m=ProtectedContinuationMachine("adapter:a",("S",),tuple(ProtectedContinuation("S",f"preserve:{i}",("T",),ContinuationStatus.WARRANTED if i in c.preserves_interfaces else ContinuationStatus.UNKNOWN,evidence_refs=c.evidence_refs if i in c.preserves_interfaces else ()) for i in requested))
    assert {e.continuation for e in m.edges_from("S") if e.status is ContinuationStatus.WARRANTED}=={"preserve:i1","preserve:i2"}
    assert tuple(e.continuation for e in m.unresolved("S"))==("preserve:i3",)

def test_viability_is_live_supported_future_view():
    states={"ready","spent"}; failures=("fail",); live={"repair"}
    one=[Hyperedge("ready","spent","fail",frozenset({"repair"}))]
    rep=[Hyperedge("ready","ready","fail",frozenset({"repair"}))]
    def hm(edges):
        return ProtectedContinuationMachine("viability",tuple(states),tuple(ProtectedContinuation(e.source,f"failure:{e.failure_class}",("repair",),ContinuationStatus.WARRANTED,target=e.target,support_refs=tuple(e.support_refs),evidence_refs=e.evidence_refs) for e in edges))
    one_m,rep_m=hm(one),hm(rep)
    assert one_m.live_signature("ready",live)==(("failure:fail",("repair",),"spent"),)
    assert rep_m.live_signature("ready",live)==(("failure:fail",("repair",),"ready"),)
    assert greatest_viability_kernel(states,failures,one,live)==frozenset()
    assert greatest_viability_kernel(states,failures,rep,live)==frozenset({"ready"})
    assert one_m.live_signature("ready",set())==()

def test_three_values_realize_future_bracket_and_roundtrip():
    m=ProtectedContinuationMachine("bracket",("q",),(
        ProtectedContinuation("q","proved",("yes",),ContinuationStatus.WARRANTED),
        ProtectedContinuation("q","refuted",("yes",),ContinuationStatus.EXCLUDED),
        ProtectedContinuation("q","open",("yes",),ContinuationStatus.UNKNOWN),
    ))
    assert [x[0] for x in m.lower_signature("q")]==["proved"]
    assert [x[0] for x in m.upper_signature("q")]==["open","proved"]
    assert [e.continuation for e in m.unresolved("q")]==["open"]
    obj=m.semantic_object()
    assert obj.type_id=="future.protected.partial@1"
    assert obj==type(obj).from_bytes(obj.to_bytes())
