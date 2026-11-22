"""Independent finite keyed-agreement reference; no subject code is imported.

The input is a controlled observation corpus, not four executed YAML parsers.
The reference checks each literal expectation and the faithful legacy transcript
projection before a result is written. Agreement is about keyed observations,
not YAML conformance or equality of parsed values.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
BACKENDS = ("lean", "c", "python", "rust")
PRESETS = ("unlimited", "default", "strict", "permissive", "safe_tags")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(case):
    evidence = case["evidence"]
    if evidence["schemaVersion"] != 2 or evidence["comparison"] != "per-case-acceptance":
        raise ValueError("REFERENCE_INPUT_SHAPE_INVALID")
    required = {(b, p) for b in BACKENDS for p in PRESETS}
    runs = evidence["runs"]
    transcripts = case["legacy_transcripts"]
    if (len(runs) != len(required) or len(transcripts) != len(required)
            or {(r["backend"], r["preset"]) for r in runs} != required
            or {(r["backend"], r["preset"]) for r in transcripts} != required):
        raise ValueError("REFERENCE_ROSTER_INCOMPLETE")
    by_run = {(r["backend"], r["preset"]): r["cases"] for r in runs}
    by_transcript = {(r["backend"], r["preset"]): r["stdout"] for r in transcripts}
    observations = {}
    for key, rows in by_run.items():
        if not rows or len({(r["id"], r["variant"]) for r in rows}) != len(rows):
            raise ValueError("REFERENCE_CASE_IDENTITIES_INVALID")
        # This corpus deliberately uses ordinary expected-success cases. An
        # accept/reject observation therefore projects directly to pass/fail.
        if any(r["expectFail"] is not False or r["outcome"] not in ("accepted", "rejected") for r in rows):
            raise ValueError("REFERENCE_CASE_OUTSIDE_FINITE_DOMAIN")
        passed = sum(r["outcome"] == "accepted" for r in rows)
        failed = len(rows) - passed
        progress = [f"  [{i + 1}/{len(rows)}] {r['id']} " +
                    ("✓" if r["outcome"] == "accepted" else "✗ controlled rejection")
                    for i, r in enumerate(rows)]
        progress.append(f"  TOTAL: {passed} passed, {failed} failed, 0 skipped ({len(rows)} total)")
        if by_transcript[key] != "\n".join(progress) + "\n":
            raise ValueError("REFERENCE_LEGACY_PROJECTION_MISMATCH")
        observations[key] = frozenset((r["id"], r["variant"], r["yaml"], r["expectFail"], r["outcome"])
                                      for r in rows)
    presets = [{"preset": p, "agreement": len({observations[b, p] for b in BACKENDS}) == 1}
               for p in PRESETS]
    return {"agreement": all(p["agreement"] for p in presets), "preset_agreement": presets}


def main():
    corpus_path = HERE / "per-case-cases.json"
    data = corpus_path.read_bytes()
    cases = json.loads(data)
    records = []
    for case in cases:
        observed = observe(case)
        if observed != case["expected"]:
            raise ValueError("REFERENCE_EXPECTATION_MISMATCH: " + case["id"])
        records.append({"id": case["id"], "observed": observed})
    result = {"runner_sha256": digest(Path(__file__).read_bytes()),
              "corpus_sha256": digest(data), "records": records}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
