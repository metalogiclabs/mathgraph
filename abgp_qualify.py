from __future__ import annotations

from pathlib import Path

from mathgraph.abgp.qualification import run_qualification, write_qualification_artifact


OUTPUT = Path("abgp-qualification-summary.json")


def main() -> None:
    artifact = run_qualification()
    write_qualification_artifact(OUTPUT, artifact)
    print("REALITYGRAPH / ABGP TEST QUALIFICATION V1")
    print("---------------------------------------")
    print("verdict", artifact["verdict"])
    print("implementation_qualified", int(artifact["implementation_qualified"]))
    print("complete_pass_power_qualified", int(artifact["complete_pass_power_qualified"]))
    print("fixtures", artifact["fixture_count"])
    print("statistical_reference", artifact["statistical_reference_audit"]["status"])
    print("historical_component_power_qualified", int(bool(artifact["power_audit"]["qualified"])))
    print("confirmatory_namespace_used", int(artifact["confirmatory_namespace_used"]))
    print("qualification_digest", artifact["qualification_digest"])
    if artifact["verdict"] == "HARNESS_QUALIFIED":
        print("ABGP_HARNESS_QUALIFIED")
        return
    print("ABGP_NOT_QUALIFIED")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
