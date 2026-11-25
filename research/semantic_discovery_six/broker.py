#!/usr/bin/env python3
"""Logged, credit-bounded file and process access for either trial arm.

Usage::

    python broker.py --arm-root ARM --case CASEID list [RELATIVE_DIRECTORY]
    python broker.py --arm-root ARM --case CASEID read RELATIVE_FILE
    python broker.py --arm-root ARM --case CASEID write < request.json
    python broker.py --arm-root ARM --case CASEID run < request.json
    python broker.py --arm-root ARM --case shared finalize < final.json

``write`` accepts {"path": "work/example.py", "content": "..."}; ``run``
accepts {"argv": ["python", "example.py"], "timeout": 60}. Finalization accepts
any JSON value and exclusively creates results/final.json and its SHA256 lock.

Costs are list=1, read=1, write=1, run=4, finalize=1. Each named case has 24
credits; the reserved case name ``shared`` has 12. An admitted attempt costs its
full credits even if it fails. A rejected over-budget attempt costs zero.
Named cases must have an existing nonsymlink inputs/CASEID.json; arbitrary
aliases cannot create fresh budgets. Shared requests cannot read case inputs.
Case requests can read only their assigned input, work/kit, and retained results.

Every request has a durable start record reserving credits before execution,
then an end record with its outcome. Only start records charge credits. Wall
times are Unix nanoseconds; monotonic times are process-independent monotonic
nanoseconds. input_bytes counts raw stdin plus an explicit path argument.
output_bytes counts the complete source bytes read, serialized listing bytes,
or complete captured process stdout/stderr, before display truncation.
written_bytes records action data placed in work/results. audit_written_bytes
separately records retained audit data, with content-addressed deduplication;
response_bytes records the complete emitted JSON response including its newline.
Request payloads and write versions are retained under results/.broker-audit.
Every run snapshots work, kit, the assigned input, and all non-audit results both
before and after execution. Snapshots retain file contents in immutable blobs,
plus paths, modes, directories and symlink targets. Each snapshot has a 16 MiB /
512 entry cap; exceeding it is a recorded failure (before execution when the
pre-run snapshot exceeds the cap). Audit storage is excluded from snapshots.
Processes start in a separate session. Timeout kills their process group before
capturing the post-run snapshot; leftover group members are also killed after a
normal exit, so an invocation cannot leave background mutation in its group.

This is procedural isolation for honest research, NOT a security sandbox.
File operations reject traversal and symlinks; process operands receive a best
effort path check. Native Python, Node, or compiled code still shares the host,
inherits its environment, and can bypass these checks through code. Inputs and
the journal must therefore also be protected by the trial procedure. The
broker contains no domain checks or expected outcomes.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid


COSTS = {"list": 1, "read": 1, "write": 1, "run": 4, "finalize": 1}
CASE_BUDGET = 24
SHARED_BUDGET = 12
DISPLAY_LIMIT = 8000
MAX_TIMEOUT = 60.0
FINAL_NAMES = {"final.json", "final.sha256", ".final.lock"}
AUDIT_DIRECTORY = ".broker-audit"
SNAPSHOT_MAX_BYTES = 16 * 1024 * 1024
SNAPSHOT_MAX_ENTRIES = 512


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


class BrokerError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Broker:
    def __init__(self, arm_root):
        self.root = Path(arm_root).resolve(strict=True)
        if not self.root.is_dir():
            raise BrokerError("invalid_root", "arm root must be an existing directory")

    def _path(self, relative, *, writable=False):
        if not isinstance(relative, str) or not relative or "\x00" in relative:
            raise BrokerError("invalid_path", "path must be a nonempty relative string")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative:
            raise BrokerError("path_escape", "absolute paths and parent traversal are forbidden")
        if writable:
            if len(path.parts) < 2 or path.parts[0] not in {"work", "results"}:
                raise BrokerError("read_only", "writes must be beneath work or results")
            if path.parts[0] == "results" and path.parts[1] in FINAL_NAMES | {AUDIT_DIRECTORY}:
                raise BrokerError("reserved_path", "final and audit artifacts are reserved to the broker")
        current = self.root
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                raise BrokerError("symlink", "symlink paths are forbidden")
        if not current.resolve(strict=False).is_relative_to(self.root):
            raise BrokerError("path_escape", "path leaves arm root")
        return current

    def _ensure_directory(self, relative):
        path = self._path(relative)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _validate_case(self, case):
        if not isinstance(case, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case):
            raise BrokerError("invalid_case", "case must be a simple assigned case identifier")
        if case != "shared" and not self._path(f"inputs/{case}.json").is_file():
            raise BrokerError("unassigned_case", "case has no assigned immutable input")

    def _authorize_read(self, source, case):
        relative = source.relative_to(self.root)
        if relative.parts and relative.parts[0] == "inputs":
            if case == "shared" or relative != Path("inputs") / f"{case}.json":
                raise BrokerError("case_input_denied", "request cannot inspect another case's input")

    def _immutable(self, relative, content, metrics):
        target = self._path(f"results/{AUDIT_DIRECTORY}/{relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if not target.is_file() or target.read_bytes() != content:
                raise BrokerError("audit_corrupt", "immutable audit artifact has conflicting contents")
        else:
            with target.open("xb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            target.chmod(0o444)
            metrics["audit_written_bytes"] += len(content)
        return {"path": str(target.relative_to(self.root)), "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest()}

    def _blob(self, content, metrics):
        digest = hashlib.sha256(content).hexdigest()
        return self._immutable(f"blobs/{digest}", content, metrics)

    def _retain_request(self, base, payload, metrics):
        blob = self._blob(payload, metrics)
        descriptor = {key: base[key] for key in ("request_id", "action", "case", "input_bytes", "argv")}
        descriptor.update(path=base.get("path"), payload=blob)
        artifact = self._immutable(f"requests/{base['request_id']}.json", json_bytes(descriptor), metrics)
        metrics["request_artifact"] = artifact

    def _snapshot(self, request_id, phase, case, metrics):
        entries, size, failure = {}, 0, None
        roots = [self.root / "work", self.root / "kit", self.root / "results"]
        if case != "shared":
            roots.append(self._path(f"inputs/{case}.json"))

        def visit(candidate):
            nonlocal size
            relative = str(candidate.relative_to(self.root))
            if relative == f"results/{AUDIT_DIRECTORY}":
                return
            if len(entries) >= SNAPSHOT_MAX_ENTRIES:
                raise BrokerError("snapshot_limit", "snapshot exceeds 512 entries")
            info = candidate.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                entries[relative] = {"type": "symlink", "target": os.readlink(candidate), "mode": mode}
            elif stat.S_ISDIR(info.st_mode):
                entries[relative] = {"type": "directory", "mode": mode}
                for child in sorted(candidate.iterdir()):
                    visit(child)
            elif stat.S_ISREG(info.st_mode):
                if size + info.st_size > SNAPSHOT_MAX_BYTES:
                    raise BrokerError("snapshot_limit", "snapshot exceeds 16 MiB")
                content = candidate.read_bytes()
                if size + len(content) > SNAPSHOT_MAX_BYTES:
                    raise BrokerError("snapshot_limit", "snapshot exceeds 16 MiB")
                size += len(content)
                entries[relative] = {"type": "file", "mode": mode, **self._blob(content, metrics)}
            else:
                raise BrokerError("snapshot_special_file", "snapshot cannot retain special files")

        try:
            for root in roots:
                if root.exists() or root.is_symlink():
                    visit(root)
        except (BrokerError, OSError) as exc:
            failure = exc if isinstance(exc, BrokerError) else BrokerError("snapshot_failed", str(exc))
        manifest = {"request_id": request_id, "phase": phase, "case": case,
                    "complete": failure is None, "content_bytes": size, "entries": entries}
        if failure:
            manifest.update(error_code=failure.code, error=str(failure))
        artifact = self._immutable(f"runs/{request_id}.{phase}.json", json_bytes(manifest), metrics)
        metrics.setdefault("snapshots", {})[phase] = artifact
        if failure:
            raise failure
        return artifact

    @staticmethod
    def _append_journal(journal, event):
        journal.seek(0, os.SEEK_END)
        data = json_bytes(event)
        offset = 0
        while offset < len(data):
            written = journal.write(data[offset:])
            if not written:
                raise OSError("short journal write")
            offset += written
        journal.flush()
        os.fsync(journal.fileno())

    @staticmethod
    def _used_credits(journal, case):
        journal.seek(0)
        used = 0
        for line in journal:
            try:
                event = json.loads(line)
                if event["phase"] not in {"start", "end"}:
                    raise ValueError("unknown journal phase")
                credits = event["credits"]
                if isinstance(credits, bool) or not isinstance(credits, int) or credits < 0:
                    raise ValueError("invalid credit count")
                if event["phase"] == "start" and event["case"] == case:
                    used += credits
            except (KeyError, TypeError, ValueError, UnicodeError) as exc:
                raise BrokerError("journal_corrupt", "cannot establish budget from journal") from exc
        return used

    def request(self, action, case, *, path=None, payload=b""):
        """Return (JSON-serializable response, CLI exit status); never hide failures."""
        start_wall, start_mono = time.time_ns(), time.monotonic_ns()
        request_id = uuid.uuid4().hex
        input_bytes = len(payload) + (len(path.encode("utf-8")) if isinstance(path, str) else 0)
        base = {
            "request_id": request_id,
            "action": action,
            "case": case,
            "wall_start_ns": start_wall,
            "monotonic_start_ns": start_mono,
            "wall_end_ns": None,
            "monotonic_end_ns": None,
            "input_bytes": input_bytes,
            "output_bytes": 0,
            "written_bytes": 0,
            "audit_written_bytes": 0,
            "response_bytes": 0,
            "argv": None,
            "exit": None,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "payload_bytes": len(payload),
        }
        if path is not None:
            base["path"] = path
        # Parse only for audit metadata here; validation remains a charged action.
        if action == "run":
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    base["argv"] = parsed.get("argv")
            except (ValueError, UnicodeError):
                pass
        flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.root / "journal.jsonl", flags, 0o600)
            with os.fdopen(fd, "a+b", buffering=0) as journal:
                if not stat.S_ISREG(os.fstat(journal.fileno()).st_mode):
                    raise OSError("journal must be a regular file")
                fcntl.flock(journal.fileno(), fcntl.LOCK_EX)
                return self._request_locked(journal, base, action, case, path, payload)
        except OSError as exc:
            return {
                "ok": False, "action": action, "case": case, "request_id": request_id,
                "error_code": "journal_unavailable", "error": str(exc), "exit": 1,
            }, 1

    def _request_locked(self, journal, base, action, case, path, payload):
        budget = SHARED_BUDGET if case == "shared" else CASE_BUDGET
        used, credits, denial = 0, 0, None
        try:
            used = self._used_credits(journal, case)
            self._validate_case(case)
            if action not in COSTS:
                raise BrokerError("invalid_action", "unknown broker action")
            if used + COSTS[action] > budget:
                raise BrokerError("budget_exceeded", "request would exceed the case credit budget")
            credits = COSTS[action]
        except BrokerError as exc:
            denial = exc

        self._append_journal(journal, {**base, "phase": "start", "credits": credits,
                                      "budget": budget, "used_before": used})
        metrics = {"output_bytes": 0, "written_bytes": 0, "audit_written_bytes": 0}
        response = {
            "ok": False, "action": action, "case": case, "request_id": base["request_id"],
            "credits": credits, "budget": budget, "used": used + credits,
            "remaining": max(0, budget - used - credits), "exit": 1,
        }
        try:
            self._retain_request(base, payload, metrics)
            if denial:
                raise denial
            data = self._perform(action, case, path, payload, base["request_id"], metrics)
            response.update(data)
            # _perform explicitly reports child failure without discarding its output.
            response["ok"] = data.get("ok", True)
            response["exit"] = data.get("exit", 0)
        except BrokerError as exc:
            response.update(error_code=exc.code, error=str(exc))
        except (OSError, ValueError, TypeError, UnicodeError) as exc:
            response.update(error_code="operation_failed", error=str(exc))
        except Exception as exc:
            response.update(error_code="operation_failed", error=f"{type(exc).__name__}: {exc}")

        end_wall, end_mono = time.time_ns(), time.monotonic_ns()
        event = {**base, **metrics, "phase": "end", "credits": 0,
                 "reserved_credits": credits, "budget": budget, "used_after": used + credits,
                 "wall_end_ns": end_wall, "monotonic_end_ns": end_mono,
                 "elapsed_seconds": (end_mono - base["monotonic_start_ns"]) / 1e9,
                 "response_bytes": len(json_bytes(response)), "exit": response["exit"],
                 "ok": response["ok"],
                 "total_written_bytes": metrics["written_bytes"] + metrics["audit_written_bytes"]}
        for field in ("error", "error_code", "sha256", "stdout_path", "stderr_path", "timeout_seconds"):
            if field in response:
                event[field] = response[field]
        try:
            self._append_journal(journal, event)
        except OSError as exc:
            # The durable reservation remains as an explicitly unfinished request.
            return {"ok": False, "action": action, "case": case,
                    "request_id": base["request_id"], "exit": 1,
                    "error_code": "journal_write_failed", "error": str(exc),
                    "action_result": response}, 1
        return response, 0 if response["ok"] else 1

    @staticmethod
    def _json_payload(payload):
        try:
            return json.loads(payload)
        except (ValueError, UnicodeError) as exc:
            raise BrokerError("invalid_json", "stdin must contain valid JSON") from exc

    def _perform(self, action, case, path, payload, request_id, metrics):
        if action == "list":
            directory = self._path(path or ".")
            self._authorize_read(directory, case)
            if not directory.is_dir():
                raise BrokerError("path_missing", "listing directory does not exist")
            files = []
            for current, directories, names in os.walk(directory, followlinks=False):
                directories[:] = sorted(name for name in directories
                                        if not (Path(current) / name).is_symlink())
                for name in sorted(names):
                    candidate = Path(current) / name
                    if candidate.is_symlink():
                        continue
                    try:
                        self._authorize_read(candidate, case)
                    except BrokerError:
                        continue
                    info = candidate.stat()
                    if stat.S_ISREG(info.st_mode):
                        files.append({"path": str(candidate.relative_to(self.root)), "bytes": info.st_size})
            data = {"files": sorted(files, key=lambda item: item["path"])}
            metrics["output_bytes"] = len(json_bytes(data))
            return data
        if action == "read":
            source = self._path(path)
            self._authorize_read(source, case)
            if not source.is_file():
                raise BrokerError("path_missing", "source file does not exist")
            content = source.read_bytes()
            metrics["output_bytes"] = len(content)
            try:
                return {"path": path, "encoding": "utf-8", "content": content.decode("utf-8")}
            except UnicodeError:
                return {"path": path, "encoding": "base64",
                        "content": base64.b64encode(content).decode("ascii")}
        if action == "write":
            request = self._json_payload(payload)
            if not isinstance(request, dict) or not isinstance(request.get("content"), str):
                raise BrokerError("invalid_write", "write requires an object with string path and content")
            target = self._path(request.get("path"), writable=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            content = request["content"].encode("utf-8")
            if target.exists() and not target.is_file():
                raise BrokerError("invalid_write", "write target must be a regular file")
            prior = self._blob(target.read_bytes(), metrics) if target.exists() else None
            new = self._blob(content, metrics)
            version = {"request_id": request_id, "path": str(target.relative_to(self.root)),
                       "prior": prior, "new": new}
            metrics["write_version"] = self._immutable(f"writes/{request_id}.json", json_bytes(version), metrics)
            with target.open("wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            metrics["written_bytes"] = len(content)
            return {"path": str(target.relative_to(self.root)), "bytes": len(content)}
        if action == "run":
            return self._run(self._json_payload(payload), request_id, case, metrics)
        if action == "finalize":
            content = json_bytes(self._json_payload(payload))
            results = self._ensure_directory("results")
            for name in FINAL_NAMES:
                if (results / name).exists() or (results / name).is_symlink():
                    raise BrokerError("final_locked", "this arm already has a finalization lock")
            digest = hashlib.sha256(content).hexdigest()
            # Reserve the lock first. A partial failure stays locked and auditable.
            for name, data in ((".final.lock", (digest + "\n").encode()),
                               ("final.json", content),
                               ("final.sha256", (digest + "  final.json\n").encode())):
                target = results / name
                with target.open("xb") as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                metrics["written_bytes"] += len(data)
                target.chmod(0o444)
            return {"path": "results/final.json", "sha256": digest}
        raise BrokerError("invalid_action", "unknown broker action")

    def _operand(self, value, case):
        if not value or "\x00" in value or "\\" in value:
            raise BrokerError("invalid_argv", "invalid file operand")
        candidate = Path(value)
        candidate = candidate if candidate.is_absolute() else self.root / "work" / candidate
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise BrokerError("path_escape", "process file operand leaves arm root")
        self._authorize_read(resolved, case)
        current = self.root
        # Check lexical ancestors as well as the resolved destination.
        try:
            parts = candidate.relative_to(self.root).parts
        except ValueError as exc:
            raise BrokerError("path_escape", "process file operand leaves arm root") from exc
        for part in parts:
            current /= part
            if current.is_symlink():
                raise BrokerError("symlink", "symlink process operands are forbidden")

    def _validate_argv(self, argv, case):
        if not isinstance(argv, list) or not argv or any(
                not isinstance(arg, str) or not arg or "\x00" in arg for arg in argv):
            raise BrokerError("invalid_argv", "argv must be a nonempty array of nonempty strings")
        command = argv[0]
        if "/" in command or "\\" in command:
            # Host-installed interpreters/compilers may be absolute executables.
            if not Path(command).is_absolute():
                self._operand(command, case)
            elif not any(Path(command).resolve().is_relative_to(Path(prefix))
                         for prefix in ("/usr/bin", "/usr/local/bin", "/bin", "/opt")):
                self._operand(command, case)
        elif shutil.which(command) is None:
            raise BrokerError("executable_missing", "executable is not on inherited PATH")
        executable = Path(command).name
        inline_interpreter = executable.startswith("python") or executable in {"node", "nodejs"}
        expect_path, skip_value = False, False
        path_flags = {"-o", "-I", "-L", "-MF", "-include", "--output", "--file", "--input"}
        for arg in argv[1:]:
            if skip_value:
                skip_value = False
                continue
            if inline_interpreter and arg in {"-c", "-e", "--eval", "-p", "--print", "-m"}:
                skip_value = True
                continue
            if expect_path:
                self._operand(arg, case)
                expect_path = False
                continue
            if arg in path_flags:
                expect_path = True
                continue
            value = arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg
            if arg.startswith(("-I", "-L", "-o")) and len(arg) > 2 and not arg.startswith("--"):
                value = arg[2:]
            if "/" in value or "\\" in value or value in {".", ".."} or (
                    not value.startswith("-") and
                    ((self.root / "work" / value).exists() or Path(value).suffix)):
                self._operand(value, case)
        if expect_path:
            raise BrokerError("invalid_argv", "file flag is missing its operand")

    def _run(self, request, request_id, case, metrics):
        if not isinstance(request, dict):
            raise BrokerError("invalid_run", "run requires an object with argv")
        argv = request.get("argv")
        self._validate_argv(argv, case)
        timeout = request.get("timeout", MAX_TIMEOUT)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= MAX_TIMEOUT:
            raise BrokerError("invalid_timeout", "timeout must be greater than zero and at most 60 seconds")
        work = self._ensure_directory("work")
        self._ensure_directory("results/runs")
        self._snapshot(request_id, "before", case, metrics)
        run_start = time.monotonic_ns()
        error_code = None
        try:
            # A separate session makes timeout cleanup include native descendants.
            # Popen is required because subprocess.run does not expose the group PID.
            with subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  start_new_session=True, shell=False) as process:
                metrics["pid"] = metrics["process_group"] = process.pid
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    code = process.returncode
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        metrics["group_kill_sent"] = True
                    except ProcessLookupError:
                        metrics["group_kill_sent"] = False
                    stdout, stderr = process.communicate()
                    code, error_code = 124, "timeout"
                finally:
                    # Also prevent ordinary background children from mutating a
                    # completed invocation after its post-run snapshot.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        metrics["group_kill_sent"] = True
                    except ProcessLookupError:
                        metrics.setdefault("group_kill_sent", False)
                    process.wait()
        except OSError as exc:
            stdout, stderr, code = b"", str(exc).encode("utf-8"), 127
            error_code = "process_start_failed"
        run_seconds = (time.monotonic_ns() - run_start) / 1e9
        metrics.update(output_bytes=len(stdout) + len(stderr), stdout_bytes=len(stdout),
                       stderr_bytes=len(stderr), run_seconds=run_seconds, process_exit=code)
        paths, retention_failure = {}, None
        try:
            for label, content in (("stdout", stdout), ("stderr", stderr)):
                # Retain immutable output even if a later process mutates results/runs.
                metrics[label + "_artifact"] = self._blob(content, metrics)
                relative = f"results/runs/{request_id}.{label}"
                target = self._path(relative, writable=True)
                with target.open("xb") as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
                metrics["written_bytes"] += len(content)
                paths[label + "_path"] = relative
        except (BrokerError, OSError) as exc:
            retention_failure = exc if isinstance(exc, BrokerError) else BrokerError("retention_failed", str(exc))
        # Preserve subprocess mutations even when the child or output storage failed.
        try:
            self._snapshot(request_id, "after", case, metrics)
        except (BrokerError, OSError) as exc:
            retention_failure = exc if isinstance(exc, BrokerError) else BrokerError("snapshot_failed", str(exc))
        stdout_text, stderr_text = stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
        displayed_stdout = stdout_text[:DISPLAY_LIMIT]
        displayed_stderr = stderr_text[:max(0, DISPLAY_LIMIT - len(displayed_stdout))]
        result = {"ok": code == 0, "exit": code, **paths,
                  "stdout": displayed_stdout, "stderr": displayed_stderr,
                  "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
                  "truncated": len(stdout_text) + len(stderr_text) > DISPLAY_LIMIT,
                  "timeout_seconds": timeout, "run_seconds": run_seconds}
        if error_code:
            result.update(error_code=error_code, error="process exceeded timeout" if code == 124 else "process could not start")
        elif code:
            result.update(error_code="process_failed", error="process exited unsuccessfully")
        if retention_failure:
            result.update(ok=False, exit=1, process_exit=code, error_code=retention_failure.code,
                          error=str(retention_failure))
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-root", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("action")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args(argv)
    payload = sys.stdin.buffer.read() if args.action in {"write", "run", "finalize"} else b""
    try:
        response, code = Broker(args.arm_root).request(args.action, args.case, path=args.path, payload=payload)
    except (OSError, BrokerError) as exc:
        response, code = {"ok": False, "error_code": "invalid_root", "error": str(exc), "exit": 1}, 1
    sys.stdout.buffer.write(json_bytes(response))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
