#!/usr/bin/env python3
"""Unmodified, pinned C versus Rust native execution, with bounded evidence.

All compilation wrappers are external to the frozen upstream source files.
This is differential finite testing, not a proof of full ACSL refinement.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

from cohort import full_population, contract_output, mutants, mutant_output, review_one, synthesize_minimum_probes
from reference import conventional_verdict

HERE = Path(__file__).resolve().parent
LOCK = HERE / "LOCK.json"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def check_pin(data: bytes, expected: str) -> str:
    measured = git_blob_sha(data)
    if measured != expected:
        raise ValueError(f"PIN_MISMATCH expected={expected} actual={measured}")
    return measured


def grade_native_row(case: str, row: tuple[int, ...],
                     source: tuple[int, ...] | None,
                     target: tuple[int, ...] | None) -> str:
    return review_one(case, row, {
        "source_pin_ok": True, "target_pin_ok": True,
        "contract_active": True, "native_source": source,
        "native_target": target,
    })


def parse_native_rows(stdout: str, rows: list[tuple[int, ...]],
                      columns: int) -> list[tuple[int, ...]]:
    lines = stdout.splitlines()
    if len(lines) != len(rows):
        raise ValueError(f"NATIVE_ROW_COUNT expected={len(rows)} actual={len(lines)}")
    result = []
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) != columns:
            raise ValueError(f"NATIVE_ROW_WIDTH index={i} expected={columns} actual={len(parts)}")
        try:
            result.append(tuple(int(token) for token in parts))
        except ValueError as error:
            raise ValueError(f"NATIVE_ROW_NOT_INTEGER index={i}") from error
    return result


# The wrappers only provide controlled separate storage, input/output, and
# function entry points. Original C/Rust bytes remain unchanged on disk.
C_SIGNATURES = {
    "conditional_reset": "void reset_1st_if_2nd_is_true(int*, const int*);",
    "vector_addition": "void vec_add(int*, const int*, size_t);",
    "search_replace": "void search_and_replace(int*, size_t, int, int);",
}
C_RUN = {
    "conditional_reset": """
int a,b;
while (scanf("%d %d", &a, &b) == 2) {
    reset_1st_if_2nd_is_true(&a,&b);
    printf("%d %d\\n",a,b);
}
""",
    "vector_addition": """
int len,a[3],b[3];
while (scanf("%d %d %d %d %d %d %d", &len,&a[0],&a[1],&a[2],&b[0],&b[1],&b[2]) == 7) {
    if(len<0 || len>3) return 3;
    vec_add(a,b,(size_t)len);
    printf("%d %d %d %d %d %d\\n",a[0],a[1],a[2],b[0],b[1],b[2]);
}
""",
    "search_replace": """
int len,a[3],old_value,new_value;
while (scanf("%d %d %d %d %d %d", &len,&a[0],&a[1],&a[2],&old_value,&new_value) == 6) {
    if(len<0 || len>3) return 3;
    search_and_replace(a,(size_t)len,old_value,new_value);
    printf("%d %d %d\\n",a[0],a[1],a[2]);
}
""",
}
RUST_RUN = {
    "conditional_reset": """
pub fn apply(row: &mut [i32]) {
    let mut a = row[0];
    let b = row[1];
    reset_1st_if_2nd_is_true(&mut a,&b);
    row[0] = a;
}
""",
    "vector_addition": """
pub fn apply(row: &mut [i32]) {
    let n = row[0] as usize;
    assert!(n <= 3);
    let (left,right) = row[1..].split_at_mut(3);
    vec_add(left,right,n);
}
""",
    "search_replace": """
pub fn apply(row: &mut [i32]) {
    let n = row[0] as usize;
    assert!(n <= 3);
    let old_value = row[4];
    let new_value = row[5];
    search_and_replace(&mut row[1..4],n,old_value,new_value);
}
""",
}


def c_wrapper(case: str) -> str:
    return ("#include <stdio.h>\n#include <stddef.h>\n" + C_SIGNATURES[case]
            + "\nint main(void){\n" + C_RUN[case] + "return 0;\n}\n")


def rust_wrapper(case: str) -> str:
    return ("#![allow(dead_code,unused_variables)]\nmod original {\n"
            + 'include!(env!("RUST_TARGET_FILE"));\n' + RUST_RUN[case]
            + "}\nuse std::io::{self,Read};\n"
            + "fn main() {\n let mut text=String::new();\n"
            + " io::stdin().read_to_string(&mut text).unwrap();\n"
            + " for line in text.lines(){\n"
            + "  let mut row: Vec<i32>=line.split_whitespace().map(|x| x.parse().unwrap()).collect();\n"
            + f"  assert_eq!(row.len(),{2 if case=='conditional_reset' else 7 if case=='vector_addition' else 6});\n"
            + "  original::apply(&mut row);\n"
            + ("  let output=&row[..];\n" if case == "conditional_reset"
               else "  let output=&row[1..4];\n" if case == "search_replace"
               else "  let output=&row[1..];\n")
            + "  println!(\"{}\",output.iter().map(|x|x.to_string()).collect::<Vec<_>>().join(\" \"));\n"
            + " }\n}\n")


def command(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True, timeout=90, **kwargs)
    if result.returncode:
        raise RuntimeError(f"NATIVE_COMMAND_FAILED cmd={args[0]} exit={result.returncode} "
                           f"stderr={result.stderr[:2000]}")
    return result


def obtain_pinned(lock: dict, case: dict, root: Path) -> tuple[Path, Path]:
    paths = []
    for kind, extension in (("source", ".c"), ("target", ".rs")):
        repo_path = case[f"{kind}_path"]
        url = ("https://raw.githubusercontent.com/" + lock["source_repository"] + "/"
               + lock["source_commit"] + "/" + repo_path)
        with urlopen(url, timeout=30) as response:
            data = response.read()
        check_pin(data, case[f"{kind}_git_blob"])
        dest = root / f"{case['id']}-{kind}{extension}"
        dest.write_bytes(data)  # Temporary exact upstream download, never altered.
        paths.append(dest)
    return paths[0], paths[1]


def native_outputs(case: str, source: Path, target: Path,
                   rows: list[tuple[int, ...]], root: Path
                  ) -> tuple[list[tuple[int, ...]], list[tuple[int, ...]]]:
    c_wrapper_path = root / f"{case}-external.c"
    c_wrapper_path.write_text(c_wrapper(case))
    rust_wrapper_path = root / f"{case}-external.rs"
    rust_wrapper_path.write_text(rust_wrapper(case))
    original_object = root / f"{case}-original.o"
    c_binary = root / f"{case}-c"
    rust_binary = root / f"{case}-rust"
    command(["gcc", "-std=c11", "-O0", "-Dmain=upstream_original_main", "-c",
             str(source), "-o", str(original_object)])
    command(["gcc", "-std=c11", "-O0", str(c_wrapper_path), str(original_object),
             "-o", str(c_binary)])
    env = dict(os.environ, RUST_TARGET_FILE=str(target.resolve()))
    command(["rustc", "--edition=2021", "-C", "opt-level=0", str(rust_wrapper_path),
             "-o", str(rust_binary)], env=env)
    stdin = "".join(" ".join(map(str, row)) + "\n" for row in rows)
    native_c = command([str(c_binary)], input=stdin)
    native_rust = command([str(rust_binary)], input=stdin)
    widths = {"conditional_reset": 2, "vector_addition": 6, "search_replace": 3}
    return (parse_native_rows(native_c.stdout, rows, widths[case]),
            parse_native_rows(native_rust.stdout, rows, widths[case]))


def evaluate(output_dir: Path) -> dict:
    lock = json.loads(LOCK.read_text())
    population = full_population()
    expected = lock["expected_counts"]
    if {k: len(v) for k, v in population.items()} != {k: expected[k] for k in population}:
        raise ValueError("COHORT_DEVIATES_FROM_FROZEN_POPULATION")
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    transcript_path = output_dir / "native-transcript.jsonl"
    with tempfile.TemporaryDirectory(prefix="pinned-native-") as d:
        with transcript_path.open("w") as transcript:
            for c in lock["cases"]:
                case = c["id"]
                rows = population[case]
                c_path, rust_path = obtain_pinned(lock, c, Path(d))
                c_out, rust_out = native_outputs(case, c_path, rust_path, rows, Path(d))
                verdicts = []
                baseline = []
                for row, source_output, target_output in zip(rows, c_out, rust_out):
                    decision = grade_native_row(case, row, source_output, target_output)
                    independent = conventional_verdict(case, row, source_output, target_output)
                    verdicts.append(decision)
                    baseline.append(independent)
                    transcript.write(json.dumps({
                        "case": case, "input": row, "c": source_output,
                        "rust": target_output, "declared_contract": contract_output(case, row),
                        "mathgraph_verdict": decision, "independent_verdict": independent,
                        "source_git_blob": c["source_git_blob"],
                        "target_git_blob": c["target_git_blob"],
                    }, sort_keys=True) + "\n")
                mutation_witnesses = {}
                for name in mutants(case):
                    witnesses = [i for i, row in enumerate(rows) if
                                 conventional_verdict(case, row, c_out[i],
                                                      mutant_output(case, name, row))
                                 == "DEMONSTRATED_DEFECT"]
                    if not witnesses:
                        raise AssertionError(f"MUTANT_ESCAPED {case}/{name}")
                    mutation_witnesses[name] = {"detected": True, "witness_count": len(witnesses),
                                                "first_input": rows[witnesses[0]]}
                if verdicts != baseline:
                    raise AssertionError(f"DISAGREEMENT_WITH_CONVENTIONAL {case}")
                summaries.append({
                    "case": case, "population": len(rows),
                    "native_c_contract_matches": verdicts.count("WARRANTED_BOUNDED_MATCH")
                        + verdicts.count("DEMONSTRATED_DEFECT"),
                    "native_target_matches": verdicts.count("WARRANTED_BOUNDED_MATCH"),
                    "source_contract_disagreements": verdicts.count("SOURCE_CONTRACT_DISAGREEMENT"),
                    "target_defects": verdicts.count("DEMONSTRATED_DEFECT"),
                    "mutation_controls": mutation_witnesses,
                    "conventional_comparator": "EXACT_AGREEMENT_SAME_INFORMATION",
                })
    probes = synthesize_minimum_probes("conditional_reset")
    controls = {
        "wrong_source_pin": "UNKNOWN_SOURCE_AUTHORITY",
        "wrong_target_pin": "UNKNOWN_SOURCE_AUTHORITY",
        "withdrawn_contract": "UNKNOWN_SOURCE_AUTHORITY",
        "missing_native_receipt": "UNKNOWN_NATIVE_OBSERVATION",
    }
    # Exercise control transitions against one actual native receipt shape.
    input_example = (3, 1)
    exemplar = (0, 1)
    for key, attr in (("wrong_source_pin", "source_pin_ok"),
                      ("wrong_target_pin", "target_pin_ok"),
                      ("withdrawn_contract", "contract_active")):
        evidence = {"source_pin_ok": True, "target_pin_ok": True,
                    "contract_active": True, "native_source": exemplar,
                    "native_target": exemplar}
        evidence[attr] = False
        assert review_one("conditional_reset", input_example, evidence) == controls[key]
    assert grade_native_row("conditional_reset", input_example, exemplar, None) == controls["missing_native_receipt"]
    total = sum(x["population"] for x in summaries)
    failures = sum(x["target_defects"]+x["source_contract_disagreements"] for x in summaries)
    return {
        "status": "WARRANTED_BOUNDED_SOURCE_TARGET_MATCH" if failures == 0
                  else "OBSERVED_SOURCE_OR_TARGET_DISAGREEMENT",
        "lock_commit": "126bc8f5d3ca5958aad0f6d2dfa95da11ec68e77",
        "upstream_source_commit": lock["source_commit"],
        "total_native_rows": total, "cases": summaries,
        "negative_control_witnesses": sum(len(x["mutation_controls"]) for x in summaries),
        "positive_control_matches": total - failures,
        "withdrawal_controls": controls,
        "reset_minimum_probes": {k: probes[k] for k in
                                 ("status", "basis_cost", "conventional_minimum_cost", "relative_result")},
        "comparison": "BASELINE_TIE: independent conventional source-aware checker agrees with every native verdict",
        "novel_sensor_invention": "UNKNOWN_NOT_EXHIBITED",
        "action_authority": False,
        "verification_boundary": "Pinned exact C/Rust upstream files; original bytes; native gcc/rustc; 1189 finite vectors; no universal refinement or human-intent claim",
        "artifact": str(transcript_path.name),
    }


def main() -> int:
    output = Path("out/prospective_triangulation_v1")
    output.mkdir(parents=True, exist_ok=True)
    try:
        result = evaluate(output)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, TimeoutError) as exc:
        result = {"status": "UNKNOWN_NATIVE_OR_PIN_BOUNDARY",
                  "failure_type": type(exc).__name__, "failure": str(exc)[:2000],
                  "action_authority": False}
    (output / "report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PROSPECTIVE_TRIANGULATION_RESULT=" + json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "WARRANTED_BOUNDED_SOURCE_TARGET_MATCH" else 1


if __name__ == "__main__":
    sys.exit(main())
