"""Read-only source-frozen rocket correspondence profile for MathGraph Check.

The supplied private ZIP is NEVER committed or executed. This module can check
a source archive's exact identity, correspondence of its small source inputs,
and an independent finite Boolean oracle. It cannot authenticate unsigned
native receipts, recover human intent or authorize a specification repair.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

SCHEMA = "mathgraph.check.rocket-correspondence.v1"
BUNDLE_DIGEST = "fc055bc03c34fd8b7ca90242b71a400d30e4376e4c2e262d744a7aaa8d5b9d1f"
FRET_SHA = "cf0f913cc15c41705e803593297e89cd6056b839"
R2U2_SHA = "2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a"
FRETISH = "whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST"
SOURCE_FORMULA = "(BOOST -> (F[0,7] COAST))"
ALTERNATIVE_FORMULA = "(BOOST -> (F[1,7] COAST))"
PREFIX = "pilot_fret_r2u2/"
SPEC_DIGESTS = {
    "rocket_fretish": "61cdfdb56da7463f3fb220381649c011efb6d0a5177a841255540186f2b3ea15",
    "rocket_delayed": "cc16408a46782573397b8d6f06857fb011651adac90d1c8a9379213c9aef7100",
}
MAP_DIGEST = "dc8649dfeefbccd35f1df8afbf25f8e14b10cc0ff97551b8b6aa79724f79ea2f"
SCENARIOS = ("rocket_simultaneous", "rocket_next_tick", "rocket_no_coast", "rocket_no_boost")
CSV_DIGESTS = {
    "rocket_simultaneous": "e14aa588b62919ceb4b175f521f6de5ac6a459ebc3600d9e7d8df4e77d1eaaf4",
    "rocket_next_tick": "83e74ab2106ab85aca5c4b955205a712e6212218c9e6b47497a9bff2073662ba",
    "rocket_no_coast": "b3016ef1ad92739ec428d7a35290e49f29c5ac8338bd1ffca2a43d810fda6708",
    "rocket_no_boost": "55bc33a80c012ccdab995941ac17c232ca232eadd513f9587253aed1382e8950",
}
MAX_ZIP_BYTES = 1_000_000
MAX_MEMBER_BYTES = 128_000


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _no_duplicate_keys(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("DUPLICATE_JSON_KEY")
        output[key] = value
    return output


def _json(value: bytes):
    return json.loads(
        value.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON"))
    )


def read_admitted_archive(zip_bytes: bytes, expected_archive_sha256: str = BUNDLE_DIGEST):
    """Read whitelisted input members; never unzip to disk or execute ZIP code."""
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ValueError("ARCHIVE_TOO_LARGE")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_archive_sha256):
        raise ValueError("INVALID_EXPECTED_ARCHIVE_IDENTITY")
    if digest(zip_bytes) != expected_archive_sha256:
        raise ValueError("ARCHIVE_IDENTITY_CHANGED")
    needed = {"rocket_formalization.json"}
    for variant in SPEC_DIGESTS:
        needed.update((variant + ".c2po", variant + ".map", variant + "_receipt.json"))
    for scenario in SCENARIOS:
        needed.update((scenario + ".csv", scenario + ".json"))
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            entries = z.infolist()
            names = [entry.filename for entry in entries]
            if len(set(names)) != len(names) or any(
                not name.startswith(PREFIX) or ".." in name.split("/") or "\\" in name
                for name in names
            ):
                raise ValueError("UNSAFE_ARCHIVE_MEMBERS")
            requested = {PREFIX + name for name in needed}
            if not requested <= set(names):
                raise ValueError("MISSING_SOURCE_MEMBER")
            if any(entry.file_size > MAX_MEMBER_BYTES for entry in entries
                   if entry.filename in requested):
                raise ValueError("OVERSIZE_ARCHIVE_MEMBER")
            return {name: z.read(PREFIX + name) for name in needed}
    except zipfile.BadZipFile as exc:
        raise ValueError("INVALID_ARCHIVE") from exc


def oracle_at(trace, current, lower):
    """Declared complete eight-tick semantics, not unrestricted MLTL."""
    return not trace[current]["BOOST"] or any(
        trace[t]["COAST"] for t in range(current + lower, min(8, current + 8))
    )


def minimal_two_event_witness():
    minimum, witnesses = 17, []
    # All 2**16 complete two-signal/eight-tick Boolean traces.
    for mask in range(1 << 16):
        if not (mask & 1):
            continue
        if (mask & (1 << 8)) and not (mask & (((1 << 8) - 1) << 9)):
            weight = mask.bit_count()
            if weight < minimum:
                minimum, witnesses = weight, [mask]
            elif weight == minimum:
                witnesses.append(mask)
    if (minimum, witnesses) != (2, [257]):
        raise ValueError("FINITE_MINIMAL_WITNESS_FAILED")
    return {"total_traces": 65536, "minimum_true_event_count": 2,
            "unique_minimum_mask": 257}


def _case(assets, scenario):
    raw = assets[scenario + ".csv"]
    if digest(raw) != CSV_DIGESTS[scenario]:
        raise ValueError("TRACE_SOURCE_CHANGED:" + scenario)
    trace = _json(assets[scenario + ".json"])
    if not isinstance(trace, list) or len(trace) != 8 or any(
        type(row) is not dict or set(row) != {"BOOST", "COAST"} or
        any(type(row[key]) is not int or row[key] not in (0, 1)
            for key in ("BOOST", "COAST"))
        for row in trace
    ):
        raise ValueError("TRACE_DOMAIN_INVALID:" + scenario)
    expected = ["# BOOST, COAST"] + [
        f'{row["BOOST"]},{row["COAST"]}' for row in trace
    ]
    if raw.decode("utf-8").splitlines() != expected:
        raise ValueError("TRACE_CSV_IDENTITY_MISMATCH:" + scenario)
    return trace


def assess_archive(zip_bytes: bytes, expected_archive_sha256: str = BUNDLE_DIGEST):
    """A positive finite oracle is not an operational-intent or native warrant."""
    result = {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "permission": "ADVISORY_ONLY",
        "subject": {
            "archive_sha256": digest(zip_bytes),
            "fret_commit": FRET_SHA,
            "r2u2_commit": R2U2_SHA,
            "signals": ["BOOST", "COAST"],
            "domain": "8 complete ticks, Boolean signals; [0,7] versus [1,7]"
        },
        "source_artifact_admission": "UNKNOWN",
        "semantic_distinction": "UNKNOWN",
        "native_monitor_correspondence": "UNKNOWN",
        "fretish_export_correspondence": "UNKNOWN",
        "repair_authority": "UNKNOWN",
        "repair_eligible": False,
        "automatic_repair": "DENIED",
        "authority_basis": "AUTHENTICATED_OPERATIONAL_OWNER_DECISION_ABSENT",
        "semantic_scope": "Eight complete ticks only; no unrestricted MLTL theorem",
        "decisive_owner_question": "Does simultaneous COAST at the BOOST instant satisfy this operational requirement?"
    }
    try:
        files = read_admitted_archive(zip_bytes, expected_archive_sha256)
        doc = _json(files["rocket_formalization.json"])
        if (doc.get("fretish") != FRETISH or
            doc.get("r2u2_code") != SOURCE_FORMULA or
            doc.get("delayed_candidate_stream_adaptation") != ALTERNATIVE_FORMULA or
            doc.get("reference_status") != "published example; no independent owner-intent decision"):
            raise ValueError("FORMALIZATION_DECLARATION_MISMATCH")
        for variant, formula in (
            ("rocket_fretish", SOURCE_FORMULA),
            ("rocket_delayed", ALTERNATIVE_FORMULA)
        ):
            spec, mapping = files[variant + ".c2po"], files[variant + ".map"]
            receipt = _json(files[variant + "_receipt.json"])
            if (digest(spec) != SPEC_DIGESTS[variant] or
                digest(mapping) != MAP_DIGEST or
                mapping != b"BOOST:0\r\nCOAST:1\r\n" or
                spec.decode("utf-8").count("ROCKET_RESPONSE: " + formula) != 1):
                raise ValueError("SOURCE_MAP_SPEC_MISMATCH:" + variant)
            if (receipt.get("schema") != "mathgraph-r2u2-input-binding-pilot-v1" or
                receipt.get("spec_sha256") != digest(spec) or
                receipt.get("map_sha256") != digest(mapping) or
                receipt.get("fret_commit") != FRET_SHA or
                receipt.get("r2u2_commit") != R2U2_SHA or
                receipt.get("signal_order") != ["BOOST", "COAST"] or
                not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("binary_sha256", "")))):
                raise ValueError("UNSIGNED_RECEIPT_SOURCE_MISMATCH:" + variant)
            if variant == "rocket_delayed" and "not owner-approved" not in receipt.get("role", ""):
                raise ValueError("ALTERNATIVE_NOT_LABELED_AS_CANDIDATE")
        verdicts = {}
        for scenario in SCENARIOS:
            trace = _case(files, scenario)
            verdicts[scenario.removeprefix("rocket_")] = {
                "source_0_7": [oracle_at(trace, t, 0) for t in range(8)],
                "constructed_1_7": [oracle_at(trace, t, 1) for t in range(8)]
            }
        if (verdicts["simultaneous"]["source_0_7"][0],
            verdicts["simultaneous"]["constructed_1_7"][0]) != (True, False):
            raise ValueError("MINIMAL_SEPARATOR_NOT_REPRODUCED")
        for scenario, expected in (
            ("next_tick", True), ("no_coast", False), ("no_boost", True)
        ):
            if any(verdicts[scenario][key][0] != expected for key in
                   ("source_0_7", "constructed_1_7")):
                raise ValueError("CONTROL_FAILED:" + scenario)
        minimal = minimal_two_event_witness()
    except (ValueError, KeyError, UnicodeError, OSError) as exc:
        result["reason"] = str(exc)
        return result
    result.update({
        "status": "UNKNOWN",  # Overall purpose-to-deployment claim stays UNKNOWN.
        "source_artifact_admission": "EXACT_ARCHIVE_AND_MEMBER_BYTES_MATCH",
        "semantic_distinction": "WARRANTED_BOUNDED_FINITE_ORACLE",
        "fretish_export_correspondence": "UNKNOWN_NOT_REPLAYED_BY_THIS_PROFILE",
        "native_monitor_correspondence": "UNKNOWN_BINARIES_NOT_IN_BUNDLE",
        "reason": "FINITE_SEMANTICS_CHECKED_BUT_NATIVE_AND_OWNER_AUTHORITY_UNKNOWN",
        "finite_expected_verdict_count": 64,
        "finite_minimality": minimal,
        "case_verdicts": verdicts,
        "source_pins": {
            "source_spec_sha256": SPEC_DIGESTS["rocket_fretish"],
            "alternative_spec_sha256": SPEC_DIGESTS["rocket_delayed"],
            "signal_map_sha256": MAP_DIGEST
        },
        "claimed_native_receipts_are": "UNSIGNED_UNAUTHENTICATED_BINARY_DIGESTS",
        "existing_warrant_carrier": (
            "BoundaryWarrant: Subject/Obligation/Relation/Verification/"
            "Conclusion/Dependencies; no qualified native Receipt constructed"
        )
    })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="locally held source-only ZIP")
    parser.add_argument("--out", type=Path, help="write JSON result")
    args = parser.parse_args(argv)
    result = assess_archive(args.bundle.read_bytes())
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload)
    else:
        sys.stdout.write(payload)
    return 0 if result["semantic_distinction"] == "WARRANTED_BOUNDED_FINITE_ORACLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
