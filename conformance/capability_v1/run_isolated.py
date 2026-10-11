#!/usr/bin/env python3
"""Host-only harness. The offline runtime receives exactly four read-only files."""

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
expected = {"consumer.py", "capability-contract.json", "finite.json", "trust-policy.json"}
assert {p.name for p in pathlib.Path(".").iterdir()} == expected
results = []
for family, address in [(socket.AF_INET, ("1.1.1.1", 443)), (socket.AF_INET6, ("2606:4700:4700::1111", 443))]:
    try:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            result = connection.connect_ex(address)
    except OSError as error:
        result = error.errno
    assert result in {errno.EPERM, errno.EACCES, errno.ENETUNREACH, errno.EAFNOSUPPORT}, result
    results.append(result)
try:
    pathlib.Path(sys.argv[1]).read_bytes()
except (PermissionError, FileNotFoundError):
    pass
else:
    raise AssertionError("repository is readable")
assert not pathlib.Path("/var/run/docker.sock").exists()
assert not any(key in os.environ for key in ("GH_TOKEN", "GITHUB_TOKEN", "AWS_ACCESS_KEY_ID", "OPENAI_API_KEY"))
print(json.dumps({"network_denied": True, "network_errno": results,
                  "repository_unavailable": True, "inputs": sorted(expected)}, sort_keys=True))
'''


def run(args):
    if hashlib.sha256((HERE / "trust-policy.json").read_bytes()).hexdigest() != args.policy_sha256:
        raise ValueError("external policy pin mismatch")
    if args.backend == "docker" and not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_id or ""):
        raise ValueError("Docker requires a previously acquired immutable image ID")
    if args.backend == "macos" and sys.platform != "darwin":
        raise ValueError("macOS sandbox unavailable")
    with tempfile.TemporaryDirectory(prefix="finite-capability-offline-") as tmp:
        stage = Path(tmp).resolve()
        stage.chmod(0o755)
        sources = [(HERE / "consumer.py", "consumer.py"),
                   (HERE / "trust-policy.json", "trust-policy.json"),
                   (HERE / "fixtures/capability-contract.json", "capability-contract.json"),
                   (HERE / "fixtures/finite-representation-refinement-v1.json", "finite.json")]
        for source, name in sources:
            shutil.copyfile(source, stage / name)
            (stage / name).chmod(0o444)
        image_identity, executable = None, None
        if args.backend == "macos":
            executable = str(Path(sys._base_executable).resolve())
            profile = '(version 1)(deny default)(allow process*)(allow sysctl-read)(allow mach-lookup)(allow file-read-metadata)(allow file-read* (literal "/"))(deny network*)'
            for path in ("/System", "/usr", "/opt/homebrew", "/dev", str(stage)):
                profile += '(allow file-read* (subpath ' + json.dumps(path) + '))'
            prefix = ["/usr/bin/sandbox-exec", "-p", profile, executable, "-I", "-S"]
            environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
        else:
            inspected = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", args.image_id],
                                       check=True, capture_output=True, text=True)
            image_identity = inspected.stdout.strip()
            if image_identity != args.image_id:
                raise ValueError("runtime image identity mismatch")
            prefix = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                      "--security-opt", "no-new-privileges", "--pids-limit", "32", "--memory", "256m",
                      "--user", "65534:65534", "--mount", f"type=bind,source={stage},target=/replay,readonly",
                      "--workdir", "/replay", image_identity, "python", "-I", "-S"]
            environment = None  # No host variables are passed into the container.

        def execute(command):
            return subprocess.run(prefix + command, cwd=stage, env=environment,
                                  capture_output=True, check=True, timeout=30)

        probe = json.loads(execute(["-c", PROBE, str(HERE.parents[1] / "AGENTS.md")]).stdout)
        command = ["consumer.py", "--fixture", "finite.json", "--contract", "capability-contract.json",
                   "--policy", "trust-policy.json", "--policy-sha256", args.policy_sha256, "--audit-imports"]
        first, second = execute(command), execute(command)
        if first.stdout != second.stdout:
            raise ValueError("non-deterministic replay")
        audit = json.loads(first.stderr)
        if audit["nonstdlib_modules"] or not audit["isolated"] or not audit["no_site"]:
            raise ValueError("non-isolated imports")
        metadata = {"backend": args.backend, "runtime_image_identity": image_identity,
                    "runtime_executable": executable, "probe": probe, "import_audit": audit,
                    "replay_sha256": hashlib.sha256(first.stdout).hexdigest(), "replays_identical": True}
        print(json.dumps(metadata, sort_keys=True), file=sys.stderr)
        sys.stdout.buffer.write(first.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("macos", "docker"), required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--image-id")
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("ISOLATION_FAILED: " + str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr.decode(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
