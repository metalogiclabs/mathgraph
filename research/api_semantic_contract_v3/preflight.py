#!/usr/bin/env python3
"""Pre-exposure synthetic acceptance/abstention/counterexample tests; no held-out source."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location("prefreeze_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan = load("api_scan")
propose = load("propose")
observe = load("observe")

with TemporaryDirectory() as td:
    root = Path(td)
    pkg = root / "demo_normalizer"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        'import re\n__all__ = ["slugify"]\ndef slugify(s):\n'
        '    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")\n'
    )
    api = scan.identify_public_entrypoint(root)
    assert api["module"] == "demo_normalizer" and api["exports"] == ["slugify"]
    metadata = {"repository": "synthetic/opaque-tool", "source_sha": "b"*40,
                "description": "Experimental string functions"}
    ca = propose.propose(api, metadata, "candidate")
    ex = propose.propose(api, metadata, "expert")
    assert ca["selected"] == ex["selected"] == {"symbol":"slugify","family":"slug"}
    assert [x["id"] for x in ca["obligations"]] == [
        "normalization-idempotence", "url-component-no-extra-encoding"]
    assert ca["obligations"] == ex["obligations"]
    junit = root / "native.xml"
    junit.write_text('<testsuite tests="10" failures="0" errors="0" skipped="1"></testsuite>')
    qualified = observe.judge(ca, ex, metadata, api, root, junit)
    assert qualified["comparison"]["verdict"] == "TIE"
    assert qualified["comparison"]["candidate_independent_warrants"] == 1
    assert qualified["arms"]["candidate"]["verdicts"]["normalization-idempotence"] == "WARRANTED_BOUNDED_NATIVE_METAMORPHIC"
    assert qualified["arms"]["candidate"]["verdicts"]["url-component-no-extra-encoding"] == "WARRANTED_BOUNDED_INDEPENDENT_URL"
    assert all(row["synthetic_bad_path_rejected"] for row in qualified["arms"]["candidate"]["observations"])
    malformed = SimpleNamespace(slugify=lambda s: s+"!")
    bad = observe.check_proposal(ca, malformed, observe.native_receipt(junit))
    assert bad["verdicts"]["url-component-no-extra-encoding"] == "REJECTED_BOUNDED_DECLARED_RELATION"
    assert bad["verdicts"]["normalization-idempotence"] == "REJECTED_BOUNDED_DECLARED_RELATION"
    junit.write_text('<testsuite tests="10" failures="1" errors="0" skipped="0"></testsuite>')
    native_red = observe.check_proposal(ca, malformed, observe.native_receipt(junit))
    assert set(native_red["verdicts"].values()) == {"UNKNOWN_NATIVE_TESTS"}
    unk_api = {"exports":["dumps", "loads"], "relative_api_path":"unknown/__init__.py",
               "module":"unknown", "api_sha256":"0"*64}
    assert propose.propose(unk_api, metadata, "candidate")["status"] == "UNKNOWN_NO_SUPPORTED_RELATION"
print("API_NORMALIZATION_PREFREEZE_SYNTHETIC_PASS")
