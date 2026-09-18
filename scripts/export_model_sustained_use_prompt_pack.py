#!/usr/bin/env python3
"""Export a frozen prompt pack for the first external-model sustained-use pilot."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_model_sustained_use_eval.py"
_SPEC = importlib.util.spec_from_file_location("_model_sustained_use_runner", RUNNER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load {RUNNER}")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MOD
_SPEC.loader.exec_module(_MOD)


def build_verified_bank():
    bank = []
    seen = set()
    for raw in _MOD.TRAIN_TASKS:
        task = _MOD.Task(*raw)
        table = _MOD.KNOWN_TABLES[task.deterministic_table_name]
        checked = _MOD.check_finite_countermodel(task.source, task.target, table)
        if not checked.terminal_candidate_ok:
            raise RuntimeError(f"fixed capability failed verification: {task.task_id}")
        cid = _MOD._table_id(table)
        if cid in seen:
            continue
        seen.add(cid)
        bank.append(
            _MOD.Capability(
                capability_id=cid,
                table=_MOD.normalize_table(table),
                source_task_id=task.task_id,
                behavior_signature=_MOD._signature(table),
                verifier_evidence={
                    "terminal_candidate_ok": True,
                    "source_equation": task.source,
                    "target_equation": task.target,
                    "witness_env": dict(checked.witness_env),
                    "origin": "preauthorized_fixed_bank_v1",
                },
            )
        )
    return bank


def request_rows(bank):
    rows = []
    for task in _MOD._tasks(_MOD.FRESH_TASKS):
        supporting = _MOD._supporting_ids(task, bank)
        ablated = [cap for cap in bank if cap.capability_id not in supporting]
        conditions = {
            "cold": [],
            "warm": list(bank),
            "restart": list(bank),
            "sham": list(bank),
            "ablation": ablated,
        }
        for mode, visible_bank in conditions.items():
            prompt = _MOD._prompt(task, mode, visible_bank)
            rows.append(
                {
                    "request_id": f"{mode}:{task.task_id}",
                    "mode": mode,
                    "task_id": task.task_id,
                    "task": {
                        "source": task.source,
                        "target": task.target,
                    },
                    "capability_bank": [cap.public_summary() for cap in visible_bank],
                    "prompt": prompt,
                    "response_contract": {
                        "accepted_candidate_forms": [
                            {"table": "square integer matrix"},
                            {"reuse_id": "capability_id from visible capability_bank"},
                        ],
                        "no_prose": True,
                    },
                }
            )
    return rows


def sha256_json(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="/tmp/open_math_model_sustained_use_v1/external_prompt_pack",
    )
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bank = build_verified_bank()
    bank_json = [cap.to_dict() for cap in bank]
    rows = request_rows(bank)

    bank_path = out / "preauthorized_verified_bank.json"
    requests_path = out / "requests.jsonl"
    manifest_path = out / "manifest.json"

    bank_path.write_text(json.dumps(bank_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    requests_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "protocol": "MATHGRAPH_EXTERNAL_MODEL_PROMPT_PACK_V1",
        "bank_capability_count": len(bank),
        "request_count": len(rows),
        "fresh_task_count": len(_MOD.FRESH_TASKS),
        "conditions": ["cold", "warm", "restart", "sham", "ablation"],
        "bank_sha256": sha256_json(bank_json),
        "requests_sha256": hashlib.sha256(requests_path.read_bytes()).hexdigest(),
        "claim_boundary": (
            "This pack contains prompts and independently verified reusable capabilities only. "
            "It contains no external-model result. A model run becomes evidence only after its "
            "frozen transcript is replayed through run_model_sustained_use_eval.py."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        **manifest,
        "bank_path": str(bank_path),
        "requests_path": str(requests_path),
        "manifest_path": str(manifest_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
