"""Fail-closed exact-result audit using MathGraph's existing warrant resolver.

No claim of universal Aeneas translation correctness or independent kernel
soundness; native output is observational, Lean theorem is bounded to the
generated definition, and the source-to-model relation is tested only at one
closed input. Known-mismatched source fidelity receives no support route.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import sys

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, compare_snapshots, resolve_graph

ev = pathlib.Path(sys.argv[1]).resolve()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return (ev / path).read_text()
output = read("native_output.txt")
def extract(key):
    match = re.search(r"(?m)^" + re.escape(key) + r"=(-?\d+)\s*$", output)
    if not match:
        raise RuntimeError(f"NATIVE_OUTPUT_MISSING_{key}")
    return int(match.group(1))
native_drop, native_control = extract("NATIVE_DROP"), extract("NATIVE_CONTROL")
if (native_drop, native_control) != (7, 0):
    raise RuntimeError(f"NATIVE_ORACLE_MISMATCH_{native_drop}_{native_control}")
for role in ("drop", "control"):
    expected = f"MATHGRAPH_{role.upper()}_LEAN_THEOREM_PASSED"
    if expected not in read(f"lean_{role}_check.txt"):
        raise RuntimeError(f"NO_KERNEL_CHECK_RECEIPT_{role}")
    if "sorryAx" in read(f"lean_{role}_check.txt"):\n        raise RuntimeError("LEAN_SORRY_AXIOM_IN_PROOF")\n    if "sorry" in (ev / "verified" / ("DropVerified.lean" if role == "drop" else "ControlVerified.lean")).read_text():
        raise RuntimeError("SORRY_IN_CHECKED_FILE")
if native_drop == 0:
    raise RuntimeError("NEGATIVE_CASE_STOPPED_BEING_NEGATIVE")
if native_control != 0:
    raise RuntimeError("POSITIVE_CASE_STOPPED_MATCHING")
scope = "documentary:one-execution-source-bound-pinned-aeneas-v1"
names = (
    "rust.drop.7",
    "rust.control.0",
    "lean.drop.0",
    "lean.control.0",
    "observed.drop.mismatch",
    "observed.control.match",
    "rust_to_lean.drop_semantic_equivalence",
    "unrelated.native.control",
)
claims = [Claim(x, "documentary", scope) for x in names]
receipts = [Receipt(r, "documentary", scope) for r in (
    "native_drop", "native_control", "lean_drop", "lean_control",
    "checked_diff_drop", "checked_diff_control",
)]
routes = [
    Route("rust.drop.7", ("native_drop",)),
    Route("rust.control.0", ("native_control",)),
    Route("lean.drop.0", ("lean_drop",)),
    Route("lean.control.0", ("lean_control",)),
    Route("observed.drop.mismatch", ("checked_diff_drop",), ("rust.drop.7", "lean.drop.0")),
    Route("observed.control.match", ("checked_diff_control",), ("rust.control.0", "lean.control.0")),
    Route("unrelated.native.control", ("native_control",)),
]
# No route can qualify source-to-Lean Drop semantic equivalence:
# original and translation differ; the bounded equality proposition is REFUTED by observation.
base = dict(resolve_graph(claims, routes, receipts).states)
assert base["rust_to_lean.drop_semantic_equivalence"] == "UNKNOWN"
assert base["observed.drop.mismatch"] == "SOURCE_DOCUMENTED"
assert base["observed.control.match"] == "SOURCE_DOCUMENTED"
cases = {
    "withdraw_control_comparator": ("checked_diff_control", {"observed.control.match"}),
    "withdraw_native_drop": ("native_drop", {"rust.drop.7", "observed.drop.mismatch"}),
    "withdraw_lean_drop": ("lean_drop", {"lean.drop.0", "observed.drop.mismatch"}),
    "withdraw_lean_control": ("lean_control", {"lean.control.0", "observed.control.match"}),
}
comparison = {}
for label, (receipt, expected_lost) in cases.items():
    after = dict(resolve_graph(claims, routes, receipts, withdrawn=frozenset((receipt,))).states)
    lost = {k for k in base if base[k] != "UNKNOWN" and after[k] == "UNKNOWN"}
    if lost != expected_lost:
        raise RuntimeError(f"SELECTIVE_WITHDRAWAL_ERROR_{label}:{sorted(lost)}")
    if after["rust_to_lean.drop_semantic_equivalence"] != "UNKNOWN":
        raise RuntimeError("FALSE_SEMANTIC_PROMOTION")
    # Restoration must be exactly reversible.
    restored = dict(resolve_graph(claims, routes, receipts).states)
    if restored != base:
        raise RuntimeError("RESTORATION_NOT_IDEMPOTENT")
    comparison[label] = {
        "withdrew": receipt,
        "lost_only": sorted(lost),
        "before_after": compare_snapshots(base, after),
        "restores_exactly": True,
    }
source = pathlib.Path(__file__).with_name("one_guard.rs")
generated = {
    role: [{"path": str(f.relative_to(ev)), "sha256": digest(f)}
           for f in sorted((ev / ("generated_" + role)).rglob("*.lean"))]
    for role in ("drop", "control")
}
report = {
    "schema": "mathgraph.aeneas-drop-correspondence.v1",
    "status": "WARRANTED_BOUNDED_NATIVE_AND_GENERATED_LEAN_OBSERVATION",
    "translation_equivalence_status": "REJECTED_BOUNDED_FOR_ONE_CLOSED_CASE",
    "prospective_new_method_status": "UNKNOWN_NOT_TESTED",
    "source": {
        "aeneas_release": "nightly-2026.10.12-d119a47",
        "aeneas_source_revision": "d119a474f852781f8ae88a85424f2f8ba8407b82",
        "charon_revision": "798016509139eb51f0d764645f76d068d34ba5f6",
        "rust_toolchain": "nightly-2026-09-17",
        "lean_toolchain": "v4.31.0",
        "rust_reproducer_sha256": digest(source),
        "release_asset_sha256_line": read("release_sha256.txt").strip(),
        "lean_release_asset_sha256_line": read("lean_release_sha256.txt").strip(),
    },
    "observations": {
        "rust_fn0": native_drop,
        "lean_fn0": 0,
        "rust_control": native_control,
        "lean_control": 0,
        "generated": generated,
        "lean_drop_theorem_output_sha256": digest(ev / "lean_drop_check.txt"),
        "lean_control_theorem_output_sha256": digest(ev / "lean_control_check.txt"),
    },
    "closure": {"baseline": base, "withdrawals": comparison},
    "boundaries": [
        "Rust return value obtained from native execution, not a Rust proof",
        "Lean result obtained from checked generated function theorem, not Rust source correctness",
        "Differential evidence is one closed case, not general translation verification",
        "MathGraph resolver validates declared consequences, NOT externally admitted evidence authenticity",
        "The false source-to-Lean Drop equivalence is never admitted, before or after withdrawal",
    ],
}
(ev / "RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    "status": report["status"],
    "rust_drop": native_drop,
    "lean_drop": 0,
    "native_control": native_control,
    "lean_control": 0,
    "semantic_equivalence": report["translation_equivalence_status"],
    "withdrawals_lost": {k: v["lost_only"] for k, v in comparison.items()},
}, indent=2))
