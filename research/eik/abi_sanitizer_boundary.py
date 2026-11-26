#!/usr/bin/env python3
"""A deliberate C-UB control for the pinned EIK host/target assurance boundary.

Run with the official kit's pinned Python environment. No competition API calls,
registration, or submissions are performed. The unmodified published entry is an
input fixture, not code or a performance improvement claimed by this experiment.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

KIT_COMMIT = "5a32428ad4aa23bce737d50a738ace24ddeeed2e"
CONTROL_SHA256 = "8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37"
ANCHOR = "static uint32_t t_eik_tanh(uint32_t t_w) { return t_t_eik_tanh(t_w); }"
VARIANTS = {"control": None, "arm-only-shift-control": 32, "repaired-control": 31}
TARGETS = ("rv32im", "thumbv6m", "thumbv7em")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def sources(control, out):
    if sha256(control) != CONTROL_SHA256:
        raise ValueError("the fixture must be the exact published entry #49")
    text = Path(control).read_text()
    if text.count(ANCHOR) != 1:
        raise ValueError("the Thumb wrapper anchor is not unique")
    result = {}
    for name, shift in VARIANTS.items():
        value = text if shift is None else text.replace(
            ANCHOR,
            "static uint32_t t_eik_tanh(uint32_t t_w) { "
            f"uint32_t audit_shift = 1u << {shift}; (void)audit_shift; "
            "return t_t_eik_tanh(t_w); }",
        )
        path = out / (name + ".c")
        path.write_text(value)
        result[name] = path
    return result


def allocated_image(path):
    # Debug sections / symbol tables can differ because source filenames differ.
    # Compare executable identity: entry point plus every SHF_ALLOC section,
    # including its address, type, flags, size, and complete initialized bytes.
    from elftools.elf.elffile import ELFFile

    with Path(path).open("rb") as f:
        elf = ELFFile(f)
        header = tuple(elf[k] for k in ("e_type", "e_machine", "e_entry", "e_flags"))
        sections = tuple(
            (s.name, s["sh_addr"], s["sh_type"], s["sh_flags"], s["sh_size"], s.data())
            for s in elf.iter_sections() if s["sh_flags"] & 2
        )
    return header, sections


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kit", required=True, type=Path)
    ap.add_argument("--control", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    kit, out = args.kit.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "-C", kit, "rev-parse", "HEAD"], text=True).strip()
    if head != KIT_COMMIT:
        raise ValueError("wrong evaluator commit")
    sys.path.insert(0, str(kit))
    from eik import config as K, stages as ST, toolchain as T
    from eik.emu import Core

    src = sources(args.control, out)
    manifest = {name: sha256(path) for name, path in src.items()}
    write_json(out / "source-pins.json", {"kit_commit": head, "sources": manifest})
    checks = {}

    # Official admission gate: source policy, preprocessing, object code, stack.
    gate = ST.gate(src["arm-only-shift-control"])
    write_json(out / "official-gate.json", gate)
    checks["official_gate_accepts_deliberate_fault"] = gate["verdict"] == "accepted"

    # An actual official host check, limited explicitly to one 2^20-word chunk.
    # 0x3f800000 (1.0f) is in this chunk; ARM and host select different lanes.
    host = ST.fullcheck(src["arm-only-shift-control"], "tanh", chunks=(1016, 1017), threads=1)
    write_json(out / "official-host-chunk.json", host)
    checks["official_host_chunk_passes"] = (
        host["verdict"] == "passed" and host["words_checked"] == 1048576
        and host["range_complete"] and not host["complete"]
    )

    # Visit the Thumb wrapper directly using the official host compiler and
    # sanitizer flags. The faulty source, unlike its control and repair, fails.
    direct = {}
    for name, path in src.items():
        harness = out / (name + "-direct.c")
        harness.write_text(
            f'#include "{path.as_posix()}"\n#include <stdio.h>\n'
            'int main(void) { printf("%08x\\n", t_eik_tanh(0x3f800000u)); return 0; }\n'
        )
        exe = out / (name + "-direct")
        built = T.run([K.HOST_CC, *T.host_cc_args(), harness, "-o", exe])
        (out / (name + "-direct-build.txt")).write_text(built.stdout + built.stderr)
        p = subprocess.run([exe], text=True, capture_output=True, env={**os.environ, **ST.SANITIZER_ENV})
        direct[name] = {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    write_json(out / "direct-thumb-lane-sanitizers.json", direct)
    checks["direct_lane_positive_controls_pass"] = all(
        direct[n]["exit"] == 0 and direct[n]["stdout"].strip() == "3f42f7d6"
        for n in ("control", "repaired-control")
    )
    bad = direct["arm-only-shift-control"]
    checks["direct_lane_detects_shift_ub"] = (
        bad["exit"] == ST.UBSAN_EXIT
        and "shift exponent 32 is too large" in bad["stderr"]
    )

    # Both scored guest images and actual exhaustive-target checker images.
    # This is an image comparison, not a claim to have run full target checks.
    images = {}
    for target in TARGETS:
        images[target] = {}
        for kind, build in (("scoring_guest", T.guest_image), ("target_checker", T.target_checker)):
            base = build(src["control"], target)
            baseline = allocated_image(base)
            images[target][kind] = {}
            for name in ("arm-only-shift-control", "repaired-control"):
                candidate = build(src[name], target)
                equal = baseline == allocated_image(candidate)
                images[target][kind][name] = {
                    "entry_and_allocated_sections_identical": equal,
                    "allocated_sections": len(baseline[1]),
                    "control_file_sha256": sha256(base),
                    "candidate_file_sha256": sha256(candidate),
                }
                checks[f"{target}/{kind}/{name}/same_allocated_image"] = equal
    write_json(out / "target-image-equivalence.json", images)

    # Prototype repair of the measurement boundary: instrument each target's
    # selected C program before optimization. Only candidate code is sanitized;
    # this is separate from scoring and changes no submitted entry.
    trapped = {}
    for target in TARGETS:
        trapped[target] = {}
        for name, path in src.items():
            obj = out / (name + "-" + target + "-ubsan.o")
            elf = out / (name + "-" + target + "-ubsan.elf")
            T.run(T.ZIG + ["cc", *T.target_cc_args(target),
                          "-fsanitize=undefined", "-fsanitize-trap=undefined",
                          "-fno-sanitize-recover=all", "-c", "-o", obj, path])
            T.run(T.ZIG + ["cc", *K.TARGETS[target]["cc"], *K.CFLAGS,
                          "-I", K.HARNESS, "-include", K.HARNESS / "eik.h",
                          "-Wl,--entry=eik_batch", "-o", elf, K.HARNESS / "guest.c", obj])
            try:
                value, instructions = Core(elf, target).call("tanh", 0x3f800000)
                outcome = {"outcome": "returned", "value": f"{value:08x}", "instructions": instructions}
            except Exception as e:
                outcome = {"outcome": "trapped", "error": type(e).__name__ + ": " + str(e)}
            trapped[target][name] = outcome
            should_trap = name == "arm-only-shift-control" and target != "rv32im"
            checks[f"{target}/{name}/target_ubsan_expected_outcome"] = (
                outcome["outcome"] == "trapped" and "UC_ERR_INSN_INVALID" in outcome.get("error", "")
                if should_trap else outcome["outcome"] == "returned" and outcome["value"] == "3f42f7d6"
            )
    write_json(out / "target-sanitizer-traps.json", trapped)
    passed = all(checks.values())
    summary = {
        "epistemic_status": "WARRANTED" if passed else "UNKNOWN",
        "terminal_form": "FINITE_COUNTERMODEL" if passed else "NAMED_OBSTRUCTION",
        "claim": "identical preprocessing plus a sanitized host execution does not ensure the selected ARM C path is free of UB",
        "boundary": "exact pinned fixture/evaluator; deliberate shift UB; one official host chunk; allocated image equality; one target-sanitized input",
        "limits": ["no defect alleged in unmodified entry #49", "no new all-domain qualification", "target instrumentation is a prototype, not a complete C-UB proof"],
        "kit_commit": head, "sources": manifest, "checks": checks,
        "registration_sent": False, "entry_submitted": False,
    }
    write_json(out / "decision.json", summary)
    files = {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.json"}
    write_json(out / "SHA256SUMS.json", files)
    print(json.dumps(summary, indent=2))
    if not passed:
        raise SystemExit("a control or boundary check failed; inspect raw reports")


if __name__ == "__main__":
    main()
