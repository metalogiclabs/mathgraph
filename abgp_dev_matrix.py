from __future__ import annotations

from pathlib import Path

from mathgraph.abgp.runner import run_dev_matrix, write_dev_summary


OUTPUT = Path("abgp-dev-matrix-summary.json")


def main() -> None:
    summary = run_dev_matrix()
    write_dev_summary(OUTPUT, summary)
    print("REALITYGRAPH / ABGP DEV MATRIX V1")
    print("--------------------------------")
    for arm in ("A", "B", "G", "P"):
        result = summary["analysis"]["arms"][arm]
        print(
            f"{arm} dev_verdict={result['verdict']} "
            f"effect={result['effect']:.6f} "
            f"raw_p={result['raw_pvalue']:.6g} "
            f"holm_p={result['holm_adjusted_pvalue']:.6g}"
        )
    print("scientific_status", summary["scientific_status"])
    print("confirmatory_namespace_used", int(summary["confirmatory_namespace_used"]))
    print("ABGP_DEV_MATRIX_OK")


if __name__ == "__main__":
    main()
