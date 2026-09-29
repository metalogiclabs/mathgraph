#!/usr/bin/env python3
import json
import sys
from pathlib import Path

tasksat_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tasksat_root / "src" / "smt"))

from z3 import is_false  # noqa: E402
from tasknet_parser import parse_tasknet  # noqa: E402
from tasknet_smt import TaskNetTL  # noqa: E402

PIN = "f9d6063b45967a3fea578c47f54806aadaafe1b0"


def solve(source: str):
    tn = parse_tasknet(source)
    enc = TaskNetTL(
        tn,
        error_trace=False,
        use_optimization=False,
        track=False,
        portfolio=False,
    )
    model, _ = enc.solve(analyze_core=False)
    return tn, enc, model


base_h2 = """
tasknet BaseH2 {
  end = 2;
}
"""

ghost_h2 = """
tasknet GhostH2 {
  end = 2;
  optional task ghost;
}
"""

ghost_h3 = """
tasknet GhostH3 {
  end = 3;
  optional task ghost {
    start_range [10, 10];
  }
}
"""

base_time_guard = """
tasknet BaseTimeGuard {
  end = 3;
  constraints {
    prop no_time_1: always not (time = 1);
  }
}
"""

ghost_time_guard = """
tasknet GhostTimeGuard {
  end = 3;
  optional task ghost {
    start_range [10, 10];
  }
  constraints {
    prop no_time_1: always not (time = 1);
  }
}
"""

_, base2_enc, base2_model = solve(base_h2)
_, ghost2_enc, ghost2_model = solve(ghost_h2)
_, ghost3_enc, ghost3_model = solve(ghost_h3)
_, base_guard_enc, base_guard_model = solve(base_time_guard)
_, ghost_guard_enc, ghost_guard_model = solve(ghost_time_guard)

assert base2_model is not None, "control without optional task must be SAT"
assert ghost2_model is None, (
    "expected pinned TaskSAT to reproduce completeness loss: adding an excludable "
    "optional task at H=2 should make the current fixed-size zone skeleton UNSAT"
)

assert ghost3_model is not None, "H=3 ghost case should be SAT"
ghost_included = ghost3_model.eval(
    ghost3_enc.optional_included["ghost"], model_completion=True
)
assert is_false(ghost_included), (
    "start_range [10,10] with horizon 3 must force the optional ghost to be excluded"
)
ghost3_zones = [
    ghost3_model.eval(z, model_completion=True).as_long()
    for z in ghost3_enc.zones
]
assert ghost3_zones == [0, 1, 2, 3], (
    f"excluded ghost still expected to force phantom boundaries [0,1,2,3], got {ghost3_zones}"
)

assert base_guard_model is not None, (
    "without the ghost, the zone positions are only 0 and 3, so always not(time=1) is SAT"
)
assert ghost_guard_model is None, (
    "excluded ghost's phantom boundaries should flip the same temporal constraint to UNSAT"
)

evidence = {
    "tasksat_pin": PIN,
    "finding": "EXCLUDED_OPTIONAL_TASK_IS_NOT_SEMANTICALLY_INERT",
    "cases": {
        "base_h2": {
            "sat": True,
            "zone_count": base2_enc.zone_count,
        },
        "ghost_h2": {
            "sat": False,
            "zone_count": ghost2_enc.zone_count,
            "expected_semantics": "SAT by excluding ghost",
        },
        "ghost_h3": {
            "sat": True,
            "ghost_included": False,
            "zones": ghost3_zones,
            "semantic_consequence": "excluded ghost still contributes two zone boundaries",
        },
        "base_time_guard": {
            "sat": True,
            "constraint": "always not (time = 1)",
        },
        "ghost_time_guard": {
            "sat": False,
            "constraint": "always not (time = 1)",
            "ghost_forced_excluded": True,
            "semantic_consequence": "excluded declaration changes a temporal verdict",
        },
    },
    "derived_residual": (
        "zone skeleton must be conditional on task inclusion, or absent task boundaries "
        "must be quotiented away without changing temporal observation points"
    ),
}

out = Path("tasksat_optional_zone_audit_v1_evidence.json")
out.write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
print("PASS_TASKSAT_OPTIONAL_ZONE_SEMANTIC_COUNTEREXAMPLE")
