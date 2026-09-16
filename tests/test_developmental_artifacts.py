import pytest

from mathgraph.developmental_artifacts import (
    VerifiedCapabilityBlock,
    VerifiedDevelopmentTransition,
    VerifiedObstruction,
)


def test_capability_block_hash_is_stable_and_scope_is_explicit():
    block = VerifiedCapabilityBlock(
        capability_id="cap:test",
        applicability={"source_family": "fresh_v81"},
        action={"kind": "retain_round1_node", "node_id": 7},
        verifier_boundary="replay_verified_critical_pair",
        certificate_refs=("sha256:abc",),
        provenance=("v81:fresh:source:1",),
        dependencies=("source",),
        scope={"horizon": 2, "budget": 5},
        causal_evidence=("warm_cold_counterfactual",),
        persistence_hash="sha256:def",
    )
    assert block.stable_hash() == block.stable_hash()
    assert block.to_dict()["scope"]["budget"] == 5


def test_obstruction_requires_positive_residual():
    with pytest.raises(ValueError, match="residual"):
        VerifiedObstruction(
            obstruction_id="obs:test",
            prior_state=(1, 2, 3, 4, 5),
            prior_scope={"horizon": 2},
            extended_scope={"horizon": 3},
            exact_global_old=100,
            persistent_value_new=120,
            exact_global_new=120,
            residual=0,
            provenance=("v81",),
        )


def test_transition_rejects_admitted_nonpositive_delta():
    with pytest.raises(ValueError, match="positive"):
        VerifiedDevelopmentTransition(
            transition_id="dev:test",
            from_state=(1, 2, 3, 4, 5),
            proposal={"drop": 1, "add": 6},
            verifier="exact_frontier",
            delta=0,
            admitted=True,
            to_state=(2, 3, 4, 5, 6),
            causal_witnesses=(),
            exact_optimality_status="unknown",
        )
