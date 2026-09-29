#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

SOURCE_REPO = "lamm-mit/graphene-agent"
SOURCE_COMMIT = "401e5f1f2a7529d8370a75a9c6b403bf2b9679ab"

CASES = [
    {
        "name": "phi010_no_overlap",
        "run_id": "run_20260909_071807_f7d894",
        "source_blob": "0f270244ddd59bf79f2095871e674f75d63c28fd",
        "slit_len_A": 11.875,
        "period_y_A": 16.0,
        "angle_deg": 20.0,
        "expected_overlap": False,
        "rebo2_strength_Nm": 20.036106301197968,
    },
    {
        "name": "phi020_overlap",
        "run_id": "run_20260906_012602_320a91",
        "source_blob": "c8197da73beb6c28130fb40b00023a1679c8962d",
        "slit_len_A": 26.5,
        "period_y_A": 16.0,
        "angle_deg": 20.0,
        "expected_overlap": True,
        "rebo2_strength_Nm": 8.937497909653079,
    },
    {
        "name": "phi030_overlap",
        "run_id": "run_20260909_082248_7c3ed8",
        "source_blob": "ac92dc76ab0d191dc4df88dbd560dadca097d25a",
        "slit_len_A": 39.375,
        "period_y_A": 16.0,
        "angle_deg": 20.0,
        "expected_overlap": True,
        "rebo2_strength_Nm": 12.905249617003875,
    },
]

OUT = Path("evidence/buehler-graphene-cross-potential-v2")
WORK = OUT / "work"
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)

STRAINS = [round(i * 0.01, 6) for i in range(0, 36)]
TRANSFER_MARGIN = 0.05  # preregistered: no-overlap must exceed each overlap peak by >5%

def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "MathGraph-Crystal/1"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def parse_extxyz(raw: bytes):
    lines = raw.decode("utf-8").splitlines()
    n = int(lines[0].strip())
    header = lines[1]
    m = re.search(r'Lattice="([^"]+)"', header)
    if not m:
        raise ValueError("missing Lattice")
    vals = [float(x) for x in m.group(1).split()]
    if len(vals) != 9:
        raise ValueError("unexpected lattice")
    lx, ly, lz = vals[0], vals[4], vals[8]
    atoms = []
    for line in lines[2:2+n]:
        p = line.split()
        if len(p) < 4 or p[0] != "C":
            raise ValueError(f"unexpected atom line: {line[:120]}")
        atoms.append((float(p[1]), float(p[2]), float(p[3])))
    if len(atoms) != n:
        raise ValueError("atom count mismatch")
    return {"n": n, "lx": lx, "ly": ly, "lz": lz, "atoms": atoms, "header": header}

def write_data(path: Path, geom):
    with path.open("w") as f:
        f.write("Buehler exact graphene geometry; atom type 1 = C\n\n")
        f.write(f"{geom['n']} atoms\n")
        f.write("1 atom types\n\n")
        f.write(f"0.0 {geom['lx']:.12f} xlo xhi\n")
        f.write(f"0.0 {geom['ly']:.12f} ylo yhi\n")
        f.write(f"0.0 {geom['lz']:.12f} zlo zhi\n\n")
        f.write("Masses\n\n1 12.011\n\nAtoms # atomic\n\n")
        for i, (x,y,z) in enumerate(geom["atoms"], 1):
            # Keep periodic coordinates inside half-open box for robust read_data.
            xx = x % geom["lx"]
            yy = y % geom["ly"]
            f.write(f"{i} 1 {xx:.10f} {yy:.10f} {z:.10f}\n")

def write_input(path: Path, data_path: Path, pot_path: Path, geom):
    lx0 = geom["lx"]
    lines = [
        "units metal",
        "atom_style atomic",
        "boundary p p f",
        f"read_data {data_path.resolve()}",
        "mass 1 12.011",
        "pair_style airebo 3.0 1 1",
        f"pair_coeff * * {pot_path.resolve()} C",
        "neighbor 2.0 bin",
        "neigh_modify delay 0 every 1 check yes",
        "min_style fire",
        "min_modify dmax 0.05",
        "thermo 250",
        "thermo_style custom step atoms pe pxx pyy lx ly",
        # First relax coordinates and transverse box only; x remains the exact source length.
        "fix bry all box/relax y 0.0 vmax 0.001",
        "minimize 1.0e-7 1.0e-5 1000 10000",
        "unfix bry",
        f"variable s2d equal -pxx*lz*1.0e-5",
        f'print "strain,sigma2d_Nm,pxx_bar,pyy_bar,lx_A,ly_A,pe_eV" file curve.csv screen no',
        f'print "0.000000,$(v_s2d:%.10f),$(pxx:%.10f),$(pyy:%.10f),$(lx:%.10f),$(ly:%.10f),$(pe:%.10f)" append curve.csv screen no',
    ]
    for eps in STRAINS[1:]:
        lx = lx0 * (1.0 + eps)
        lines += [
            f"change_box all x final 0.0 {lx:.12f} remap x units box",
            "fix bry all box/relax y 0.0 vmax 0.001",
            "minimize 1.0e-7 1.0e-5 1000 10000",
            "unfix bry",
            f'print "{eps:.6f},$(v_s2d:%.10f),$(pxx:%.10f),$(pyy:%.10f),$(lx:%.10f),$(ly:%.10f),$(pe:%.10f)" append curve.csv screen no',
        ]
    path.write_text("\n".join(lines) + "\n")

def parse_curve(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("strain"):
            continue
        p = line.split(",")
        if len(p) != 7:
            continue
        rows.append({
            "strain": float(p[0]),
            "sigma2d_Nm": float(p[1]),
            "pxx_bar": float(p[2]),
            "pyy_bar": float(p[3]),
            "lx_A": float(p[4]),
            "ly_A": float(p[5]),
            "pe_eV": float(p[6]),
        })
    if not rows:
        raise ValueError(f"empty curve: {path}")
    peak = max(rows, key=lambda r: r["sigma2d_Nm"])
    return rows, peak

def run_case(case, lmp: str, pot_path: Path):
    run_id = case["run_id"]
    raw_url = (
        f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
        f"carbon_discovery/experiments/database/runs/{run_id}/initial.extxyz"
    )
    raw = get(raw_url)
    geom = parse_extxyz(raw)
    cdir = WORK / case["name"]
    cdir.mkdir(parents=True, exist_ok=True)
    ext = cdir / "initial.extxyz"
    ext.write_bytes(raw)
    data = cdir / "structure.data"
    inp = cdir / "in.airebo"
    write_data(data, geom)
    write_input(inp, data, pot_path, geom)
    log = cdir / "lammps.log"
    with log.open("w") as lf:
        proc = subprocess.run(
            [lmp, "-in", inp.name],
            cwd=cdir,
            stdout=lf,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1500,
        )
    result = {
        **case,
        "source_url": raw_url,
        "download_sha256": sha256(raw),
        "source_atom_count": geom["n"],
        "source_lattice_A": [geom["lx"], geom["ly"], geom["lz"]],
        "tip_overlap_margin_A": case["slit_len_A"] * abs(math.sin(math.radians(case["angle_deg"]))) - case["period_y_A"]/2,
        "returncode": proc.returncode,
        "log_tail": "\n".join(log.read_text(errors="replace").splitlines()[-80:]),
    }
    if proc.returncode != 0 or not (cdir/"curve.csv").exists():
        result["status"] = "INFRASTRUCTURE_OR_SIMULATION_FAILURE"
        return result
    rows, peak = parse_curve(cdir/"curve.csv")
    result.update({
        "status": "MEASURED",
        "curve": rows,
        "airebo_peak_strength_Nm": peak["sigma2d_Nm"],
        "airebo_peak_strain": peak["strain"],
        "final_sigma2d_Nm": rows[-1]["sigma2d_Nm"],
        "final_strain": rows[-1]["strain"],
    })
    return result

def main():
    lmp = shutil.which("lmp") or shutil.which("lammps")
    if not lmp:
        raise SystemExit("No LAMMPS executable found")
    pot_env = os.environ.get("AIREBO_POTENTIAL")
    if not pot_env:
        raise SystemExit("AIREBO_POTENTIAL not set")
    pot_path = Path(pot_env)
    if not pot_path.exists():
        raise SystemExit(f"missing potential: {pot_path}")
    version = subprocess.run([lmp, "-h"], capture_output=True, text=True).stdout.splitlines()[:10]
    pot_bytes = pot_path.read_bytes()
    meta = {
        "schema": "mathgraph.buehler-graphene-cross-potential-v2",
        "status": "CANDIDATE_CROSS_POTENTIAL",
        "source": {
            "repo": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "geometry_files": [
                {
                    "run_id": c["run_id"],
                    "declared_blob_sha": c["source_blob"],
                } for c in CASES
            ],
        },
        "alternate_physics": {
            "engine": "LAMMPS AIREBO",
            "lammps_help_head": version,
            "potential_path": str(pot_path),
            "potential_sha256": sha256(pot_bytes),
            "pair_style": "airebo 3.0 1 1",
            "boundary": "p p f",
            "protocol": "0 K AQS; x engineering strain 0..0.35 in 0.01 steps; FIRE minimization; y box-relax to zero pressure",
        },
        "preregistered_transfer_criterion": {
            "law": "at fixed 20deg staggered slit-row geometry, no-overlap peak strength exceeds each overlap peak strength",
            "relative_margin_each": TRANSFER_MARGIN,
            "decision": "WARRANTED_BOUNDED_CROSS_POTENTIAL only if both pairwise advantages exceed 5%; otherwise REJECTED or UNKNOWN on failed simulation",
        },
    }
    # Three cases concurrently; each LAMMPS process is single-rank.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(run_case, c, lmp, pot_path) for c in CASES]
        results = [f.result() for f in futs]
    meta["cases"] = results
    measured = {r["name"]: r for r in results if r.get("status") == "MEASURED"}
    if len(measured) != 3:
        meta["promotion"] = "UNKNOWN_INCOMPLETE_ALTERNATE_POTENTIAL_RUN"
    else:
        s0 = measured["phi010_no_overlap"]["airebo_peak_strength_Nm"]
        s1 = measured["phi020_overlap"]["airebo_peak_strength_Nm"]
        s2 = measured["phi030_overlap"]["airebo_peak_strength_Nm"]
        adv1 = s0 / s1 - 1.0
        adv2 = s0 / s2 - 1.0
        meta["comparison"] = {
            "no_overlap_Nm": s0,
            "overlap_phi020_Nm": s1,
            "overlap_phi030_Nm": s2,
            "advantage_vs_phi020": adv1,
            "advantage_vs_phi030": adv2,
            "rebo2_reference_Nm": {c["name"]: c["rebo2_strength_Nm"] for c in CASES},
        }
        meta["promotion"] = (
            "WARRANTED_BOUNDED_CROSS_POTENTIAL"
            if adv1 > TRANSFER_MARGIN and adv2 > TRANSFER_MARGIN
            else "REJECTED_CROSS_POTENTIAL_TRANSFER"
        )
    (OUT/"result.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    print(json.dumps({
        "promotion": meta.get("promotion"),
        "comparison": meta.get("comparison"),
        "potential_sha256": meta["alternate_physics"]["potential_sha256"],
        "case_statuses": {r["name"]: r["status"] for r in results},
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
