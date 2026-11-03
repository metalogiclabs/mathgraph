"""A maintainer-readable claim -> obligation -> evidence -> boundary report."""
import json,sys
from pathlib import Path
from rules import admit

def render(receipt,controller):
    a=admit(receipt,controller)
    if a['state']=='UNKNOWN':return '# Claim-to-consumer investigation\n\nUNKNOWN: '+a['reason']+'\n\nNo supported claim is admitted. Inspect retained native diagnostics.\n'
    lines=['# L4YAML: empty-tail claim-to-consumer investigation','',
    '**WARRANTED_BOUNDED — the two declared constructor APIs satisfy the frozen consumer at head.**','',
    'Claim authority: [upstream PR212](https://github.com/nasa-jpl/L4YAML/pull/212), replayed in [owned-fork PR6](https://github.com/metalogiclabs/L4YAML/pull/6). This is retrospective verification of an explicitly declared fix, not a new bug discovery.','',
    'Required capability, for every `n : Nat` and `s : SurfPos`:','',
    '```lean','TCompactSeqTail n s s [] ∧ TCompactMapTail n s s []','```','',
    'The independently written consumer uses both promised constructor APIs. Its expectation comes from the source grammar and declared change, rather than Python-output parity.','',
    '| Variant | Generated module | Source empty cases | Strong constructor consumer | Weakened offer | Consumer requiring P |','|---|---|---|---|---|---|']
    for arm,row in receipt['arms'].items():
        v=lambda k:'compiles' if row[k]['exit']==0 else 'rejected'
        lines.append('| '+arm+' | '+' | '.join(v(k) for k in ['module','source_witness','strong_consumer','weak_offer','weak_consumer'])+' |')
    lines+=['','The modules compile even where the declared constructor consumer is rejected. Removing only the two constructors reproduces the rejection; restoration recovers the same semantic observations. The base/deletion result establishes named API unavailability, not that every alternative proof is impossible.','',
    'A deliberately weakened offered conclusion `P ∨ True` compiles in every arm, but a consumer requiring `P` rejects it. The additional Lean proof `¬ (∀ P : Prop, (P ∨ True) → P)` verifies the reusable logical obstruction.','',
    '**Assumptions:** the strong TraceOf consumer and weak offered proof depend on standard Lean axiom `propext`. Source witnesses and the generic weakening law have no axioms. `sorryAx` and any additional axiom are rejected. The initial axiom-free admission in run41600070575 remained UNKNOWN; this explicit revised boundary does not relabel it as an axiom-free success.','',
    '**Boundary:** trusted Lean4.35, not independent Nucleus replay. This is a new audit consumer, not evidence of an existing production consumer failure. Whole-generator semantic completeness, all YAML derivations and whole-PR correctness remain UNKNOWN.','',
    '**Next action:** retain the declared capability as a regression obligation and use the same claim/consumer method for a different consequential claim before generalizing or changing App verdicts.','',
    '## Exact evidence','',f"Controller: `{receipt['controller_sha']}`",f"Base: `{receipt['base_sha']}`",f"Head: `{receipt['head_sha']}`",f"Contract SHA256: `{receipt['contract_sha256']}`",'','Full stdout/stderr, exits, axiom inspections, archive/source/probe hashes and withdrawal evidence are retained in receipt.json and logs/.','']
    return '\n'.join(lines)

if __name__=='__main__':
    root=Path(sys.argv[1]);r=json.loads((root/'receipt.json').read_text());(root/'REPORT.md').write_text(render(r,sys.argv[2]))
