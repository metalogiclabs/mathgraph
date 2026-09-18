from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class ConfirmatoryLockedError(RuntimeError):
    """Raised when code attempts to enter the confirmatory namespace before lock."""


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(data: Any) -> str:
    return sha256(_canonical_json(data).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ABGPDesign:
    raw: Mapping[str, Any]
    status: str
    confirmatory_execution_enabled: bool
    design_version: str
    development_namespace: str
    confirmatory_namespace: str
    arms: Mapping[str, Any]
    digest: str


@dataclass(frozen=True)
class ABGPAnalysisPlan:
    raw: Mapping[str, Any]
    status: str
    normative: bool
    familywise_alpha: float
    primary_arms: tuple[str, ...]
    arms: Mapping[str, Any]
    digest: str


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object at {p}")
    return data


def load_design_manifest(path: str | Path) -> ABGPDesign:
    data = _read_json(path)
    if data.get("schema") != "mathgraph.abgp.design-manifest.v1":
        raise ValueError("unexpected ABGP design-manifest schema")
    status = str(data.get("status", ""))
    enabled = bool(data.get("confirmatory_execution_enabled", False))
    if status != "FROZEN" and enabled:
        raise ValueError("non-FROZEN design manifest cannot enable confirmation")
    namespaces = data.get("seed_namespaces")
    if not isinstance(namespaces, dict):
        raise ValueError("missing seed_namespaces")
    development = str(namespaces.get("development", ""))
    confirmatory = str(namespaces.get("confirmatory", ""))
    if not development or not confirmatory or development == confirmatory:
        raise ValueError("development and confirmatory namespaces must be distinct")
    arms = data.get("arms")
    if not isinstance(arms, dict) or tuple(arms.keys()) != ("A", "B", "G", "P"):
        raise ValueError("design manifest must define arms A, B, G, P in canonical order")
    return ABGPDesign(
        raw=data,
        status=status,
        confirmatory_execution_enabled=enabled,
        design_version=str(data.get("design_version", "")),
        development_namespace=development,
        confirmatory_namespace=confirmatory,
        arms=arms,
        digest=_digest(data),
    )


def load_analysis_plan(path: str | Path) -> ABGPAnalysisPlan:
    data = _read_json(path)
    if data.get("schema") != "mathgraph.abgp.analysis-plan.v1":
        raise ValueError("unexpected ABGP analysis-plan schema")
    arms = data.get("arms")
    if not isinstance(arms, dict) or tuple(arms.keys()) != ("A", "B", "G", "P"):
        raise ValueError("analysis plan must define arms A, B, G, P in canonical order")
    return ABGPAnalysisPlan(
        raw=data,
        status=str(data.get("status", "")),
        normative=bool(data.get("normative", False)),
        familywise_alpha=float(data.get("familywise_alpha", 0.0)),
        primary_arms=tuple(arms.keys()),
        arms=arms,
        digest=_digest(data),
    )


def derive_dev_seed(arm: str, cell: str, index: int, generator_version: str) -> str:
    if arm not in {"A", "B", "G", "P"}:
        raise ValueError(f"unknown ABGP arm: {arm}")
    if index < 0:
        raise ValueError("index must be non-negative")
    if not cell or not generator_version:
        raise ValueError("cell and generator_version are required")
    material = f"ABGP-DEV-v1|{arm}|{cell}|{index}|{generator_version}"
    return sha256(material.encode("utf-8")).hexdigest()


def reject_confirmatory_namespace(namespace: str, final_lock: Mapping[str, Any] | None = None) -> None:
    if namespace != "ABGP-CONFIRM-v1":
        raise ValueError(f"not the registered confirmatory namespace: {namespace}")
    if final_lock is None:
        raise ConfirmatoryLockedError("ABGP confirmation is locked: no final lock supplied")
    if final_lock.get("status") != "FROZEN":
        raise ConfirmatoryLockedError("ABGP confirmation is locked: final lock is not FROZEN")
    if final_lock.get("confirmatory_execution_enabled") is not True:
        raise ConfirmatoryLockedError("ABGP confirmation is locked: execution is not enabled")
    raise ConfirmatoryLockedError(
        "ABGP confirmation remains disabled in preregistration-freeze-v1; unlocking requires a separate reviewed change"
    )
