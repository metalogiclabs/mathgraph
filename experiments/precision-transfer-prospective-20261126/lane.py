"""One isolated automatic-check or ordinary Hypothesis execution."""
import argparse
import importlib
import importlib.metadata
import inspect
import json
import sys
import time
from pathlib import Path
from contract import *


class CallLimit(Exception):
    pass


def corrupt(value):
    if type(value) is int:
        return int(float(value))
    if type(value) is list:
        return [corrupt(v) for v in value]
    if type(value) is dict:
        return {k: corrupt(v) for k, v in value.items()}
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--module", required=True)
    p.add_argument("--arm", choices=["candidate", "hypothesis"], required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--mutant", action="store_true")
    a = p.parse_args()
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    rows = []
    result = dict(module=a.module, arm=a.arm, seed=a.seed, injected_mutant=a.mutant,
                  status="UNKNOWN", model_calls_during_frozen_execution=0)
    try:
        module = importlib.import_module(a.module)
        name = next((n for n in ["loads", "decode"] if callable(getattr(module, n, None))), None)
        if name is None:
            raise RuntimeError("NO_SUPPORTED_ENTRYPOINT")
        native = getattr(module, name)
        result["entrypoint"] = a.module + "." + name
        result["module_file"] = module.__file__
        result["module_sha256"] = digest(Path(module.__file__).read_bytes())
        admission = [observe(native, n, 0) for n in [0, 1, -1, 23, -24, 255, 256]]
        result["admission"] = admission
        if any(r["status"] != "AGREEMENT" for r in admission):
            raise RuntimeError("UNSUPPORTED_API_OR_SMALL_INTEGER_CONTRACT")
        decoder = (lambda raw: corrupt(native(raw))) if a.mutant else native

        def check(pair):
            if len(rows) >= 5000:
                raise CallLimit("native call cap reached")
            row = observe(decoder, *pair)
            rows.append(row)
            return row["status"] == "AGREEMENT"

        if a.arm == "candidate":
            for pair in corpus(a.seed):
                if not check(pair):
                    break
        else:
            from hypothesis import given, settings, seed, example, strategies as st, Phase, HealthCheck
            result["hypothesis_version"] = importlib.metadata.version("hypothesis")
            strategy = st.tuples(
                st.one_of(st.sampled_from(boundary_values()), st.integers(MINIMUM, MAXIMUM)),
                st.integers(0, 2))

            @seed(a.seed)
            @settings(max_examples=BUDGET - 1, deadline=None, database=None,
                      phases=(Phase.explicit, Phase.generate, Phase.shrink),
                      suppress_health_check=[HealthCheck.too_slow])
            @example((2**53 + 1, 0))
            @given(strategy)
            def property_test(pair):
                assert check(pair), "exact integer-preservation property failed"

            try:
                property_test()
            except AssertionError:
                if not any(r["status"] != "AGREEMENT" for r in rows):
                    raise
        bad = [r for r in rows if r["status"] != "AGREEMENT"]
        result["status"] = ("VALUE_DISCREPANCY" if any(r["status"] == "VALUE_DISCREPANCY" for r in bad)
                            else "UNKNOWN_REJECTED_INPUT" if bad else "BOUNDED_AGREEMENT")
        result["first_nonagreement_call"] = next((i+1 for i, r in enumerate(rows) if r["status"] != "AGREEMENT"), None)
    except Exception as exc:
        result.update(error=type(exc).__name__, reason=str(exc)[:1000])
    result.update(wall_ns=time.perf_counter_ns()-wall, cpu_ns=time.process_time_ns()-cpu,
                  native_probe_calls=len(rows), observations=rows)
    Path(a.out).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ["admission", "observations"]}))


if __name__ == "__main__":
    main()
