"""Recheck exact Nyx #613 source, tests and native logs before graph admission.

The GitHub receipt's status is not evidence. This adapter trusts only pinned
bytes, expected native outcomes and the previously qualified graph interface.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from io import BytesIO
import json
import zipfile

from mathgraph_check.boundary_warrant import (
    BoundaryWarrant, Conclusion, Dependency, Obligation, Relation, Subject,
    Verification, required_dependencies, scope_identity,
)
from mathgraph_check.warrant_resolution import Receipt
from nyx_replay import TEST_MARKER, LATITUDE_ANCHOR, classify_native_test, transplant_exact_regression

RUN_ID = 41653162686
ARTIFACT_ID = 13237614768
ARTIFACT_SHA256 = "92d8a37b6ebf8f344ccd7cebacb56306704dd6d54c2e9bfb02af4e81a531912c"
BASE_SHA = "d1c3598d5ccf4c984a1d3dd82c450e2af363e821"
HEAD_SHA = "ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b"
TEST_TRANSPLANT_SHA = "a53dcec895f666139993ce839c102af7b59680b02bd5915501b85ff88dcb5872"
LOCK_SHA = "cc2eb3c7c3e046df6b9e6c352ce2d41d17a48ff82f301c0eaec43a37ab595949"
POLICY_SHA = "5492b13551b0670fcbc3b0def11d3ac4b1d514d8339130d30b8d208248137120"
RUSTC = "rustc 1.99.1 (58cf8f9c3 2026-10-13)"

SOURCES = {
    "base_event": ("6d07cd717e120f188923d931943fb233f968afe5",
                   "92d9f32461bd8704cedc6440c8d550a88ec46164fce28b3a1a8bea3da90f3676"),
    "head_event": ("fb46c8eb2152124d9e814012e8748cb98ff0f6ae",
                   "1b8bb83166e8e398f5ee382fb907e02ae10af9270b2e9dde7ae30210bbb5f495"),
    "base_test": ("fa3ad8e8bd7dc4a24538061dbc035cdd6fdd0c7f",
                  "a5e56d83ec0df73c9980b712009994766f33a317c749f70de77c43e3d8cc1cf4"),
    "head_test": ("830919f246536ccc65be4041e9a4b775220f57bb",
                  "3b5948cc98681a75802437bf9224bb09485b825b912c86bf126ea64b0c497426"),
}
FIXTURES = {
    "pck08.pca": (33236, "ddd79e64419e7d3925ea85ab26853060e4f397477a1a6538b1d38190ca3d4468"),
    "earth_longterm_000101_251211_250915.bpc":
        (4941824, "39d1f9907cbfdf989b8f8d39802fe355ad30fa93d00381f29fe847715fb83340"),
    "earth_latest_high_prec.bpc":
        (4388864, "f03347c0b3ccba47e6e8a53c77a0381d695973fa9af8f409c282d111fc1ceb22"),
    "de440s.bsp": (32726016, "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"),
}


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def export_nyx_boundary(
    artifact: bytes, *, base_event: bytes, head_event: bytes,
    base_test: bytes, head_test: bytes,
) -> tuple[BoundaryWarrant, Receipt, dict]:
    """Admit exactly one frame-sensitive Rust regression, never a global guarantee."""
    if sha256(artifact).hexdigest() != ARTIFACT_SHA256:
        raise ValueError("ARTIFACT_IDENTITY_MISMATCH")
    sources = dict(base_event=base_event, head_event=head_event,
                   base_test=base_test, head_test=head_test)
    if any(_git_blob(raw) != SOURCES[key][0] or sha256(raw).hexdigest() != SOURCES[key][1]
           for key, raw in sources.items()):
        raise ValueError("SOURCE_IDENTITY_MISMATCH")

    base_text, head_text = base_test.decode(), head_test.decode()
    transplant = transplant_exact_regression(base_text, head_text)
    if sha256(transplant.encode()).hexdigest() != TEST_TRANSPLANT_SHA:
        raise ValueError("TRANSPLANT_IDENTITY_MISMATCH")
    test_start = head_text.index(TEST_MARKER)
    test_end = head_text.index(LATITUDE_ANCHOR, test_start)
    obligation_bytes = head_text[test_start:test_end].encode()

    with zipfile.ZipFile(BytesIO(artifact)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("UNSAFE_ARTIFACT")

        def read(name: str) -> bytes:
            try:
                return archive.read(name)
            except KeyError as exc:
                raise ValueError("INCOMPLETE_ARTIFACT:" + name) from exc

        native = json.loads(read("native-receipt.json"))
        if (native.get("run_id") != str(RUN_ID)
                or native.get("source_base") != BASE_SHA
                or native.get("source_head") != HEAD_SHA
                or native.get("test_only_transplant_sha256") != TEST_TRANSPLANT_SHA
                or native.get("status") != "CANDIDATE_BOUNDED_NATIVE"
                or native.get("authority") != "PR_TEST_DECLARED_NOT_EXTERNAL"):
            raise ValueError("UNQUALIFIED_NATIVE_RECEIPT")

        observed_fixtures = read("lfs-fixture-hashes.txt").decode().splitlines()
        expected_fixtures = [
            f"{arm} {name} {size} sha256:{digest}"
            for arm in ("nyx-base", "nyx-head")
            for name, (size, digest) in FIXTURES.items()
        ]
        if observed_fixtures != expected_fixtures:
            raise ValueError("FIXTURE_IDENTITY_MISMATCH")
        if (read("rustc.txt").decode().strip() != RUSTC or
                read("cargo-lock-hashes.txt").decode().splitlines() != [
                    f"{LOCK_SHA}  nyx-base/Cargo.lock",
                    f"{LOCK_SHA}  nyx-head/Cargo.lock",
                ]):
            raise ValueError("TOOLCHAIN_OR_DEPENDENCY_MISMATCH")

        outcomes = {}
        for arm, expected_exit in (("base", 101), ("head", 0)):
            exit_code = int(read(f"{arm}.exit").decode().strip())
            if exit_code != expected_exit:
                raise ValueError("UNEXPECTED_NATIVE_EXIT:" + arm)
            parsed = classify_native_test(
                read(f"{arm}.stdout").decode(), read(f"{arm}.stderr").decode(),
                exit_code, arm, expected_target=f"target-nyx-{arm}",
            )
            if native.get(arm) != parsed:
                raise ValueError("NATIVE_LOG_RECEIPT_MISMATCH")
            outcomes[arm] = parsed

    subject = Subject("metalogiclabs/nyx", HEAD_SHA, SOURCES["head_event"][1])
    obligation = Obligation(
        "event-frame-refinement",
        "At the Earth-fixed longitude crossing, absolute IAU_EARTH_FRAME residual < 1e-3 "
        "degrees and inertial residual > 1 degree",
        "PR_TEST_DECLARED; NOT_CUSTOMER_APPROVED", sha256(obligation_bytes).hexdigest(),
    )
    relation = Relation(
        "event_consistency",
        "Bracketing and Brent refinement evaluate the same physical event in the "
        "requested IAU_EARTH_FRAME, returning the state in the propagation frame",
        (("base_revision", BASE_SHA), ("base_event_blob", SOURCES["base_event"][0]),
         ("head_event_blob", SOURCES["head_event"][0]),
         ("transplanted_test", TEST_TRANSPLANT_SHA),
         ("test_cases", "1"), ("frame", "IAU_EARTH_FRAME")),
    )
    verification = Verification(
        "native", RUSTC, POLICY_SHA, (
            "2025-01-01 test orbit and the four exact planetary fixtures",
            "One numerical regression; source-author requirement, not external safety acceptance",
        ), "nyx:run:" + str(RUN_ID) + ":artifact:" + str(ARTIFACT_ID),
    )
    warrant = BoundaryWarrant(
        subject, obligation, relation, verification,
        Conclusion("SUPPORTED", (
            "One event-frame regression; baseline EventNotFound, head passes both frame assertions",
            "Exact historical fork base/head and pinned fixtures, Rust, Cargo and policy",
            "No independent customer obligation authority, other trajectories, or live upstream qualification",
        )),
        required_dependencies(subject, obligation, relation, verification) + (
            Dependency("evidence", "nyx:run-artifact", ARTIFACT_SHA256),
            Dependency("evidence", "nyx:cargo-lock", LOCK_SHA),
            *(Dependency("evidence", "nyx:fixture:" + name, digest)
              for name, (_, digest) in FIXTURES.items()),
        ),
    )
    assessment = {
        "base_failures": outcomes["base"]["failed"],
        "head_failures": outcomes["head"]["failed"],
        "authority": "PR_TEST_DECLARED",
        "independent_owner_authority": "UNKNOWN",
        "run_id": RUN_ID, "artifact_id": ARTIFACT_ID,
        "replay": "RECHECKED_EXACT_NATIVE_ARTIFACT",
    }
    return (warrant, Receipt(verification.receipt_id, "native", scope_identity(warrant)),
            assessment)
