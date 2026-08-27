#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$ROOT/source"
mkdir -p "$ROOT/source/kernel_v41" "$ROOT/source/uvrm_v6"

gh run download 32782797883 --repo heathsanchez/test --name v41-disagreement-atlas --dir "$ROOT/source/kernel_v41"
gh run download 32691619972 --repo heathsanchez/test --name uvrm-graph-v6-protected --dir "$ROOT/source/uvrm_v6"

sha256sum "$ROOT/source/kernel_v41/disagreement_atlas.json" "$ROOT/source/uvrm_v6/run_metadata.json" "$ROOT/source/uvrm_v6/score_output.txt"
