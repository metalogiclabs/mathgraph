"""Conservative, source-scoped warrant maintenance.

A public source notice establishes that a publisher made a statement,
not that a mathematical theorem is false. Formal and documentary evidence
never cross their type boundary without a separately verified adapter.

This is bounded reference machinery, not a soundness theorem or a trust root.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from html import escape
import json
from pathlib import Path
from typing import Mapping, Sequence

OPENAI_REPO = "openai/math"
OPENAI_HEAD = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
OPENAI_HISTORY_BLOB = "693874f398905b1bc59e01b898b223ae9956bfc2"
OPENAI_HISTORY_URL = (
    "https://github.com/openai/math/blob/" + OPENAI_HEAD + "/history.md"
)
WITHDRAWN_TITLES = (
    "Algebraicity of Weil classes on split abelian eightfolds",
    "Algebraicity of Kuga–Satake Correspondences for K3 Surfaces",
    "The rational Hodge conjecture for products of K3 surfaces",
)
RECORD_ID = "mg-living-warrant-openai-jpl-20261010"
SCHEMA = "mathgraph.living-warrant-snapshot.v1"
JPL_CLAIM = "jpl.l4yaml.finite_parser_acceptance"
JPL_SCOPE = (
    "nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
    ":yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870"
    ":48-cases"
)
JPL_RECEIPT = "mathgraph.l4yaml.48-case-qualification"
KINDS = frozenset(("formal", "documentary"))


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def read_withdrawals(raw: bytes) -> tuple[str, ...]:
    """Source-pin and parse only the exact public October-7 notice."""
    if git_blob_sha1(raw) != OPENAI_HISTORY_BLOB:
        raise ValueError("OPENAI_HISTORY_GIT_BLOB_MISMATCH")
    text = raw.decode("utf-8")
    if text.count("## October 7, 2026") != 1:
        raise ValueError("WITHDRAWAL_HEADING_NOT_UNIQUE")
    section = text.split("## October 7, 2026", 1)[1].split("\n## ", 1)[0]
    if ("sign error invalidates a stabilization-trace cancellation argument" not in section
            or "withdrawn" not in section.lower()
            or "**Withdrawals**" not in section):
        raise ValueError("NO_QUALIFIED_WITHDRAWAL_REASON")
    part = section.split("**Withdrawals**", 1)[1].split("**Fixes**", 1)[0]
    bullets = tuple(
        line.strip()[2:].strip()
        for line in part.splitlines()
        if line.strip().startswith("- ")
    )
    if bullets != WITHDRAWN_TITLES:
        raise ValueError("WITHDRAWAL_TITLES_CHANGED")
    return bullets


@dataclass(frozen=True)
class Claim:
    id: str
    kind: str
    scope: str

    def __post_init__(self):
        if not self.id or self.kind not in KINDS or not self.scope:
            raise ValueError("INVALID_CLAIM_TYPE")


@dataclass(frozen=True)
class Receipt:
    """Pre-qualified externally bound evidence, NOT an untrusted self-label.

    Real imports must independently validate source/replay before constructing
    these values. These value objects are not signature or receipt verifiers.
    """
    id: str
    kind: str
    scope: str

    def __post_init__(self):
        if not self.id or self.kind not in KINDS or not self.scope:
            raise ValueError("INVALID_RECEIPT_TYPE")


@dataclass(frozen=True)
class Route:
    conclusion: str
    evidence: tuple[str, ...]
    premises: tuple[str, ...] = ()


def reclose(
    claims: Sequence[Claim],
    routes: Sequence[Route],
    receipts: Sequence[Receipt],
    *,
    withdrawn: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Small, monotone, source/logic-typed AND/OR consequence resolver.

    All routes require conjunctive premises and evidence; independent routes
    are alternatives. Cycles with no qualified base remain UNKNOWN. No
    source/documentary route can establish a formal theorem.
    """
    cl = {c.id: c for c in claims}
    ev = {r.id: r for r in receipts}
    if len(cl) != len(claims) or len(ev) != len(receipts):
        raise ValueError("DUPLICATE_CLAIM_OR_RECEIPT")
    if not withdrawn.issubset(ev.keys()):
        raise ValueError("UNKNOWN_WITHDRAWAL_TARGET")
    if len(set(routes)) != len(routes):
        raise ValueError("DUPLICATE_ROUTE")
    for route in routes:
        if route.conclusion not in cl or not route.evidence:
            raise ValueError("INVALID_ROUTE")
        if any(x not in ev for x in route.evidence):
            raise ValueError("UNKNOWN_ROUTE_RECEIPT")
        if any(x not in cl for x in route.premises):
            raise ValueError("UNKNOWN_ROUTE_PREMISE")
        dest = cl[route.conclusion]
        if any(ev[x].kind != dest.kind or ev[x].scope != dest.scope
               for x in route.evidence):
            raise ValueError("CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE")
        if any(cl[x].kind != dest.kind or cl[x].scope != dest.scope
               for x in route.premises):
            raise ValueError("CROSS_BOUNDARY_PREMISE_WITHOUT_BRIDGE")

    active = set()
    for _ in range(len(cl) + 1):
        changed = False
        for route in routes:
            if (all(e not in withdrawn for e in route.evidence)
                    and all(p in active for p in route.premises)
                    and route.conclusion not in active):
                active.add(route.conclusion)
                changed = True
        if not changed:
            break
    return {
        key: ("WARRANTED_BOUNDED" if cl[key].kind == "formal"
              else "SOURCE_DOCUMENTED") if key in active else "UNKNOWN"
        for key in sorted(cl)
    }


def compare_snapshots(
    before: Mapping[str, str], after: Mapping[str, str]
) -> dict[str, dict]:
    if before.keys() != after.keys():
        raise ValueError("DIFFERENT_CLAIM_UNIVERSE")
    result = {}
    for claim in sorted(before):
        old, new = before[claim], after[claim]
        if old != "UNKNOWN" and new == "UNKNOWN":
            status = "STALE"
        else:
            status = new
        result[claim] = {"before": old, "after": status,
                         "changed": old != status}
    return result


def build_snapshot(history: bytes, jpl_record: dict) -> dict:
    """Read only immutable upstream source and previously qualified JPL receipt."""
    titles = read_withdrawals(history)
    from .public_receipts import (
        _release_integrity, resolve as resolve_jpl,
        RECORD_ID as JPL_RECORD_ID, JPL_COMMIT, SUITE_COMMIT
    )
    _release_integrity(jpl_record)
    jpl_result = resolve_jpl(jpl_record, {
        "record_id": JPL_RECORD_ID,
        "source_commit": JPL_COMMIT,
        "external_suite_commit": SUITE_COMMIT,
        "goal": "finite_parser_acceptance",
    })
    if jpl_result.get("status") != "WARRANTED_BOUNDED":
        raise ValueError("JPL_VERIFIER_RECEIPT_NOT_QUALIFIED")

    claims = []
    receipts = []
    routes = []
    withdrawn = set()
    mapping = []
    for n, title in enumerate(titles):
        id_ = "openai.original_support.%d" % (n + 1)
        rid = "openai.original_publication_receipt.%d" % (n + 1)
        scope = "openai/math:" + title + ":original-withdrawn-edition"
        claims.append(Claim(id_, "documentary", scope))
        receipts.append(Receipt(rid, "documentary", scope))
        routes.append(Route(id_, (rid,)))
        withdrawn.add(rid)
        claims.append(Claim("openai.theorem.%d" % (n + 1), "formal", scope))
        mapping.append({"name": title, "original_support_claim": id_,
                        "mathematical_truth": "UNKNOWN",
                        "editorial_status": "WITHDRAWN_BY_PUBLISHER"})
    claims.append(Claim(JPL_CLAIM, "formal", JPL_SCOPE))
    receipts.append(Receipt(JPL_RECEIPT, "formal", JPL_SCOPE))
    routes.append(Route(JPL_CLAIM, (JPL_RECEIPT,)))

    previous = reclose(claims, routes, receipts)
    current = reclose(claims, routes, receipts, withdrawn=frozenset(withdrawn))
    states = compare_snapshots(previous, current)
    # These "before" routes are explicitly illustrative: historical proof
    # soundness was NOT independently established.
    assert all(states[x["original_support_claim"]]["after"] == "STALE"
               for x in mapping)
    assert all(states["openai.theorem.%d" % (n + 1)]["after"] == "UNKNOWN"
               for n in range(3))
    assert states[JPL_CLAIM]["after"] == "WARRANTED_BOUNDED"
    publication = {
        "derivation": {
            "claims": [asdict(x) for x in claims],
            "receipts": [asdict(x) for x in receipts],
            "routes": [asdict(x) for x in routes],
            "withdrawn_evidence": sorted(withdrawn),
            "receipt_admission": {
                "documentary": "exact pinned OpenAI history notice",
                "formal": "exact pinned JPL finite parser receipt",
            },
        },
        "schema": SCHEMA,
        "id": RECORD_ID,
        "sources": {
            "openai": {
                "commit": OPENAI_HEAD,
                "path": "history.md",
                "git_blob_sha1": OPENAI_HISTORY_BLOB,
                "byte_sha256": hashlib.sha256(history).hexdigest(),
                "url": OPENAI_HISTORY_URL,
                "notice_date": "2026-10-07",
            },
            "jpl_record_id": JPL_RECORD_ID,
            "jpl_record_sha256": jpl_record["content_sha256"],
        },
        "publisher_notice": {
            "kind": "PUBLICATION_WITHDRAWAL",
            "documents": mapping,
            "cause_as_reported": "sign_error_in_original_argument",
            "does_not_imply": "mathematical_theorem_refuted",
        },
        "resolutions": states,
        "interpretation": {
            "simulated_before": "Documentary original-support routes were modeled as active before publisher withdrawal; this does not prove their correctness.",
            "after": "The publisher withdrew three original arguments. Their prior documentary support paths are stale; mathematical truth remains UNKNOWN.",
            "unaffected": "An independently qualified JPL 48-case record survives without new verification or false promotion.",
            "source_contract": "Publication history is a source notice, not a formal theorem verifier.",
            "runtime_status": "IMMUTABLE_HISTORICAL_SNAPSHOT_NOT_CONTINUOUSLY_MONITORED",
        },
    }
    publication["snapshot_sha256"] = hashlib.sha256(canonical(publication)).hexdigest()
    return publication


def verify_snapshot(snapshot: dict) -> bool:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise ValueError("UNKNOWN_SNAPSHOT_SCHEMA")
    hash_ = snapshot.get("snapshot_sha256")
    if not isinstance(hash_, str):
        raise ValueError("MISSING_SNAPSHOT_HASH")
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if hashlib.sha256(canonical(body)).hexdigest() != hash_:
        raise ValueError("SNAPSHOT_CORRUPTED")
    # Self-hashing is NOT provenance authentication. Requiring an externally
    # pinned expected digest belongs to the consumer/release boundary.
    return True


def render_html(snapshot: dict) -> str:
    verify_snapshot(snapshot)
    source = snapshot["sources"]["openai"]
    names = snapshot["publisher_notice"]["documents"]
    rows = "\n".join(
        "<tr><td>" + escape(item["name"]) +
        "</td><td>Withdrawn original support</td><td>UNKNOWN</td></tr>"
        for item in names
    )
    jpl = snapshot["resolutions"][JPL_CLAIM]
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MathGraph Check · Living warrants experiment</title>
<style>
:root{color-scheme:light;font-family:Inter,system-ui,-apple-system,sans-serif}
body{margin:0;background:#f6f7f9;color:#17212b}
main{max-width:950px;margin:0 auto;padding:56px 24px}
header{border-bottom:1px solid #d6dce2;padding-bottom:24px}
h1{font-size:clamp(30px,5vw,48px);letter-spacing:-.045em;line-height:1.13}
h2{margin-top:38px;font-size:21px}
p{line-height:1.7;color:#354556}
small{color:#56687b}
table{border-collapse:collapse;width:100%;background:white;border:1px solid #dbe1e8}
th,td{padding:16px 12px;text-align:left;border-bottom:1px solid #e6ebf0}
th{font-size:12px;color:#526273;text-transform:uppercase;letter-spacing:.065em}
td{font-size:14px}
a{color:#155d9f}code{font-size:12px;overflow-wrap:anywhere}
.notice{border-left:3px solid #526273;padding:10px 16px;background:#eceff2}
footer{border-top:1px solid #d6dce2;margin-top:42px;padding-top:24px}
@media(max-width:560px){main{padding:28px 14px}th,td{padding:10px 6px;font-size:12px}}
</style></head><body><main><header><small>MathGraph Check / Bounded evidence experiment</small>
<h1>Evidence changes. Truth is not silently rewritten.</h1>
<p>Three OpenAI mathematics manuscripts were withdrawn on 7 October 2026 after
a reported sign error. This source-pinned audit withdraws their recorded
original justification routes, without claiming the mathematical theorems
have been disproved.</p></header>
<h2>Publisher-reported changes</h2><table>
<thead><tr><th>Manuscript</th><th>Recorded support</th><th>Theorem truth</th></tr></thead>
<tbody>""" + rows + """</tbody></table>
<h2>Independent unaffected control</h2>
<p>NASA/JPL L4YAML, exact frozen 48-case parser acceptance:
<strong>""" + escape(jpl["after"]) + """</strong>. The OpenAI publisher notice
does not change this independent evidence path.</p>
<h2>Verification boundary</h2>
<div class="notice"><p>This is NOT proof of or against the underlying OpenAI
mathematical statements. The pre-withdrawal documentary route is an
illustrative historical state, not a claimed formally sound proof.
The evidence graph is a frozen demonstration, not live monitoring.</p></div>
<p>Exact publisher history: <a href=\"""" + escape(source["url"], quote=True) + """\">source at pinned commit</a>.
Original history SHA-256: <code>""" + escape(source["byte_sha256"]) + """</code>.</p>
<p><a href="living.json">Machine-readable snapshot</a>.
<a href="record.json">JPL finite-case record</a>.
<a href="index.html">JPL evidence inspection</a>.</p>
<footer><small>MathGraph · Metalogic Labs · Source-based findings only.
Original authors and institutions are not represented as endorsers.</small></footer>
</main></body></html>"""


def write_snapshot(history_path: Path, jpl_record_path: Path, out: Path) -> dict:
    raw = history_path.read_bytes()
    record = json.loads(jpl_record_path.read_text(encoding="utf-8"))
    snap = build_snapshot(raw, record)
    verify_snapshot(snap)
    out.mkdir(parents=True, exist_ok=True)
    (out / "living.json").write_bytes(canonical(snap) + b"\n")
    (out / "living.html").write_text(render_html(snap), encoding="utf-8")
    return snap
