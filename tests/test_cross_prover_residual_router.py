from mathgraph.cross_prover_residual_router import route_surface,route_discovery


def test_residual_classes():
    assert route_surface("EXISTS (x: real): x^2 = 2")=="EXISTENTIAL_WITNESS"
    assert route_surface("NOT (FORALL (x: real): EXISTS (y: real): x*y=1)")=="NEGATED_EXISTENTIAL"
    assert route_surface("FORALL (b: real): (FORALL (z: real): z^2+b>0) IMPLIES b>0")=="QUANTIFIED_PREMISE"
    assert route_surface("FORALL (x: posreal): x+1>1")=="SUBTYPE_RANGE"
    assert route_surface("FORALL (y: nnreal): sqrt(y)+1>=1")=="OPAQUE_OR_NONPOLYNOMIAL"
    assert route_surface("FORALL (x: real): x^2>=3*x^2")=="POLYNOMIAL_CERTIFICATE_GAP"


def test_router_preserves_typed_unknown():
    discovery={
        "unsupported_occurrences":[
            {"theory":"t","formula":"a","normalized_surface":"EXISTS (x: real): x^2 = 2","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"},
            {"theory":"t","formula":"b","normalized_surface":"EXISTS (y: real): y > 0","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"},
            {"theory":"t","formula":"c","normalized_surface":"FORALL (x: posreal): x+1>1","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"},
        ]
    }
    out=route_discovery(discovery)
    assert out["unsupported_count"]==3
    assert out["dominant_residual_class"]=="EXISTENTIAL_WITNESS"
    assert out["dominant_residual_count"]==2
    assert all(x["status"]=="UNKNOWN_UNSUPPORTED_GRAMMAR" for x in out["rows"])
