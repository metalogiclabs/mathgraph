#!/usr/bin/env python3
"""Stage only the consumer, policy, manifest, search, and shards for replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
PROBE = r'''
import errno, json, os, pathlib, socket, sys
root = pathlib.Path(".")
actual = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
expected = json.loads(sys.argv[1])
assert actual == expected, (actual, expected)
attempts = []
for family, address in [(socket.AF_INET, ("1.1.1.1", 443)), (socket.AF_INET6, ("2606:4700:4700::1111", 443))]:
    try:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            result = connection.connect_ex(address)
    except OSError as error:
        result = error.errno
    assert result in {errno.EPERM, errno.EACCES, errno.ENETUNREACH, errno.EAFNOSUPPORT}, result
    attempts.append(result)
try:
    pathlib.Path(sys.argv[2]).read_bytes()
except (PermissionError, FileNotFoundError):
    pass
else:
    raise AssertionError("repository is readable")
assert not pathlib.Path("/var/run/docker.sock").exists()
assert not any(name in os.environ for name in ("GH_TOKEN", "GITHUB_TOKEN", "AWS_ACCESS_KEY_ID", "OPENAI_API_KEY"))
print(json.dumps({"network_denied": True, "network_errno": attempts, "repository_unavailable": True,
                  "inputs": actual}, sort_keys=True, separators=(",", ":")))
'''


def _safe_source(root: Path, relative: str) -> Path:
    if (not relative or relative.startswith("/") or "\\" in relative or ":" in relative
            or any(part in {"", ".", ".."} for part in relative.split("/"))):
        raise ValueError("unsafe catalogue path")
    root = root.resolve()
    path = root / relative
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("missing or unsafe catalogue input")
    return path


def run(args) -> None:
    root, policy = args.catalogue_root.resolve(), args.policy.resolve()
    if not policy.is_file() or policy.is_symlink():
        raise ValueError("regular trust policy required")
    if not re.fullmatch(r"[0-9a-f]{64}", args.policy_sha256):
        raise ValueError("exact policy SHA-256 required")
    if hashlib.sha256(policy.read_bytes()).hexdigest() != args.policy_sha256:
        raise ValueError("external policy pin mismatch")
    if args.backend == "docker" and not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_id or ""):
        raise ValueError("Docker requires a previously acquired immutable image ID")
    if args.backend == "macos" and (sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file()):
        raise ValueError("macOS sandbox-exec unavailable")
    manifest = json.loads(_safe_source(root, "manifest.json").read_bytes())
    relative_inputs = ["manifest.json", manifest["search"]["path"], *[entry["path"] for entry in manifest["shards"]]]
    if len(relative_inputs) != len(set(relative_inputs)):
        raise ValueError("duplicate publication path")
    with tempfile.TemporaryDirectory(prefix="source-catalogue-offline-") as temporary:
        stage = Path(temporary).resolve()
        stage.chmod(0o755)
        shutil.copyfile(HERE / "consumer.py", stage / "consumer.py")
        shutil.copyfile(policy, stage / "trust-policy.json")
        for relative in relative_inputs:
            destination = stage / "catalogue" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_safe_source(root, relative), destination)
        for path in stage.rglob("*"):
            path.chmod(0o555 if path.is_dir() else 0o444)
        expected = sorted(["consumer.py", "trust-policy.json", *["catalogue/" + path for path in relative_inputs]])
        image_identity = None
        if args.backend == "macos":
            executable = str(Path(sys._base_executable).resolve())
            profile = ('(version 1)(deny default)(allow process*)(allow sysctl-read)(allow mach-lookup)'
                       '(allow file-read-metadata)(allow file-read* (literal "/"))(deny network*)')
            for path in ("/System", "/usr", "/opt/homebrew", "/dev", str(stage)):
                profile += "(allow file-read* (subpath " + json.dumps(path) + "))"
            prefix = ["/usr/bin/sandbox-exec", "-p", profile, executable, "-I", "-S", "-B"]
            environment = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LC_ALL": "C", "TZ": "UTC"}
        else:
            inspected = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", args.image_id],
                                       capture_output=True, text=True, check=True)
            image_identity = inspected.stdout.strip()
            if image_identity != args.image_id:
                raise ValueError("runtime image identity mismatch")
            prefix = ["docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
                      "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "32",
                      "--memory", "256m", "--user", "65534:65534",
                      "--mount", f"type=bind,source={stage},target=/replay,readonly", "--workdir", "/replay",
                      "--env", "HOME=/nonexistent", "--env", "LC_ALL=C", "--env", "TZ=UTC",
                      image_identity, "python", "-I", "-S", "-B"]
            environment = None

        def execute(command):
            return subprocess.run(prefix + command, cwd=stage, env=environment,
                                  capture_output=True, check=True, timeout=90)

        probe = json.loads(execute(["-c", PROBE, json.dumps(expected), str(HERE.parents[1] / "AGENTS.md")]).stdout)
        command = ["consumer.py", "--catalogue-root", "catalogue", "--policy", "trust-policy.json",
                   "--policy-sha256", args.policy_sha256, "--audit-imports"]
        first, second = execute(command), execute(command)
        if first.stdout != second.stdout:
            raise ValueError("non-deterministic isolated replay")
        audit = json.loads(first.stderr)
        if audit["forbidden_imports"] or not audit["isolated"] or not audit["no_site"] or not audit["dont_write_bytecode"]:
            raise ValueError("consumer isolation/import audit failed")
        metadata = {"backend": args.backend, "runtime_image_identity": image_identity,
                    "runtime_executable": executable if args.backend == "macos" else "python",
                    "probe": probe, "import_audit": audit,
                    "replay_sha256": hashlib.sha256(first.stdout).hexdigest(),
                    "replay_arguments": command, "replays_identical": True}
        print(json.dumps(metadata, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        sys.stdout.buffer.write(first.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("macos", "docker"), required=True)
    parser.add_argument("--catalogue-root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--image-id")
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print("ISOLATION_FAILED: " + str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr
            if detail:
                print(detail, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
