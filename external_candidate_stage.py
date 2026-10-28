"""Stage a model-authored Python function as untrusted bytes outside source.

This module never imports or executes candidate code, runs tests, or authorizes it.
"""

import ast
from hashlib import sha256
from pathlib import Path
import subprocess
import textwrap


def stage_function_candidate(*, root, expected_head, source_file, expected_sha256,
                             qualified_name, function_source, destination):
    root = Path(root).resolve()
    source_path = (root / source_file).resolve()
    output_path = Path(destination).resolve()
    if not source_path.is_relative_to(root):
        raise ValueError("SOURCE_PATH_ESCAPE")
    if output_path.is_relative_to(root):
        raise ValueError("STAGING_MUST_BE_OUTSIDE_SOURCE")
    if output_path.exists():
        raise ValueError("STAGING_OUTPUT_ALREADY_EXISTS")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                   text=True).strip()
    if head != expected_head:
        raise ValueError("SOURCE_HEAD_MISMATCH")
    raw = source_path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("SOURCE_FILE_HASH_MISMATCH")
    if not isinstance(function_source, str) or len(function_source.encode()) > 12000:
        raise ValueError("INVALID_FUNCTION_SOURCE")
    try:
        candidate_tree = ast.parse(function_source)
        original_tree = ast.parse(raw)
    except (SyntaxError, UnicodeError, ValueError):
        raise ValueError("INVALID_PYTHON_SYNTAX") from None

    if (len(candidate_tree.body) != 1 or
            not isinstance(candidate_tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef))):
        raise ValueError("PROPOSAL_NOT_SINGLE_FUNCTION")
    proposed = candidate_tree.body[0]
    if proposed.decorator_list:
        raise ValueError("PROPOSAL_DECORATORS_FORBIDDEN")

    parts = qualified_name.split(".")
    nodes = [original_tree]
    for index, part in enumerate(parts):
        eligible = (ast.FunctionDef, ast.AsyncFunctionDef) if index == len(parts) - 1 else ast.ClassDef
        nodes = [child for node in nodes for child in node.body
                 if isinstance(child, eligible) and child.name == part]
    if len(nodes) != 1 or proposed.name != parts[-1]:
        raise ValueError("TARGET_FUNCTION_NOT_UNIQUE")
    target = nodes[0]
    # The target's original decorator lines are outside the replaced def span.
    # Preserve them verbatim; never accept new decorators from model output.
    if type(target) is not type(proposed):
        raise ValueError("FUNCTION_KIND_MISMATCH")

    source_lines = raw.decode("utf8").splitlines(keepends=True)
    indentation = source_lines[target.lineno - 1][:target.col_offset]
    candidate = textwrap.indent(function_source.strip("\n") + "\n", indentation)
    candidate_lines = source_lines[:target.lineno - 1] + [candidate] + source_lines[target.end_lineno:]
    staged = "".join(candidate_lines).encode("utf8")
    try:
        ast.parse(staged)
    except SyntaxError:
        raise ValueError("STAGED_SOURCE_INVALID_SYNTAX") from None

    # A concurrent source revision cannot silently inherit an old staging receipt.
    actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                          text=True).strip()
    if actual_head != expected_head or sha256(source_path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("SOURCE_CHANGED_DURING_STAGING")
    output_path.write_bytes(staged)
    return {"status": "STAGED_UNTRUSTED_NOT_EXECUTED", "source_head": expected_head,
            "source_file": source_file, "source_sha256": expected_sha256,
            "qualified_name": qualified_name, "candidate_sha256": sha256(staged).hexdigest()}
