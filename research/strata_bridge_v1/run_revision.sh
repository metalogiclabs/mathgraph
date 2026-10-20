#!/usr/bin/env bash
set -euo pipefail
VARIANT="$1"
PIN="$2"
ROOT="$(pwd)"
DIR="$ROOT/research/strata_bridge_v1"
OUT="$DIR/evidence/$VARIANT"
mkdir -p "$OUT"
fail() { echo "APPARATUS_OR_SCIENTIFIC_RED: $*" >&2; exit 1; }
case "$VARIANT" in exposed_main|proposed_repair) ;; *) fail "unknown variant";; esac
echo "STAGE=PINNED_STRATA_SOURCE variant=$VARIANT sha=$PIN"
printf '%s\n' "$PIN" > "$OUT/expected_revision.txt"
git init -q "$OUT/upstream"
git -C "$OUT/upstream" remote add origin https://github.com/strata-org/Strata.git
git -C "$OUT/upstream" fetch --quiet --depth 1 origin "$PIN"
git -C "$OUT/upstream" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
ACTUAL="$(git -C "$OUT/upstream" rev-parse HEAD)"
test "$ACTUAL" = "$PIN" || fail "source revision changed"
printf '%s\n' "$ACTUAL" > "$OUT/actual_revision.txt"
sha256sum "$DIR/BadVC.lean" "$DIR/Control.lean" "$DIR/PROTOCOL.md" > "$OUT/probe_sha256.txt"
(
 cd "$OUT/upstream"
 sha256sum lean-toolchain lake-manifest.json Strata/MetaVerifier.lean Strata/DL/SMT/Translate.lean Strata/DL/SMT/Denote.lean > "$OUT/upstream_sha256.txt"
)
echo "STAGE=LEAN_TOOLCHAIN"
curl --fail --location --retry 2 --silent --show-error \
 "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh" -o "$OUT/elan-init.sh"
sh "$OUT/elan-init.sh" -y --default-toolchain none
export PATH="$HOME/.elan/bin:$PATH"
cd "$OUT/upstream"
lean --version > "$OUT/lean_version.txt"
lake --version > "$OUT/lake_version.txt"
echo "STAGE=UPSTREAM_NATIVE_BUILD"
lake build Strata > "$OUT/lake_build.log" 2>&1 || {
 tail -150 "$OUT/lake_build.log"
 fail "pinned library build failed"
}
echo "BUILD_STRATA_GREEN"

echo "STAGE=UNCHANGED_POSITIVE_CONTROL"
if lake env lean "$DIR/Control.lean" > "$OUT/control.log" 2>&1; then
  grep -F 'MATHGRAPH_CONTROL_GREEN' "$OUT/control.log" || fail "missing control receipt"
  grep -F 'plain_div_zero' "$OUT/control.log" || fail "plain arithmetic control not checked"
  grep -F 'smt_div_zero' "$OUT/control.log" || fail "SMT semantics control not checked"
  ! grep -F 'sorryAx' "$OUT/control.log" || fail "sorry axiom in control"
  echo "CONTROL_GREEN"
else
 tail -120 "$OUT/control.log"
 fail "control Lean file failed"
fi

echo "STAGE=EXPOSED_BAD_VC"
set +e
lake env lean "$DIR/BadVC.lean" > "$OUT/bad_vc.log" 2>&1
CODE="$?"
set -e
printf '%s\n' "$CODE" > "$OUT/bad_vc_exit_code.txt"
if [ "$VARIANT" = "exposed_main" ]; then
 test "$CODE" -eq 0 || { tail -100 "$OUT/bad_vc.log"; fail "main could not replay bad VC"; }
 grep -F '_genSMTVCs_tcbBridge' "$OUT/bad_vc.log" || fail "missing bridge axiom"
 grep -F 'MATHGRAPH_EXPOSED_FALSE_ACCEPTED' "$OUT/bad_vc.log" || fail "missing False theorem marker"
 ! grep -F 'sorryAx' "$OUT/bad_vc.log" || fail "sorryAx in bad VC proof"
 echo "MAIN_ACCEPTED_FALSE_RELATIVE_TO_BRIDGE"
else
 test "$CODE" -ne 0 || fail "proposed repair accepted the bad VC"
 grep -E 'smtUDiv|gen_smt_vcs|udiv_zero' "$OUT/bad_vc.log" > "$OUT/semantic_error_excerpts.txt" || fail "not a semantic goal rejection"
 grep -E 'error:|error\(' "$OUT/bad_vc.log" > "$OUT/error_lines.txt" || fail "no Lean errors recorded"
 echo "REPAIR_REFUSED_EXPOSED_BAD_VC"
fi

echo "STAGE=REPLAY_REPORT"
python3 - "$VARIANT" "$PIN" "$OUT" <<'PY'
import hashlib, json, pathlib, sys
variant, sha, dirname = sys.argv[1:]
p=pathlib.Path(dirname)
h=lambda path: hashlib.sha256((p/path).read_bytes()).hexdigest()
code=int((p/'bad_vc_exit_code.txt').read_text())
report={
 "schema":"mathgraph.strata-smt.exposed-transfer.v1",
 "source_repository":"strata-org/Strata",
 "pinned_revision":sha,
 "actual_revision":(p/'actual_revision.txt').read_text().strip(),
 "variant":variant,
 "control":"LEAN_CHECKED",
 "bad_vc": "ACCEPTED_WITH_BRIDGE" if code==0 else "REJECTED",
 "bad_vc_exit_code":code,
 "lean_toolchain":(p/'lean_version.txt').read_text().strip(),
 "evidence_hashes":{s:h(s) for s in ("control.log","bad_vc.log","lake_build.log","upstream_sha256.txt","probe_sha256.txt")},
 "scientific_status":"EXPOSED_RETROSPECTIVE_ONLY",
}
(p/"run_report.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
print(json.dumps({k:report[k] for k in ("variant","actual_revision","control","bad_vc","bad_vc_exit_code")},indent=2))
PY
echo "STAGE=REVISION_COMPLETED"
