"""TPTP/Vampire residual attack fabric.

This module exports first-order UNKNOWN residuals to TPTP FOF, runs a Vampire
binary using its documented stable command-line surface, parses SZS result
metadata, and returns candidate evidence.  ATP output never self-promotes into
Crystal authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Mapping

from mathgraph.crystal import content_id
from mathgraph.protected_future import ContinuationStatus, ProtectedContinuation


_NAME_RE = re.compile(r"[^A-Za-z0-9_]")


def _name(value: str, *, prefix: str = "f") -> str:
    out = _NAME_RE.sub("_", value.strip())
    if not out:
        out = prefix
    if not out[0].islower():
        out = prefix + "_" + out
    return out


@dataclass(frozen=True)
class FirstOrderResidual:
    problem_id: str
    axioms: tuple[tuple[str, str], ...]
    conjecture: str
    conjecture_name: str = "conjecture"
    boundary_ref: str = "logic:first-order"
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.problem_id or not self.conjecture.strip():
            raise ValueError("problem_id and conjecture must be non-empty")
        if any(not name or not formula.strip() for name, formula in self.axioms):
            raise ValueError("axiom names/formulas must be non-empty")
        object.__setattr__(self, "source_refs", tuple(sorted(set(self.source_refs))))

    @property
    def id(self) -> str:
        return content_id(self, prefix="fol-residual")

    def to_tptp(self) -> str:
        lines = [
            f"% MathGraph residual {self.id}",
            f"% boundary {self.boundary_ref}",
        ]
        for ref in self.source_refs:
            lines.append(f"% source {ref}")
        for name, formula in self.axioms:
            lines.append(f"fof({_name(name)}, axiom, ({formula})).")
        lines.append(f"fof({_name(self.conjecture_name)}, conjecture, ({self.conjecture})).")
        return "\n".join(lines) + "\n"

    @property
    def tptp_sha256(self) -> str:
        return hashlib.sha256(self.to_tptp().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mathgraph.atp.first-order-residual@1",
            "residual_id": self.id,
            "problem_id": self.problem_id,
            "axioms": [{"name": n, "formula": f} for n, f in self.axioms],
            "conjecture": self.conjecture,
            "conjecture_name": self.conjecture_name,
            "boundary_ref": self.boundary_ref,
            "source_refs": list(self.source_refs),
            "tptp_sha256": self.tptp_sha256,
        }


@dataclass(frozen=True)
class SZSOutputBlock:
    kind: str
    content: str


@dataclass(frozen=True)
class ATPCandidateEvidence:
    engine: str
    problem_id: str
    residual_id: str
    tptp_sha256: str
    szs_status: str | None
    candidate_status: str
    returncode: int | None
    elapsed_seconds: float
    command: tuple[str, ...]
    output_blocks: tuple[SZSOutputBlock, ...]
    stdout: str
    stderr: str
    requires_independent_check: bool = True

    @property
    def id(self) -> str:
        summary = {
            "engine": self.engine,
            "problem_id": self.problem_id,
            "residual_id": self.residual_id,
            "tptp_sha256": self.tptp_sha256,
            "szs_status": self.szs_status,
            "candidate_status": self.candidate_status,
            "returncode": self.returncode,
            "blocks": [(b.kind, hashlib.sha256(b.content.encode()).hexdigest()) for b in self.output_blocks],
        }
        return content_id(summary, prefix="atp-evidence")

    def to_dict(self, *, include_output: bool = True) -> dict[str, Any]:
        out = {
            "evidence_id": self.id,
            "engine": self.engine,
            "problem_id": self.problem_id,
            "residual_id": self.residual_id,
            "tptp_sha256": self.tptp_sha256,
            "szs_status": self.szs_status,
            "candidate_status": self.candidate_status,
            "returncode": self.returncode,
            "elapsed_seconds": self.elapsed_seconds,
            "command": list(self.command),
            "output_blocks": [{"kind": b.kind, "content": b.content} for b in self.output_blocks],
            "requires_independent_check": self.requires_independent_check,
        }
        if include_output:
            out["stdout"] = self.stdout
            out["stderr"] = self.stderr
        return out

    def as_unadmitted_continuation(self, source: str) -> ProtectedContinuation:
        """Represent ATP output as UNKNOWN until a declared checker admits it."""
        return ProtectedContinuation(
            source=source,
            continuation="logic.first-order.entailment@1",
            outcome=(self.candidate_status, self.szs_status or "NoSZSStatus"),
            status=ContinuationStatus.UNKNOWN,
            evidence_refs=(
                self.id,
                f"tptp-sha256:{self.tptp_sha256}",
                f"atp-engine:{self.engine}",
            ),
        )


_SZS_RE = re.compile(r"(?:%|#)?\s*SZS\s+status\s+([A-Za-z][A-Za-z0-9_]*)", re.IGNORECASE)
_START_RE = re.compile(r"(?:%|#)?\s*SZS\s+output\s+start\s+([^\s]+)", re.IGNORECASE)
_END_RE = re.compile(r"(?:%|#)?\s*SZS\s+output\s+end\s+([^\s]+)", re.IGNORECASE)


def parse_szs_status(output: str) -> str | None:
    match = _SZS_RE.search(output)
    return match.group(1) if match else None


def parse_szs_output_blocks(output: str) -> tuple[SZSOutputBlock, ...]:
    lines = output.splitlines()
    blocks = []
    active_kind = None
    active_lines = []
    for line in lines:
        start = _START_RE.search(line)
        if start and active_kind is None:
            active_kind = start.group(1)
            active_lines = []
            continue
        end = _END_RE.search(line)
        if end and active_kind is not None:
            blocks.append(SZSOutputBlock(active_kind, "\n".join(active_lines).strip()))
            active_kind = None
            active_lines = []
            continue
        if active_kind is not None:
            active_lines.append(line)
    return tuple(blocks)


def classify_szs(status: str | None) -> str:
    if status is None:
        return "UNKNOWN"
    normalized = status.lower()
    if normalized == "theorem":
        return "CANDIDATE_WARRANTED"
    if normalized == "countersatisfiable":
        return "CANDIDATE_EXCLUDED"
    if normalized == "contradictoryaxioms":
        return "INVALID_PREMISE_SET"
    return "UNKNOWN"


def run_vampire(
    residual: FirstOrderResidual,
    *,
    executable: str = "vampire",
    time_limit_seconds: int = 10,
    extra_args: tuple[str, ...] = (),
) -> ATPCandidateEvidence:
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")

    with tempfile.TemporaryDirectory(prefix="mathgraph-vampire-") as tmp:
        path = Path(tmp) / f"{_name(residual.problem_id)}.p"
        path.write_text(residual.to_tptp(), encoding="utf-8")
        # Vampire 5.x documents these as supported stable CLI surfaces:
        # TPTP input, TPTP proof output, and -t runtime limit.
        command = (
            executable,
            "--input_syntax", "tptp",
            "-p", "tptp",
            "-t", str(time_limit_seconds),
            *extra_args,
            str(path),
        )
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=time_limit_seconds + 5,
            )
            elapsed = time.perf_counter() - started
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            elapsed = time.perf_counter() - started
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return ATPCandidateEvidence(
                engine="vampire",
                problem_id=residual.problem_id,
                residual_id=residual.id,
                tptp_sha256=residual.tptp_sha256,
                szs_status=None,
                candidate_status="UNKNOWN",
                returncode=None,
                elapsed_seconds=elapsed,
                command=command,
                output_blocks=(),
                stdout=stdout,
                stderr=stderr,
            )

    status = parse_szs_status(stdout)
    return ATPCandidateEvidence(
        engine="vampire",
        problem_id=residual.problem_id,
        residual_id=residual.id,
        tptp_sha256=residual.tptp_sha256,
        szs_status=status,
        candidate_status=classify_szs(status),
        returncode=returncode,
        elapsed_seconds=elapsed,
        command=command,
        output_blocks=parse_szs_output_blocks(stdout),
        stdout=stdout,
        stderr=stderr,
    )


def residual_from_dict(data: Mapping[str, Any]) -> FirstOrderResidual:
    axioms = tuple((str(row["name"]), str(row["formula"])) for row in data.get("axioms", ()))
    return FirstOrderResidual(
        problem_id=str(data["problem_id"]),
        axioms=axioms,
        conjecture=str(data["conjecture"]),
        conjecture_name=str(data.get("conjecture_name", "conjecture")),
        boundary_ref=str(data.get("boundary_ref", "logic:first-order")),
        source_refs=tuple(str(x) for x in data.get("source_refs", ())),
    )
