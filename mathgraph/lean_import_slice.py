"""Exact local-import closure extraction for Lean projects.

Given a complete pinned source checkout and one or more target Lean modules,
compute the transitive closure of local imports, copy only that closure into an
isolated project, and retain a content-addressed manifest.

This module does not prove the copied project is sufficient. Sufficiency is
established only by the later Lake/Lean build of the isolated slice.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable, Sequence

IMPORT_RE = re.compile(r"^\s*(?:(?:public|private)\s+)?import\s+(.+?)\s*$")
MODULE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*")


@dataclass(frozen=True)
class SliceFile:
    path: str
    bytes: int
    sha256: str
    imports: tuple[str, ...]
    local_imports: tuple[str, ...]
    external_imports: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def module_to_path(module: str) -> Path:
    return Path(*module.split(".")).with_suffix(".lean")


def path_to_module(path: str | Path) -> str:
    p = Path(path).with_suffix("")
    return ".".join(p.parts)


def parse_imports(text: str) -> tuple[str, ...]:
    out: list[str] = []
    for line in text.splitlines():
        m = IMPORT_RE.match(line)
        if not m:
            continue
        out.extend(MODULE_RE.findall(m.group(1)))
    return tuple(out)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_local_import_closure(
    repo_root: str | Path,
    targets: Sequence[str | Path],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if not root.exists():
        raise FileNotFoundError(root)

    target_paths = [Path(t) for t in targets]
    for p in target_paths:
        if p.is_absolute():
            raise ValueError("targets must be repo-relative")
        if p.suffix != ".lean":
            p = module_to_path(str(p))
        if not (root / p).exists():
            raise FileNotFoundError(root / p)

    pending = list(target_paths)
    seen: set[Path] = set()
    files: list[SliceFile] = []
    unresolved_local_candidates: set[str] = set()

    while pending:
        rel = pending.pop()
        if rel in seen:
            continue
        seen.add(rel)
        path = root / rel
        data = path.read_bytes()
        text = data.decode("utf-8")
        imports = parse_imports(text)
        local: list[str] = []
        external: list[str] = []

        for module in imports:
            candidate = module_to_path(module)
            if (root / candidate).exists():
                local.append(module)
                if candidate not in seen:
                    pending.append(candidate)
            else:
                external.append(module)
                if module.split(".", 1)[0] in {"P2M", "Definitions", "Theorems"}:
                    unresolved_local_candidates.add(module)

        files.append(
            SliceFile(
                path=str(rel),
                bytes=len(data),
                sha256=sha256_bytes(data),
                imports=imports,
                local_imports=tuple(local),
                external_imports=tuple(external),
            )
        )

    files.sort(key=lambda x: x.path)
    return {
        "schema": "mathgraph.lean-local-import-slice.v1",
        "targets": [str(x) for x in target_paths],
        "file_count": len(files),
        "source_bytes": sum(x.bytes for x in files),
        "files": [x.to_dict() for x in files],
        "unresolved_local_candidates": sorted(unresolved_local_candidates),
        "status": "CANDIDATE_UNTIL_ISOLATED_BUILD",
    }


def materialize_slice(
    repo_root: str | Path,
    targets: Sequence[str | Path],
    out_root: str | Path,
    *,
    config_files: Sequence[str] = (
        "lakefile.lean",
        "lake-manifest.json",
        "lean-toolchain",
    ),
    extra_files: Sequence[tuple[str | Path, str | Path]] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = Path(out_root).resolve()
    report = resolve_local_import_closure(root, targets)
    if report["unresolved_local_candidates"]:
        raise RuntimeError(
            "unresolved project-local imports: "
            + ", ".join(report["unresolved_local_candidates"])
        )

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for row in report["files"]:
        rel = Path(row["path"])
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)

    copied_configs = []
    for name in config_files:
        src = root / name
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, out / name)
        copied_configs.append(name)

    copied_extras = []
    for src_value, dst_value in extra_files:
        src = Path(src_value)
        dst = out / dst_value
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied_extras.append(str(dst_value))

    report = {
        **report,
        "slice_root": str(out),
        "config_files": copied_configs,
        "extra_files": copied_extras,
    }
    (out / "crystal_slice_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
