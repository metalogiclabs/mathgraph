#!/usr/bin/env python3
"""Replay the published FRET -> C2PO -> native R2U2 case on original sources.

Requires Python 3.12+, Node.js 24+, npm, Git, GCC and Make, and public network
access to GitHub and npm. Downloads are local; nothing is published or sent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

FRET = "cf0f913cc15c41705e803593297e89cd6056b839"
R2U2 = "2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, default=Path("reproduction"))
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    work = args.work_dir.resolve()
    if work.exists() and any(work.iterdir()):
        raise SystemExit("Choose a new or empty --work-dir; previous evidence will not be overwritten.")
    for tool in ("git", "node", "npm", "gcc", "make"):
        if not shutil.which(tool):
            raise SystemExit("Missing prerequisite: " + tool)
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12 or newer is required by the pinned compiler.")
    method = package / "method"
    for row in json.loads((package / "method-source-manifest.json").read_text()):
        data = (package / row["package_path"]).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != row["git_blob"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise SystemExit("Pinned method file changed: " + row["package_path"])
    work.mkdir(parents=True, exist_ok=True)
    log = (work / "reproduction.log").open("w")
    started = datetime.now(timezone.utc).isoformat()

    def call(argv, *, cwd=work, env=None):
        print("Running:", " ".join(map(str, argv)), flush=True)
        log.write("$ " + " ".join(map(str, argv)) + "\n")
        log.flush()
        subprocess.run(list(map(str, argv)), cwd=cwd, env=env, check=True,
                       stdout=log, stderr=subprocess.STDOUT, timeout=600)

    fret = work / "fret"
    r2u2 = work / "r2u2"
    for repo, checkout, sha in (("NASA-SW-VnV/fret", fret, FRET), ("R2U2/r2u2", r2u2, R2U2)):
        call(["git", "clone", "--filter=blob:none", "--no-checkout", "https://github.com/" + repo + ".git", checkout])
        if repo.endswith("/fret"):
            call(["git", "-C", checkout, "sparse-checkout", "init", "--cone"])
            call(["git", "-C", checkout, "sparse-checkout", "set", "fret-electron/app", "fret-electron/support"])
        call(["git", "-C", checkout, "checkout", "--detach", sha])
        actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        if actual != sha:
            raise SystemExit("Upstream checkout mismatch")
    deps = work / "node-deps"
    deps.mkdir()
    for name in ("package.json", "package-lock.json"):
        shutil.copy2(package / "node-deps" / name, deps / name)
    call(["npm", "ci", "--prefix", deps, "--ignore-scripts", "--no-fund", "--no-audit"])
    call([sys.executable, "-m", "unittest", "discover", "-s", method, "-p", "test_*.py", "-v"])
    output = work / "native-rocket-out"
    environment = dict(os.environ, NODE_PATH=str(deps / "node_modules"),
                       ROCKET_FRET_ROOT=str(fret), ROCKET_OUTPUT=str(output))
    call(["node", method / "export_rocket_native.mjs"], env=environment)
    call(["make", "-C", r2u2 / "monitors/c", "-j2", "all"])
    call([sys.executable, method / "native_replay.py", "--out", output, "--fret", fret, "--r2u2", r2u2])
    call(["make", "-C", r2u2 / "monitors/c", "clean"])
    call(["make", "-C", r2u2 / "monitors/c", "-j2", "all"])
    call([sys.executable, package / "assess_local.py", "--method", method, "--out", output,
          "--monitor", r2u2 / "monitors/c/build/r2u2"])
    versions = {}
    for label, argv in (("python", [sys.executable, "--version"]), ("node", ["node", "--version"]),
                        ("npm", ["npm", "--version"]), ("gcc", ["gcc", "--version"]),
                        ("make", ["make", "--version"]), ("git", ["git", "--version"])):
        versions[label] = subprocess.check_output(argv, text=True).splitlines()[0]
    for checkout in (fret, r2u2):
        dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"], text=True)
        if dirty:
            raise SystemExit("Tracked upstream source changed: " + str(checkout))
    result = json.loads((output / "local-requalification.json").read_text())
    receipt = {"started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
               "versions": versions, "method_commit": "2b0e21e94e64ca54ff35c1d4572c60b3b6049720",
               "source_pins": {"fret": FRET, "r2u2": R2U2},
               "tracked_sources_unchanged": True, "original_contract_tests": 11,
               "original_native_positions": result["positions"],
               "actual_artifact_mutations_refused": len(result["actual_artifact_mutations"]),
               "additional_overlap_positions": result["additional_overlap_control"]["positions"],
               "operational_intent": "UNKNOWN", "repair_authority": "UNKNOWN",
               "external_publication_or_contact": "NONE"}
    (work / "run-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    log.close()
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
