#!/usr/bin/env python3
import json
import sys
from pathlib import Path

tasksat_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tasksat_root / "src" / "smt"))

from tasknet_parser import parse_tasknet  # noqa: E402
from tasknet_smt import TaskNetTL  # noqa: E402

PIN = "f9d6063b45967a3fea578c47f54806aadaafe1b0"


def stock_sat(source: str) -> bool:
    tn = parse_tasknet(source)
    enc = TaskNetTL(tn, error_trace=False, use_optimization=False, track=False, portfolio=False)
    model, _ = enc.solve(analyze_core=False)
    return model is not None


cases = {
    "interior_control": """
tasknet InteriorControl {
  end = 3;
  task A {
    start_range [1, 1];
    end_range [2, 2];
    duration_range [1, 1];
  }
}
""",
    "start_at_zero": """
tasknet StartAtZero {
  end = 3;
  task A {
    start_range [0, 0];
    end_range [1, 1];
    duration_range [1, 1];
  }
}
""",
    "end_at_horizon": """
tasknet EndAtHorizon {
  end = 3;
  task A {
    start_range [1, 1];
    end_range [3, 3];
    duration_range [2, 2];
  }
}
""",
    "shared_boundary_control": """
tasknet SharedBoundaryControl {
  end = 6;
  task A {
    start_range [1, 1];
    end_range [2, 2];
    duration_range [1, 1];
  }
  task B {
    start_range [3, 3];
    end_range [4, 4];
    duration_range [1, 1];
    after A;
  }
}
""",
    "shared_boundary_immediate": """
tasknet SharedBoundaryImmediate {
  end = 5;
  task A {
    start_range [1, 1];
    end_range [2, 2];
    duration_range [1, 1];
  }
  task B {
    start_range [2, 2];
    end_range [3, 3];
    duration_range [1, 1];
    after A;
  }
}
""",
}

observed = {name: stock_sat(src) for name, src in cases.items()}

assert observed["interior_control"] is True
assert observed["start_at_zero"] is False
assert observed["end_at_horizon"] is False
assert observed["shared_boundary_control"] is True
assert observed["shared_boundary_immediate"] is False

evidence = {
    "tasksat_pin": PIN,
    "finding": "ZONE_BIJECTION_IMPOSES_STRONGER_BOUNDARY_SEMANTICS",
    "observed": observed,
    "documented_contracts": {
        "scheduling_domain": "theory describes required-task start/end times in [0,H]",
        "after_shorthand": "manual describes no-gap after as B.start >= A.end, permitting equality",
    },
    "derived": {
        "endpoint_exclusion": "task boundaries are forced onto internal zones, so start=0 and end=H are impossible",
        "coincidence_exclusion": "2N task-boundary variables biject to 2N strictly ordered internal zones, so distinct tasks cannot share a boundary",
        "classification": {
            "endpoint_cases": "DSL/theory-to-encoder completeness mismatch",
            "shared_boundary_case": "manual/theory tension plus encoder chooses strict-distinct interpretation",
        },
    },
}
Path("tasksat_zone_boundary_audit_v3_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
print("PASS_TASKSAT_ZONE_BOUNDARY_SEMANTIC_AUDIT")
