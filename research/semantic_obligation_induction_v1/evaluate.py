#!/usr/bin/env python3
"""Frozen independent semantic oracle, native-test gate and matched-arm report."""
import argparse, hashlib, importlib, json, pathlib, sys, xml.etree.ElementTree as ET

SAMPLES = [
    {"plain": "hello", "literal_null": "null", "flag": True, "integer": 42},
    {"truth_word": "true", "number_word": "42", "nested": {"text": "false", "count": 7}},
    {"array": [1, 2, 3], "escaped": 'quoted " text', "unicode": "café"},
]


def native_tests(junit):
    root = ET.parse(junit).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
    tests = sum(int(s.attrib.get("tests", 0)) for s in suites)
    failures = sum(int(s.attrib.get("failures", 0)) for s in suites)
    errors = sum(int(s.attrib.get("errors", 0)) for s in suites)
    skipped = sum(int(s.attrib.get("skipped", 0)) for s in suites)
    return {"tests": tests, "failures": failures, "errors": errors, "skipped": skipped,
            "passed": tests > 0 and failures == errors == 0 and tests > skipped}


def compare(proposal, module, independent, native):
    output = {"arm": proposal["arm"], "proposal_status": proposal["status"],
              "proposal_digest": hashlib.sha256(json.dumps(proposal, sort_keys=True).encode()).hexdigest(),
              "obligations": []}
    for item in proposal["obligations"]:
        relation = {"id": item["id"], "relation": item["relation"], "observations": []}
        for case_no, sample in enumerate(SAMPLES):
            obs = {"sample_index": case_no}
            try:
                writer = getattr(module, item["writer"])
                encoded = writer(sample)
                if item["id"] == "external-semantics":
                    # This oracle uses Python's independent standard-library implementation,
                    # not the candidate's own decoder.
                    decoded = independent(encoded)
                    obs["same_typed_meaning"] = (type(decoded) is dict and decoded == sample)
                    altered = {**sample, "__wrong_expected_value__": "separate"}
                    obs["false_claim_rejected"] = (decoded != altered)
                else:
                    reader = getattr(module, item["reader"])
                    decoded = reader(encoded)
                    obs["same_typed_meaning"] = (decoded == sample)
                    obs["false_claim_rejected"] = (decoded != {**sample, "__wrong_expected_value__": "separate"})
                obs["encoded_type"] = type(encoded).__name__
                if not isinstance(encoded, str):
                    obs["same_typed_meaning"] = False
                    obs["reason"] = "writer did not produce expected text"
            except Exception as exc:
                obs["same_typed_meaning"] = None
                obs["false_claim_rejected"] = None
                obs["reason"] = type(exc).__name__ + ": " + str(exc)[:220]
            relation["observations"].append(obs)
        vals = [x["same_typed_meaning"] for x in relation["observations"]]
        negatives = [x["false_claim_rejected"] for x in relation["observations"]]
        if not native["passed"]:
            verdict = "UNKNOWN_NATIVE_TESTS"
        elif all(x is True for x in vals) and all(x is True for x in negatives):
            verdict = ("WARRANTED_BOUNDED_INDEPENDENT" if item["id"] == "external-semantics"
                       else "WARRANTED_BOUNDED_NATIVE_CONSISTENCY")
        elif any(x is False for x in vals):
            verdict = ("REJECTED_BOUNDED_INDEPENDENT" if item["id"] == "external-semantics"
                       else "REJECTED_BOUNDED_NATIVE_CONSISTENCY")
        else:
            verdict = "UNKNOWN_UNSUPPORTED_INPUT_OR_ORACLE"
        relation["verdict"] = verdict
        output["obligations"].append(relation)
    return output


def main():
    ap = argparse.ArgumentParser()
    for name in ("metadata", "candidate", "expert", "source", "native_junit", "output"):
        ap.add_argument("--" + name.replace("_", "-"), type=pathlib.Path, required=True)
    a = ap.parse_args()
    metadata = json.loads(a.metadata.read_text())
    candidate = json.loads(a.candidate.read_text())
    expert = json.loads(a.expert.read_text())
    assert candidate["arm"] == "candidate" and expert["arm"] == "expert"
    for proposal in (candidate, expert):
        assert proposal["source_sha"] == metadata["source_sha"]
        assert proposal["repository"] == metadata["repository"]
        assert proposal["format"] == candidate["format"]
        assert proposal["api_sha256"] == candidate["api_sha256"], "different API knowledge"
    native = native_tests(a.native_junit)
    mod_name = metadata["repository"].split("/")[-1].replace("-", "_")
    sys.path.insert(0, str(a.source.resolve()))
    module = importlib.import_module(mod_name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(a.source.resolve()), "wrong imported source"
    fmt = candidate["format"]
    if fmt == "toml":
        import tomllib
        independent = tomllib.loads
    elif fmt == "json":
        independent = json.loads
    else:
        independent = None
    if independent is None:
        result = {"source_sha": metadata["source_sha"], "native": native,
                  "candidate": {"status": "UNKNOWN_UNSUPPORTED_FORMAT"},
                  "expert": {"status": "UNKNOWN_UNSUPPORTED_FORMAT"}, "comparison": "NOT_ELIGIBLE"}
    else:
        ca = compare(candidate, module, independent, native)
        ex = compare(expert, module, independent, native)
        def score(r):
            return sum(x["verdict"] == "WARRANTED_BOUNDED_INDEPENDENT" for x in r["obligations"])
        result = {"source_sha": metadata["source_sha"], "format": fmt, "native": native,
                  "candidate": ca, "expert": ex,
                  "comparison": {"candidate_warranted_independent": score(ca),
                                 "expert_warranted_independent": score(ex),
                                 "advantage": score(ca) - score(ex),
                                 "baseline_type": "predeclared expert-authored cookbook, not a recruited external reviewer"}}
    result.update({
        "status": "PROSPECTIVE_EXECUTED_BOUNDED" if native["passed"] else "UNKNOWN_NATIVE_AUTHORITY",
        "bounds": "Fixed naming+format grammar, small input corpus and stdlib parser; NOT arbitrary intent discovery or comparative superiority from a tie.",
        "candidate_proposal_file_sha256": hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
        "expert_proposal_file_sha256": hashlib.sha256(a.expert.read_bytes()).hexdigest(),
        "native_junit_sha256": hashlib.sha256(a.native_junit.read_bytes()).hexdigest(),
    })
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PROSPECTIVE_COMPARISON", json.dumps({"source": metadata["repository"],
          "native": native, "comparison": result["comparison"], "status": result["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
