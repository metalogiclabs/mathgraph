from pathlib import Path

from mathgraph.breakthrough_lineage import historical_lineage_manifest, validate_historical_lineage


def test_lineage_contains_required_stages_and_exact_v80_identifiers():
    manifest = historical_lineage_manifest()
    names = [stage["stage"] for stage in manifest["stages"]]
    assert names == [
        "trust_boundary",
        "sair_official_pack",
        "v66",
        "v72",
        "v73",
        "v74",
        "v75",
        "v76",
        "v77",
        "v78",
        "v79",
        "v80",
    ]
    v80 = next(stage for stage in manifest["stages"] if stage["stage"] == "v80")
    assert v80["run_id"] == 35058339100
    assert v80["commit_sha"] == "6cf0db1455e517899fc76dbb4bde6087f8ca1204"
    assert v80["artifact_id"] == 10432568044
    assert v80["protocol_sha256"] == "9eb6155def95e3a6cedc324ed31decc49434e1956fe54da730703c36d2b3be2e"
    assert v80["developer_sha256"] == "82a884cf7b233b305f5fe3f7ec7f79e652cfd63ea0ad9e370bf0f53acbf92eed"
    assert v80["verdict"] == "PASS_PROSPECTIVE_DEEP_HORIZON_ACTION_INVARIANCE_V80"


def test_v79_is_negative_posthoc_calibration_not_action_expansion_success():
    manifest = historical_lineage_manifest()
    v79 = next(stage for stage in manifest["stages"] if stage["stage"] == "v79")
    assert v79["freshness"] == "posthoc_calibration"
    assert v79["verdict"] == "NO_CERTIFIED_ACTION_LANGUAGE_OBSTRUCTION_V79"
    assert v79["claim"] == "no one-swap local trap found in selected bounded depth-5 calibration"


def test_repo_local_lineage_validation_never_promotes_missing_external_artifacts():
    report = validate_historical_lineage(Path("."))
    assert report["repo_local_files_ok"] is True
    assert report["historical_status"] in {"HISTORICAL_LINEAGE_VALIDATED", "UNVERIFIED_IN_THIS_RUN"}
    assert report["missing_external_artifact_policy"] == "UNVERIFIED_IN_THIS_RUN"
