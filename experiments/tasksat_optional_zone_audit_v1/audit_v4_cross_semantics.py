#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

tasksat_root = Path(sys.argv[1]).resolve()
lean_validator = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(tasksat_root / "src" / "smt"))

from tasknet_parser import parse_tasknet  # noqa: E402
from tasknet_smt import TaskNetTL  # noqa: E402

PIN = "f9d6063b45967a3fea578c47f54806aadaafe1b0"


def stock_sat(source: str) -> bool:
    tn = parse_tasknet(source)
    enc = TaskNetTL(tn, error_trace=False, use_optimization=False, track=False, portfolio=False)
    model, _ = enc.solve(analyze_core=False)
    return model is not None


def lean_task(
    task_id,
    kind,
    start_low,
    start_high,
    end_low,
    end_high,
    dur_low,
    dur_high,
    after=None,
):
    return {
        "id": task_id,
        "ident": 0,
        "priority": 0,
        "startrng": {"low": start_low, "high": start_high},
        "endrng": {"low": end_low, "high": end_high},
        "durrng": {"low": dur_low, "high": dur_high},
        "dur": max(0, dur_low),
        "start": max(0, start_low),
        "after": after or [],
        "containedin": [],
        "after_definitions": [],
        "containedin_definitions": [],
        "kind": kind,
        "pre": [],
        "inv": [],
        "post": [],
        "impacts": [],
    }


def lean_validate(tasknet, schedule):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tn_path = td / "tasknet.json"
        sch_path = td / "schedule.json"
        tn_path.write_text(json.dumps(tasknet))
        sch_path.write_text(json.dumps(schedule))
        p = subprocess.run(
            [str(lean_validator), "--tasknet", str(tn_path), "--schedule", str(sch_path)],
            text=True,
            capture_output=True,
        )
        try:
            result = json.loads(p.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"Lean validator did not emit JSON. rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}"
            ) from e
        return bool(result["valid"]), result, p.returncode


def tn(name, horizon, tasks):
    return {
        "id": name,
        "timelines": [],
        "tasks": tasks,
        "taskdefs": [],
        "endTime": horizon,
    }


cases = {
    "interior_control": {
        "source": """tasknet InteriorControl {
  end = 3;
  task A { start_range [1,1]; end_range [2,2]; duration_range [1,1]; }
}
""",
        "lean_tn": tn("InteriorControl", 3, [lean_task("A", "required", 1, 1, 2, 2, 1, 1)]),
        "schedule": {"tasks": {"A": {"start": 1, "end": 2}}, "included": []},
        "expected": (True, True),
    },
    "excluded_optional_h2": {
        "source": """tasknet GhostH2 {
  end = 2;
  optional task ghost;
}
""",
        "lean_tn": tn("GhostH2", 2, [lean_task("ghost", "optional", 0, 100, 0, 100, 0, 100)]),
        "schedule": {"tasks": {}, "included": []},
        "expected": (False, True),
    },
    "start_at_zero": {
        "source": """tasknet StartAtZero {
  end = 3;
  task A { start_range [0,0]; end_range [1,1]; duration_range [1,1]; }
}
""",
        "lean_tn": tn("StartAtZero", 3, [lean_task("A", "required", 0, 0, 1, 1, 1, 1)]),
        "schedule": {"tasks": {"A": {"start": 0, "end": 1}}, "included": []},
        "expected": (False, True),
    },
    "end_at_horizon": {
        "source": """tasknet EndAtHorizon {
  end = 3;
  task A { start_range [1,1]; end_range [3,3]; duration_range [2,2]; }
}
""",
        "lean_tn": tn("EndAtHorizon", 3, [lean_task("A", "required", 1, 1, 3, 3, 2, 2)]),
        "schedule": {"tasks": {"A": {"start": 1, "end": 3}}, "included": []},
        "expected": (False, True),
    },
    "shared_boundary_immediate": {
        "source": """tasknet SharedBoundaryImmediate {
  end = 5;
  task A { start_range [1,1]; end_range [2,2]; duration_range [1,1]; }
  task B {
    start_range [2,2]; end_range [3,3]; duration_range [1,1];
    after A;
  }
}
""",
        "lean_tn": tn(
            "SharedBoundaryImmediate",
            5,
            [
                lean_task("A", "required", 1, 1, 2, 2, 1, 1),
                lean_task("B", "required", 2, 2, 3, 3, 1, 1, after=["A"]),
            ],
        ),
        "schedule": {
            "tasks": {
                "A": {"start": 1, "end": 2},
                "B": {"start": 2, "end": 3},
            },
            "included": [],
        },
        "expected": (False, True),
    },
}

results = {}
for name, case in cases.items():
    smt = stock_sat(case["source"])
    lean_ok, lean_result, lean_rc = lean_validate(case["lean_tn"], case["schedule"])
    expected = case["expected"]
    observed = (smt, lean_ok)
    if observed != expected:
        raise AssertionError(
            f"{name}: expected stock/Lean={expected}, observed={observed}; lean={lean_result}"
        )
    results[name] = {
        "python_z3_sat": smt,
        "lean_schedule_admissible": lean_ok,
        "lean_exit_code": lean_rc,
    }

evidence = {
    "tasksat_pin": PIN,
    "finding": "TASKSAT_LEAN_VS_PYTHON_SMT_ZONE_COMMUTING_FAILURE",
    "results": results,
    "summary": {
        "control_agreement": "interior schedule accepted by both",
        "semantic_disagreements": [
            "excluded optional task: Lean admits empty included schedule; Python/Z3 reports UNSAT",
            "task start at 0: Lean admits; Python/Z3 reports UNSAT",
            "task end at horizon: Lean admits; Python/Z3 reports UNSAT",
            "immediate handoff B.start=A.end: Lean admits; Python/Z3 reports UNSAT",
        ],
        "root": "Python/Z3 fixed strict zone bijection is stronger than TaskNetExec Lean admissibility semantics",
    },
}
Path("tasksat_cross_semantics_v4_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
print("PASS_TASKSAT_LEAN_Z3_COMMUTING_FAILURE")
