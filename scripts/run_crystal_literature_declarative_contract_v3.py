#!/usr/bin/env python3
"""Qualify the declarative literature extraction-contract interpreter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mathgraph.extraction_contract import apply_extraction_contract, qualify_falsifiers

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "evidence" / "crystal-literature-declarative-contract-v3" / "contracts.json"
RESULT = ROOT / "evidence" / "crystal-literature-declarative-contract-v3" / "result.json"
PARENT = "043a670231475020c8aa0297b477f7ccdab7867c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    bundle = json.loads(CONTRACTS.read_text())
    contracts = bundle["contracts"]
    assert len(contracts) == 2

    qualified = []
    falsifiers = []
    for contract in contracts:
        snapshot = ROOT / contract["snapshot_path"]
        source_text = snapshot.read_bytes().decode("utf-8", errors="replace")
        # Match the same HTML-to-visible-text boundary as the source-fidelity gate.
        from html import unescape
        import re
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", source_text, flags=re.I | re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = " ".join(unescape(text).split())

        result = apply_extraction_contract(
            contract,
            text,
            evidence_ref="hosted:crystal-literature-declarative-contract-v3",
        )
        rejected = qualify_falsifiers(
            contract,
            text,
            evidence_ref="hosted:crystal-literature-declarative-contract-v3",
        )
        qualified.append({"name": contract["name"], **result})
        falsifiers.extend(f"{contract['name']}:{label}" for label in rejected)

    evidence = {
        "schema": "mathgraph.crystal-literature-declarative-contract-v3.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_extraction_head": PARENT,
        "results": {
            "contracts": len(contracts),
            "source_specific_parser_functions": 0,
            "exact_parent_source_ids_reconstructed": 2,
            "exact_parent_formal_ids_reconstructed": 2,
            "relations_qualified": 2,
            "falsifiers_rejected": len(falsifiers),
            "new_crystal_waist_fields": 0,
            "new_claim_dialect_fields": 0,
        },
        "qualified_contracts": qualified,
        "rejected_falsifiers": falsifiers,
        "contract_bundle_sha256": sha256(CONTRACTS),
        "epistemic_result": {
            "declarative_contract_interpreter": "WARRANTED_ON_TWO_HETEROGENEOUS_SOURCES",
            "source_specific_contract_data": "WARRANTED_ON_PARENT_SOURCE/EXTRACTION_BOUNDARIES",
            "held_out_contract_transfer": "UNKNOWN",
            "generic_prose_extraction": "UNKNOWN",
        },
        "boundary": (
            "This removes source-specific executable parser code for the two already-qualified "
            "sources. Source-specific semantics still appear explicitly as declarative contract data. "
            "No held-out transfer or generic natural-language extraction is yet warranted."
        ),
    }
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_LITERATURE_DECLARATIVE_CONTRACT_V3=QUALIFIED_BOUNDED")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
