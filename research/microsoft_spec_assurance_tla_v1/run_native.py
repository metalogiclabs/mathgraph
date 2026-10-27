#!/usr/bin/env python3
"""Run real TLC on one untouched public source and two local controlled mutants."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

PIN = "53955cf52c9cbe417b2bde68ab72edf2b9096cfc"
JAR_SHA = "78f7e2c6bf9a8b65eda665a23e94431255587e0b43a834a4e2af1723562d9b4a"
CASES = ("author", "mutant_checked", "mutant_weakened")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_cases(source: Path, output: Path) -> None:
    """Copy author files unchanged and derive a local falsifier, never edit source."""
    source_model = (source / "LamportMutex.tla").read_text()
    config = (source / "MCLamportMutex.cfg").read_text()
    wrapper = (source / "MCLamportMutex.tla").read_text()
    guard = "  /\\ \\A q \\in Proc \\ {p} : beats(p,q)\n"
    if source_model.count(guard) != 1:
        raise ValueError("SOURCE_GUARD_NOT_UNIQUE")
    if "INVARIANTS TypeOK BoundedNetwork Mutex" not in config:
        raise ValueError("AUTHOR_MUTEX_CHECK_ABSENT")
    mutant = source_model.replace(guard, "  /\\ TRUE\n")
    smaller = config.replace("N = 3", "N = 2").replace(
        "MaxNat = 7", "MaxNat = 4").replace("maxClock = 6", "maxClock = 3")
    if smaller == config:
        raise ValueError("SOURCE_MODEL_BOUNDS_CHANGED")
    weak = smaller.replace("INVARIANTS TypeOK BoundedNetwork Mutex",
                           "INVARIANTS TypeOK BoundedNetwork")
    for name, model, cfg in (
        ("author", source_model, config),
        ("mutant_checked", mutant, smaller),
        ("mutant_weakened", mutant, weak),
    ):
        destination = output / name
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "LamportMutex.tla").write_text(model)
        (destination / "MCLamportMutex.tla").write_text(wrapper)
        (destination / "MCLamportMutex.cfg").write_text(cfg)


def run(source: Path, jar: Path, output: Path) -> dict:
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"],
                                       text=True).strip()
    if revision != PIN:
        raise ValueError(f"UPSTREAM_REVISION_CHANGED:{revision}")
    jar_hash = digest(jar)
    if jar_hash != JAR_SHA:
        raise ValueError(f"TLC_BINARY_DRIFT:{jar_hash}")
    original_hashes = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
    prepare_cases(source, output)
    report = {"source_commit": revision, "tlc_sha256": jar_hash,
              "original_files_sha256": original_hashes, "cases": {}}
    for name in CASES:
        directory = output / name
        cmd = ["java", "-XX:+UseParallelGC", "-Xmx1800m", "-cp", str(jar.resolve()),
               "tlc2.TLC", "-workers", "2", "-config", "MCLamportMutex.cfg",
               "MCLamportMutex.tla"]
        start = time.monotonic()
        try:
            p = subprocess.run(cmd, cwd=directory, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, timeout=180,
                               check=False)
        except subprocess.TimeoutExpired as exc:
            (directory / "tlc.log").write_text(f"TIMEOUT: {exc}\n")
            (directory / "tlc.exit").write_text("124\n")
            raise RuntimeError(f"{name}:NATIVE_TLC_TIMEOUT") from exc
        (directory / "tlc.log").write_text(p.stdout)
        (directory / "tlc.exit").write_text(str(p.returncode) + "\n")
        report["cases"][name] = {
            "command": cmd, "exit": p.returncode,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "log_sha256": digest(directory / "tlc.log"),
            "config_sha256": digest(directory / "MCLamportMutex.cfg"),
            "model_sha256": digest(directory / "LamportMutex.tla"),
        }
    unchanged = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
    if unchanged != original_hashes:
        raise RuntimeError("UPSTREAM_SOURCE_MUTATED")
    output.mkdir(parents=True, exist_ok=True)
    (output / "native-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--jar", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = run(args.source.resolve(), args.jar.resolve(), args.output.resolve())
    print("NATIVE_TLC_LANES", {k: v["exit"] for k, v in report["cases"].items()})


if __name__ == "__main__":
    main()
