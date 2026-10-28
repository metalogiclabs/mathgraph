"""One external-task pilot; NOT a matched comparative efficacy experiment.

The evaluate subcommand must run only in a disposable runner with no secrets.
"""

import argparse
import ast
from dataclasses import asdict
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


EXPECTED_HEAD = "b79088306513d5ed76d31ac40ab3c15f858946ea"
TASK_ID = "django__django-13512"
SOURCE_FILE = "django/forms/fields.py"
EXPECTED_SHA256 = "7e2675d83e075f0ccb252abfefc13efe853c5ac9ed4c36c9581c8f5c15db4dcf"
ISSUE = ("Django JSONField form values should render non-ASCII Unicode characters "
         "without JSON Unicode escape sequences; preserve JSON validity and invalid input handling.")


def source_task(root, expected_head=EXPECTED_HEAD):
    root = Path(root)
    actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                          text=True).strip()
    if actual_head != expected_head:
        raise ValueError("SOURCE_HEAD_MISMATCH")
    source = (root / SOURCE_FILE).read_bytes()
    digest = sha256(source).hexdigest()
    if expected_head == EXPECTED_HEAD and digest != EXPECTED_SHA256:
        raise ValueError("SOURCE_FILE_HASH_MISMATCH")
    tree = ast.parse(source)
    methods = [child for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "JSONField" for child in node.body
               if isinstance(child, ast.FunctionDef) and child.name == "prepare_value"]
    if len(methods) != 1:
        raise ValueError("TARGET_FUNCTION_NOT_UNIQUE")
    function_excerpt = ast.get_source_segment(source.decode(), methods[0])
    return ExternalTask(task_id=TASK_ID, source_repo="django/django",
                        source_commit=expected_head, source_file=SOURCE_FILE,
                        source_file_sha256=digest, issue=ISSUE,
                        function_excerpt=function_excerpt)


def evaluate_candidate(root, input_path, output_path, arm="source_bound"):
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
    with TemporaryDirectory() as temp:
        staged = Path(temp) / "candidate.py"
        metadata = stage_function_candidate(
            root=root, expected_head=task.source_commit,
            source_file=SOURCE_FILE, expected_sha256=task.source_file_sha256,
            qualified_name="JSONField.prepare_value",
            function_source=proposal["function_source"], destination=staged)
        source_mutated_during_run = False
        try:
            shutil.copyfile(staged, target)
            env = {key: value for key, value in os.environ.items()
                   if key not in ("NEBIUS_API_KEY", "GITHUB_TOKEN", "GH_TOKEN")}
            env["PYTHONPATH"] = str(root)
            process = subprocess.run(
                [sys.executable, "-c", (
                    "import json\n"
                    "from django.forms.fields import JSONField\n"
                    "field = JSONField()\n"
                    "cases = [({'name': '中国'}, '中国'), "
                    "({'emoji': '🙂', 'items': ['café']}, '🙂'), "
                    "(['東京', '¿'], '東京'), ({'ascii': 'ok'}, 'ok')]\n"
                    "for value, literal in cases:\n"
                    "    encoded = field.prepare_value(value)\n"
                    "    assert isinstance(encoded, str)\n"
                    "    assert json.loads(encoded) == value\n"
                    "    assert literal in encoded\n"
                    "print('MULTICASE_NATIVE_ACCEPTANCE_PASSED')\n")],
                cwd=root, env=env, capture_output=True, timeout=30)
        finally:
            source_mutated_during_run = sha256(target.read_bytes()).hexdigest() != metadata["candidate_sha256"]
            target.write_bytes(original)
    output = process.stdout.decode("utf8", errors="replace")
    verdict = ("REJECTED_SOURCE_MUTATED_DURING_EVALUATION" if source_mutated_during_run
               else "WARRANTED_LOCAL_BOUNDED" if process.returncode == 0 and
               "MULTICASE_NATIVE_ACCEPTANCE_PASSED" in output else "REJECTED")
    receipt = {"arm": arm, "task_id": task.task_id, "source_commit": task.source_commit,
               "source_sha256": task.source_file_sha256,
               "candidate_sha256": metadata["candidate_sha256"],
               "exit_code": process.returncode,
               "stdout_sha256": sha256(process.stdout).hexdigest(),
               "stderr_sha256": sha256(process.stderr).hexdigest(),
               "requirement_verdict": verdict,
               "scope": "FOUR_VISIBLE_MULTICASE_UNICODE_PROBES_NO_GENERAL_CORRECTNESS_CLAIM"}
    Path(output_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def emit_no_result(arm, output_path):
    receipt = {"arm": arm, "task_id": TASK_ID,
               "requirement_verdict": "NO_RESULT",
               "reason": "INFERENCE_ARTIFACT_UNAVAILABLE"}
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
    args = parser.parse_args()
    if args.operation == "no-result":
        print("MISSING_ARM_RECEIPT", json.dumps(emit_no_result(args.arm, args.output)))
        return
    if not args.root:
        parser.error("--root required")
    if args.operation == "propose":
        task = source_task(args.root)
        suggestion = ExternalNemotronProposal(style=args.arm).propose(task)
        public = {"status": suggestion.status, "task_id": task.task_id,
                  "source_commit": task.source_commit,
                  "function_source": suggestion.function_source}
        Path(args.output).write_text(json.dumps(public, ensure_ascii=False) + "\n")
        print("UNVERIFIED_PROPOSAL_SHA256", suggestion.response_sha256)
    else:
        if not args.input:
            parser.error("--input required for evaluate")
        receipt = evaluate_candidate(args.root, args.input, args.output, arm=args.arm)
        print("EXTERNAL_PILOT_RECEIPT", json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
