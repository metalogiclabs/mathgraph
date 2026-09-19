from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = Path(os.environ.get("CROSS_REP_SOURCE_ROOT", "_vendor/cross_representation_source"))
SOURCE_FILE = SOURCE_ROOT / "experiments/verified_cross_representation_compounding_v1/run.py"

SOURCE_RUN = 34603649113
SOURCE_COMMIT = "feb55aad0ab80fb9c51110367c3cc34869764dd0"
SOURCE_ARTIFACT = 10265656833
SOURCE_ARTIFACT_DIGEST = "sha256:86e7dc456daae4da807b2b6cac87a2659c2dfe88c526dab6607565ef17e8b7d9"
ARRIVAL_AFTER_COLD_DEPTH = 6


def _load_source():
    spec = importlib.util.spec_from_file_location("cross_rep_source", SOURCE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned source: {SOURCE_FILE}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cold_prefix(mod, max_depth: int) -> dict:
    calls = nodes = evals = 0
    wins = []
    for depth in range(1, max_depth + 1):
        level = []
        for program in itertools.product(mod.TARGET, repeat=depth):
            nodes += 1
            r = mod.execute(program)
            calls += r["calls"]
            evals += r["evaluations"]
            if r["valid"] and r["success"]:
                level.append(program)
        if level:
            wins = level
            return {
                "correct": True,
                "verifier_calls": calls,
                "search_nodes": nodes,
                "candidate_evaluations": evals,
                "success_depth": depth,
                "canonical_success": list(min(level)),
            }
    return {
        "correct": False,
        "verifier_calls": calls,
        "search_nodes": nodes,
        "candidate_evaluations": evals,
        "success_depth": None,
        "canonical_success": None,
    }


def incremental_macro_search(mod, macro, adapter_calls: int, max_depth: int = 7) -> dict:
    alphabet = mod.TARGET + ("XFER",)
    calls = adapter_calls
    nodes = evals = 0
    for depth in range(1, max_depth + 1):
        level = []
        for program in itertools.product(alphabet, repeat=depth):
            # All target-only programs through depth 6 have already been evaluated.
            # After the event, only programs whose semantics changed are new work.
            if "XFER" not in program:
                continue
            nodes += 1
            r = mod.execute(program, macro)
            calls += r["calls"]
            evals += r["evaluations"]
            if r["valid"] and r["success"]:
                level.append(program)
        if level:
            return {
                "correct": True,
                "verifier_calls": calls,
                "search_nodes": nodes,
                "candidate_evaluations": evals,
                "success_depth": depth,
                "canonical_success": list(min(level)),
                "adapter_calls": adapter_calls,
            }
    return {
        "correct": False,
        "verifier_calls": calls,
        "search_nodes": nodes,
        "candidate_evaluations": evals,
        "success_depth": None,
        "canonical_success": None,
        "adapter_calls": adapter_calls,
    }


def arm_from_parts(name: str, prefix: dict, suffix: dict | None, fallback: dict | None = None) -> dict:
    if suffix is None:
        assert fallback is not None
        return {
            "arm": name,
            "correct": fallback["correct"],
            "verifier_calls": fallback["verifier_calls"],
            "search_nodes": fallback["search_nodes"],
            "candidate_evaluations": fallback["candidate_evaluations"],
            "success_depth": fallback["success_depth"],
            "canonical_success": fallback["canonical_success"],
            "cold_prefix_calls": prefix["verifier_calls"],
            "post_event_calls": fallback["verifier_calls"] - prefix["verifier_calls"],
        }
    return {
        "arm": name,
        "correct": suffix["correct"],
        "verifier_calls": prefix["verifier_calls"] + suffix["verifier_calls"],
        "search_nodes": prefix["search_nodes"] + suffix["search_nodes"],
        "candidate_evaluations": prefix["candidate_evaluations"] + suffix["candidate_evaluations"],
        "success_depth": suffix["success_depth"],
        "canonical_success": suffix["canonical_success"],
        "cold_prefix_calls": prefix["verifier_calls"],
        "post_event_calls": suffix["verifier_calls"],
        "adapter_calls": suffix["adapter_calls"],
    }


def run() -> dict:
    mod = _load_source()

    compiled, adapter_calls, certs = mod.compile_by_equivalence(mod.SOURCE_D2)
    sham_compiled, sham_adapter_calls, sham_certs = mod.compile_by_equivalence(("TEMPORAL",))
    if compiled is None or sham_compiled is None:
        raise RuntimeError("frozen behavioral compilation failed")

    prefix = cold_prefix(mod, ARRIVAL_AFTER_COLD_DEPTH)
    cold = mod.search()
    upfront = mod.search(("XFER",), compiled, adapter_calls)

    flash_suffix = incremental_macro_search(mod, compiled, adapter_calls)
    sham_suffix = incremental_macro_search(mod, sham_compiled, sham_adapter_calls)

    flash = arm_from_parts("FLASH", prefix, flash_suffix)
    sham = arm_from_parts("SHAM_REDUNDANT_MACRO", prefix, sham_suffix)
    raw = arm_from_parts("RAW_HISTORY", prefix, None, cold)
    ablation = arm_from_parts("ABLATION", prefix, None, cold)
    answer_memory = arm_from_parts("ANSWER_MEMORY_ONLY", prefix, None, cold)

    arms = {
        "COLD": {
            "arm": "COLD",
            **cold,
            "cold_prefix_calls": prefix["verifier_calls"],
            "post_event_calls": cold["verifier_calls"] - prefix["verifier_calls"],
        },
        "UPFRONT": {
            "arm": "UPFRONT",
            **upfront,
            "cold_prefix_calls": 0,
            "post_event_calls": upfront["verifier_calls"],
        },
        "FLASH": flash,
        "RAW_HISTORY": raw,
        "ABLATION": ablation,
        "SHAM_REDUNDANT_MACRO": sham,
        "ANSWER_MEMORY_ONLY": answer_memory,
    }

    avoided = cold["verifier_calls"] - flash["verifier_calls"]
    gates = {
        "source_surface_disjoint": not set(mod.SOURCE).intersection(mod.TARGET),
        "cold_depth6_unsolved": prefix["correct"] is False,
        "cold_prefix_calls_35290": prefix["verifier_calls"] == 35290,
        "cold_full_calls_222808": cold["verifier_calls"] == 222808,
        "upfront_calls_320": upfront["verifier_calls"] == 320,
        "flash_calls_35602": flash["verifier_calls"] == 35602,
        "flash_post_event_calls_312": flash["post_event_calls"] == 312,
        "flash_avoids_187206": avoided == 187206,
        "flash_strictly_better_than_cold": flash["verifier_calls"] < cold["verifier_calls"],
        "upfront_strictly_better_than_flash": upfront["verifier_calls"] < flash["verifier_calls"],
        "ablation_restores_cold": ablation["verifier_calls"] == cold["verifier_calls"],
        "raw_history_restores_cold": raw["verifier_calls"] == cold["verifier_calls"],
        "answer_memory_restores_cold": answer_memory["verifier_calls"] == cold["verifier_calls"],
        "sham_does_not_reproduce": sham["verifier_calls"] > cold["verifier_calls"],
        "valid_macro_compiled_uniquely": len(certs) == len(mod.SOURCE_D2),
        "sham_macro_compiled_uniquely": len(sham_certs) == 1,
        "all_terminal_arms_correct": all(row["correct"] for row in arms.values()),
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.cross-representation-flash.v1",
        "source_authority": {
            "run_id": SOURCE_RUN,
            "commit": SOURCE_COMMIT,
            "artifact_id": SOURCE_ARTIFACT,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "source_program": list(mod.SOURCE_D2),
            "compiled_target_macro": list(compiled),
            "adapter_calls": adapter_calls,
        },
        "schedule": {
            "target_begins_cold": True,
            "arrival_after_completed_cold_depth": ARRIVAL_AFTER_COLD_DEPTH,
            "cold_prefix_verifier_calls": prefix["verifier_calls"],
            "cold_prefix_search_nodes": prefix["search_nodes"],
        },
        "arms": arms,
        "avoided_verifier_calls": avoided,
        "avoided_fraction": avoided / cold["verifier_calls"],
        "gates": gates,
        "scientific_verdict": (
            "PASS_LIVE_CROSS_REPRESENTATION_FLASH"
            if gates["pass"]
            else "FAIL_CROSS_REPRESENTATION_FLASH"
        ),
        "boundary": (
            "Bounded exhaustive live transfer through a supplied typed behavioral interface. "
            "The target surface vocabulary is disjoint and the target completes cold levels 1-6 "
            "before the verified source procedure arrives. This does not establish learned adapter "
            "discovery, natural-domain transfer, unbounded compounding, or universal Flash."
        ),
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main():
    result = run()
    (ROOT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("CROSS_REPRESENTATION_FLASH_V1=" + result["scientific_verdict"])
    print("COSTS=" + json.dumps({k: v["verifier_calls"] for k, v in result["arms"].items()}, sort_keys=True))
    print("AVOIDED_VERIFIER_CALLS=" + str(result["avoided_verifier_calls"]))
    print("AVOIDED_FRACTION=" + f'{result["avoided_fraction"]:.9f}')
    print("DIGEST_SHA256=" + result["digest_sha256"])
    if not result["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
