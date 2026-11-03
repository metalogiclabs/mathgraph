export const CLI_MODE='OWNED_FORK_CLI_PARITY';
export const CLI_PROFILES=[
  {
    "id": "traceof",
    "base_entry": "scripts/gen_traceof.py",
    "head_entry": "Scripts/Main/GenTraceOf.lean",
    "runtime_scope": "generator stdout/report on declared grammar fixtures"
  },
  {
    "id": "ledger-diff",
    "base_entry": "scripts/ledger_diff.py",
    "head_entry": "Scripts/Main/LedgerDiff.lean",
    "runtime_scope": "ledger report, latest-selection, output-file and error exits"
  },
  {
    "id": "residue-classes",
    "base_entry": "scripts/residue_classes.py",
    "head_entry": "Scripts/Main/PackCensus.lean",
    "runtime_scope": "read-only classes subcommand; flip/residue proof rewriting excluded"
  }
];
export function cliProfileFor(files){const xs=CLI_PROFILES.filter(p=>files.some(f=>f.filename===p.base_entry&&f.status==='removed')&&files.some(f=>f.filename===p.head_entry&&['added','modified'].includes(f.status)));return xs.length===1?xs[0]:null;}
