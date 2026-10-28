"""Pinned external SymPy repair pilot; bounded evidence, no merge authority.

Run evaluations only in disposable workers without API credentials.
"""

import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from external_candidate_stage import stage_function_candidate
from external_model_proposal import ExternalNemotronProposal, ExternalTask


EXPECTED_HEAD = "f57fe3f4b3f2cab225749e1b3b38ae1bf80b62f0"
EXPECTED_SHA256 = "894be519b972e0c3ece8982cbd1f3022ad80bcc3f741a06aa97d68bd8daccbb7"
SOURCE_FILE = "sympy/functions/elementary/hyperbolic.py"
TASK_ID = "sympy__sympy-13480"
ISSUE = ("The historical SymPy expression coth(log(tan(x))).subs(x, 2) "
         "raises NameError: name 'cotm' is not defined. Repair the actual "
         "function without changing class decorators or unrelated methods.")
PROBE_CODE = (
    "import mpmath as mp\n"
    "from sympy import Symbol, coth, log, tan\n"
    "x = Symbol('x')\n"
    "for n in (2, 3):\n"
    "    result = complex(coth(log(tan(x))).subs(x,n).evalf(12))\n"
    "    oracle = complex(mp.coth(mp.log(mp.tan(n))))\n"
    "    assert abs(result - oracle) < 0.00001, (n, result, oracle)\n"
    "print('SYMPY_NATIVE_ACCEPTANCE_PASSED')\n")


def source_task(root, expected_head=EXPECTED_HEAD):
    root = Path(root).resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                   text=True).strip()
    if head != expected_head:
        raise ValueError("SOURCE_HEAD_MISMATCH")
    source = (root / SOURCE_FILE).read_bytes()
    digest = sha256(source).hexdigest()
    if expected_head == EXPECTED_HEAD and digest != EXPECTED_SHA256:
        raise ValueError("SOURCE_FILE_HASH_MISMATCH")
    parsed = ast.parse(source)
    targets = [method for node in parsed.body if isinstance(node, ast.ClassDef)
               and node.name == "coth" for method in node.body
               if isinstance(method, ast.FunctionDef) and method.name == "eval"]
    if len(targets) != 1:
        raise ValueError("TARGET_FUNCTION_NOT_UNIQUE")
    return ExternalTask(task_id=TASK_ID, source_repo="sympy/sympy",
                        source_commit=expected_head, source_file=SOURCE_FILE,
                        source_file_sha256=digest, issue=ISSUE,
                        function_excerpt=ast.get_source_segment(source.decode(), targets[0]))


def evaluate_candidate(root, input_path, output_path, runtime_python="python3.9", arm="source_bound"):
    if os.environ.get("NEBIUS_API_KEY"):
        raise RuntimeError("SECRET_PRESENT_IN_EVALUATION_JOB")
    root = Path(root).resolve()
    task = source_task(root, EXPECTED_HEAD)
    proposal = json.loads(Path(input_path).read_text())
    if (set(proposal) != {"task_id", "source_commit", "function_source", "status"}
            or proposal["task_id"] != task.task_id
            or proposal["source_commit"] != task.source_commit
            or proposal["status"] != "UNVERIFIED_PROPOSAL"):
        raise ValueError("PROPOSAL_IDENTITY_MISMATCH")
    target = root / SOURCE_FILE
    original = target.read_bytes()
    with TemporaryDirectory() as tmp:
        staged = Path(tmp) / "candidate.py"
        metadata = stage_function_candidate(
            root=root, expected_head=task.source_commit,
            source_file=SOURCE_FILE, expected_sha256=task.source_file_sha256,
            qualified_name="coth.eval", function_source=proposal["function_source"],
            destination=staged)
        changed = False
        try:
            shutil.copyfile(staged, target)
            env = {key: value for key, value in os.environ.items()
                   if key not in ("NEBIUS_API_KEY", "GITHUB_TOKEN", "GH_TOKEN")}
            env["PYTHONPATH"] = str(root)
            process = subprocess.run([runtime_python, "-c", PROBE_CODE], cwd=root,
                                     env=env, capture_output=True, timeout=40)
        finally:
            changed = sha256(target.read_bytes()).hexdigest() != metadata["candidate_sha256"]
            target.write_bytes(original)
    verdict = ("REJECTED_SOURCE_MUTATED_DURING_EVALUATION" if changed
               else "WARRANTED_LOCAL_BOUNDED" if process.returncode == 0 and
               b"SYMPY_NATIVE_ACCEPTANCE_PASSED" in process.stdout else "REJECTED")
    receipt = {"arm": arm, "task_id": TASK_ID, "source_commit": task.source_commit,
               "source_sha256": task.source_file_sha256,
               "candidate_sha256": metadata["candidate_sha256"],
               "exit_code": process.returncode,
               "stdout_sha256": sha256(process.stdout).hexdigest(),
               "stderr_sha256": sha256(process.stderr).hexdigest(),
               "requirement_verdict": verdict,
               "scope": "TWO_VISIBLE_NUMERIC_SUBSTITUTION_PROBES_NOT_FULL_SYMPY_TESTS"}
    Path(output_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("propose", "evaluate", "no-result"))
    parser.add_argument("--root")
    parser.add_argument("--input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--arm", choices=("source_bound", "conventional"),
                        default="source_bound")
    parser.add_argument("--runtime-python", default="python3.9")
    args = parser.parse_args()
    if args.operation == "no-result":
        receipt = {"arm": args.arm, "task_id": TASK_ID,
                   "requirement_verdict": "NO_RESULT", "reason": "INFERENCE_ARTIFACT_UNAVAILABLE"}
        Path(args.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print("SYMPY_PILOT_RECEIPT", json.dumps(receipt))
        return
    if not args.root:
        parser.error("--root required")
    if args.operation == "propose":
        task = source_task(args.root)
        proposal = ExternalNemotronProposal(style=args.arm).propose(task)
        public = {"status": proposal.status, "task_id": TASK_ID,
                  "source_commit": task.source_commit,
                  "function_source": proposal.function_source}
        Path(args.output).write_text(json.dumps(public, ensure_ascii=False) + "\n")
        print("UNVERIFIED_PROPOSAL_SHA256", proposal.response_sha256)
    else:
        if not args.input:
            parser.error("--input required")
        receipt = evaluate_candidate(args.root, args.input, args.output,
                                     runtime_python=args.runtime_python, arm=args.arm)
        print("SYMPY_PILOT_RECEIPT", json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
