#!/usr/bin/env python3
"""Frozen native + independently grounded normalization relation evaluator."""
import argparse
import hashlib
import importlib
import json
import pathlib
import sys
import urllib.parse
import xml.etree.ElementTree as ET

INPUTS = [
    "Hello World",
    "RED & blue",
    "two_words",
    "already-safe-123",
    "Multiple   spaces",
    "FAQ: Version 2.0",
]


def native_receipt(junit):
    xml = ET.parse(junit).getroot()
    suites = [xml] if xml.tag == "testsuite" else list(xml.iter("testsuite"))
    tests = sum(int(x.attrib.get("tests", 0)) for x in suites)
    failed = sum(int(x.attrib.get("failures", 0)) for x in suites)
    errors = sum(int(x.attrib.get("errors", 0)) for x in suites)
    skipped_or_xfailed = sum(int(x.attrib.get("skipped", 0)) for x in suites)
    return {
        "tests": tests, "failures": failed, "errors": errors,
        "skipped_or_xfailed": skipped_or_xfailed,
        "native_admissible": tests > skipped_or_xfailed and failed == errors == 0,
    }


def check_proposal(proposal, module, native):
    result = {"arm": proposal["arm"], "status": proposal["status"],
              "selected": proposal["selected"], "observations": []}
    if proposal["selected"] is None:
        result["verdicts"] = {}
        return result
    f = getattr(module, proposal["selected"]["symbol"], None)
    if not callable(f):
        result["verdicts"] = {ob["id"]: "UNKNOWN_NOT_CALLABLE" for ob in proposal["obligations"]}
        return result
    rows = []
    for index, value in enumerate(INPUTS):
        row = {"sample": index, "input": value}
        try:
            normalized = f(value)
            row["output"] = repr(normalized)[:250]
            row["output_type"] = type(normalized).__name__
            if not isinstance(normalized, str):
                row["idempotent"] = None
                row["url_no_extra_encoding"] = None
                row["synthetic_bad_path_rejected"] = None
                row["unsupported"] = "non-string output"
            else:
                row["idempotent"] = (f(normalized) == normalized)
                row["url_no_extra_encoding"] = (urllib.parse.quote(normalized, safe="") == normalized)
                # Fault injection deliberately corrupts the OBSERVED OUTPUT, not original source.
                # Independent URL encoder must distinguish a bogus unescaped exclamation mark.
                broken = normalized + "!"
                row["synthetic_bad_path_rejected"] = (urllib.parse.quote(broken, safe="") != broken)
        except Exception as exc:
            row.update({"idempotent": None, "url_no_extra_encoding": None,
                        "synthetic_bad_path_rejected": None,
                        "unsupported": type(exc).__name__ + ": " + str(exc)[:180]})
        rows.append(row)
    result["observations"] = rows
    verdicts = {}
    for obligation in proposal["obligations"]:
        if not native["native_admissible"]:
            verdicts[obligation["id"]] = "UNKNOWN_NATIVE_TESTS"
            continue
        key = ("idempotent" if obligation["id"] == "normalization-idempotence"
               else "url_no_extra_encoding")
        vals = [v[key] for v in rows]
        if obligation["id"] == "url-component-no-extra-encoding" and not all(
            row["synthetic_bad_path_rejected"] is True for row in rows
        ):
            verdicts[obligation["id"]] = "UNKNOWN_INDEPENDENT_NEGATIVE_CONTROL"
        elif all(v is True for v in vals):
            verdicts[obligation["id"]] = (
                "WARRANTED_BOUNDED_INDEPENDENT_URL" if key == "url_no_extra_encoding"
                else "WARRANTED_BOUNDED_NATIVE_METAMORPHIC"
            )
        elif any(v is False for v in vals):
            verdicts[obligation["id"]] = "REJECTED_BOUNDED_DECLARED_RELATION"
        else:
            verdicts[obligation["id"]] = "UNKNOWN_UNSUPPORTED_NATIVE_INPUT"
    result["verdicts"] = verdicts
    return result


def judge(candidate, expert, metadata, api, source, junit):
    assert candidate["arm"] == "candidate" and expert["arm"] == "expert"
    for proposal in (candidate, expert):
        assert proposal["protocol"] == "API_NORMALIZATION_CONTRACT_V3"
        assert proposal["source_sha"] == metadata["source_sha"]
        assert proposal["repository"] == metadata["repository"]
        assert proposal["api_sha256"] == api["api_sha256"]
        assert proposal["api_module"] == api["module"]
        assert proposal["relative_api_path"] == api["relative_api_path"]
        assert proposal["public_symbols"] == api["exports"]
    assert candidate["source_sha"] == expert["source_sha"]
    sys.path.insert(0, str(source.resolve() / "src"))
    sys.path.insert(0, str(source.resolve()))
    module = importlib.import_module(api["module"])
    assert pathlib.Path(module.__file__).resolve().is_relative_to(source.resolve()), "UNPINNED_MODULE"
    native = native_receipt(junit)
    arms = {"candidate": check_proposal(candidate, module, native),
            "expert": check_proposal(expert, module, native)}
    def score(item):
        return sum(s == "WARRANTED_BOUNDED_INDEPENDENT_URL" for s in item["verdicts"].values())
    def false_promotions(item):
        return sum(s.startswith("WARRANTED") and any(
            (obs.get("url_no_extra_encoding") is False if k == "url-component-no-extra-encoding"
             else obs.get("idempotent") is False)
            for obs in item["observations"]
        ) for k,s in item["verdicts"].items())
    cscore, escore = score(arms["candidate"]), score(arms["expert"])
    return {
        "source": metadata, "native": native, "arms": arms,
        "comparison": {
            "candidate_independent_warrants": cscore,
            "expert_independent_warrants": escore,
            "advantage": cscore - escore,
            "candidate_false_promotions": false_promotions(arms["candidate"]),
            "expert_false_promotions": false_promotions(arms["expert"]),
            "baseline": "equally informed expert-authored rulebook, NOT a blinded human reviewer",
            "verdict": ("TIE" if cscore == escore else "CANDIDATE_AHEAD" if cscore > escore else "EXPERT_AHEAD"),
        },
        "limitation": "Frozen finite naming relation. URL standard-library observer proves only bounded no-extra-encoding, not overall safe URL or source author intent. Native idempotence is NOT independent meaning.",
    }


def main():
    ap = argparse.ArgumentParser()
    for name in ("metadata", "api_view", "candidate", "expert", "source", "native_junit", "output"):
        ap.add_argument("--" + name.replace("_", "-"), type=pathlib.Path, required=True)
    a = ap.parse_args()
    metadata = json.loads(a.metadata.read_text())
    api = json.loads(a.api_view.read_text())
    candidate = json.loads(a.candidate.read_text())
    expert = json.loads(a.expert.read_text())
    receipt = judge(candidate, expert, metadata, api, a.source, a.native_junit)
    receipt["proposal_sha256"] = {
        "candidate": hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
        "expert": hashlib.sha256(a.expert.read_bytes()).hexdigest(),
        "native_junit": hashlib.sha256(a.native_junit.read_bytes()).hexdigest(),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print("NORMALIZATION_API_PROSPECTIVE_RESULT",
          json.dumps({"native": receipt["native"], "comparison": receipt["comparison"],
                      "candidate_verdicts": receipt["arms"]["candidate"]["verdicts"],
                      "expert_verdicts": receipt["arms"]["expert"]["verdicts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
