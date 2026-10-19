#!/usr/bin/env python3
"""Apply original unchanged cross-domain V1 warrant evaluator to V6 source-native Lean receipt."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cross_domain_correspondence_v1"))
from protocol import Obligation, assess  # exact frozen V1 core, not copied or edited

root = Path(sys.argv[1])
receipt_bytes = (root / "receipt.json").read_bytes()
receipt = json.loads(receipt_bytes)
assert receipt["status"] == "WARRANTED_BOUNDED_POSITIVE_NONEMPTY_TYPED_PKCSOURCE_STATEMENT_CORRESPONDENCE"
assert receipt["source_native_sysml_to_api_to_kernel"] is True
assert receipt["source_modified"] is False
assert receipt["checked_cases"] == {
    "typed_match": "MATCH", "false_mismatch": "MISMATCH",
    "typed_mismatch": "MISMATCH", "wrong_citation": "MISMATCH",
    "unsupported": "UNKNOWN_UNSUPPORTED", "true_unsupported": "UNKNOWN_UNSUPPORTED",
    "no_statement": "NO_ASSERTION",
}
source = receipt["upstream"]
required = {
    "source": source,
    "native": hashlib.sha256(receipt_bytes).hexdigest(),
    "interpretation": "PKC_TYPED_EDGE_V1_EXPLICIT_3_KINDS_AND_FALSE",
    "citation_type": "ORIGINAL_PKCIso80000_Part3_EDGE_CONSTRUCTOR",
}
case_relation = {
    "MATCH": "MATCH", "MISMATCH": "MISMATCH",
    "UNKNOWN_UNSUPPORTED": "UNSUPPORTED", "NO_ASSERTION": "NO_ASSERTION",
}
items = tuple(
    Obligation(name=k, source=source, relation=case_relation[v],
               authority="ASSERTED", dependencies=tuple(required.keys()),
               qualifier="Only if optional text is an asserted proposition under explicit V6 typed grammar")
    for k, v in receipt["checked_cases"].items()
)
verdicts = assess(items, required, required)
expected = {
    "typed_match": "SCOPED_AGREEMENT",
    "false_mismatch": "DIVERGENT_BOUNDED",
    "typed_mismatch": "DIVERGENT_BOUNDED",
    "wrong_citation": "DIVERGENT_BOUNDED",
    "unsupported": "UNKNOWN_INTERPRETATION",
    "true_unsupported": "UNKNOWN_INTERPRETATION",
    "no_statement": "NO_SEMANTIC_ASSERTION",
}
assert verdicts == expected, verdicts

mutant = dict(required, citation_type="WITHDRAWN")
withdrawn = assess(items, mutant, required)
assert set(withdrawn.values()) == {"UNKNOWN_WITHDRAWN_OR_CHANGED"}
assert assess(items, required, required) == expected
positive = next(x for x in items if x.name == "typed_match")
annotation = Obligation(**{**vars(positive), "authority": "ANNOTATION"})
unresolved = Obligation(**{**vars(positive), "authority": "UNRESOLVED"})
from protocol import judge
assert judge(annotation, required, required) == "NO_SEMANTIC_ASSERTION"
assert judge(unresolved, required, required) == "UNKNOWN_CONTRACT"

manifest = {
    "version": "PKC_TYPED_NONEMPTY_INTO_FROZEN_CROSS_DOMAIN_V1",
    "source": source,
    "source_native_receipt_sha256": required["native"],
    "verdicts_conditional_on_asserted_field_contract": verdicts,
    "all_warrants_withdrawn_when_original_citation_type_changes": True,
    "restoration_requires_pinned_receipt_replay": True,
    "explicit_annotation_verdict": "NO_SEMANTIC_ASSERTION",
    "unresolved_JPL_author_intent": "UNKNOWN_CONTRACT",
    "unchanged_core": "research/cross_domain_correspondence_v1/protocol.py",
    "promotion_boundary": "WARRANTED_BOUNDED_EXPLICIT_TYPED_V6_POSITIVE_TO_EXISTING_V1_CORE",
}
(root / "cross-domain-v1-extension.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print("PKC_V6_UNCHANGED_CROSS_DOMAIN_CORE_MATRIX_PASS")
print(json.dumps(verdicts, indent=2, sort_keys=True))
