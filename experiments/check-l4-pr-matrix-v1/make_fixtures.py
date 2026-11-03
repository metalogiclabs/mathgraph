"""Authored labelled controls. This is not autonomous discovery."""
from pathlib import Path
import json

GOOD = '''namespace Subject
def bump (n : Nat) : Nat := n + 1
theorem support (n : Nat) : bump n = n + 1 := rfl
theorem claim : ∀ n : Nat, bump n = n + 1 := support
end Subject
'''
CONSUMER = 'import Subject\nexample : ∀ n : Nat, Subject.bump n = n + 1 := Subject.claim\n'
PROBE = 'import Subject\n#guard Subject.bump 4 == 5\n'
GATE = 'import Consumer\ndef main : IO Unit := pure ()\n'
UNGATED = 'import Subject\ndef main : IO Unit := pure ()\n'
MASKED = 'import Subject\ndef main : IO Unit := do\n  let r ← IO.Process.output {cmd := "/bin/false"}\n  IO.println s!"tool exit (ignored): {r.exitCode}"\n'
WEAK = GOOD[:GOOD.index('theorem claim')] + 'theorem claim : (∀ n : Nat, bump n = n + 1) ∨ True := Or.inr True.intro\nend Subject\n'
BAD = GOOD.replace('n + 1', 'n + 2')
AXIOM = GOOD[:GOOD.index('theorem claim')] + 'axiom oracle : ∀ n : Nat, bump n = n + 1\ntheorem claim : ∀ n : Nat, bump n = n + 1 := oracle\nend Subject\n'

def make(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    baseline = {'schema': 1, 'consumer': CONSUMER, 'probe': PROBE, 'declaration': 'Subject.claim', 'allowed_axioms': [], 'required_consumer_artifact': True, 'generated_exact': False}
    cases = [
        ('alternative_proof', GOOD, GOOD.replace(':= support', ':= fun n => rfl'), GATE, 'BOUNDED_PASS'),
        ('weakened_conclusion', GOOD, WEAK, UNGATED, 'INTRODUCED_OR_CHANGED_FAILURE'),
        ('omitted_consumer', GOOD, GOOD, UNGATED, 'INTRODUCED_OR_CHANGED_FAILURE'),
        ('masked_gate', GOOD, GOOD, MASKED, 'INTRODUCED_OR_CHANGED_FAILURE'),
        ('introduced_behavior', GOOD, BAD, UNGATED, 'INTRODUCED_OR_CHANGED_FAILURE'),
        ('inherited_behavior', BAD, BAD, UNGATED, 'INHERITED_FAILURE'),
        ('valid_refactor', GOOD, GOOD.replace('n + 1', 'Nat.succ n'), GATE, 'BOUNDED_PASS'),
        ('new_axiom', GOOD, AXIOM, GATE, 'INTRODUCED_OR_CHANGED_FAILURE'),
        ('generator_drift', GOOD, GOOD, GATE, 'INTRODUCED_OR_CHANGED_FAILURE'),
        ('compile_failure', GOOD, 'this is not Lean syntax\n', UNGATED, 'UNKNOWN'),
        ('changed_contract', GOOD, GOOD, GATE, 'OWNER_REVIEW_REQUIRED'),
    ]
    labels = []
    for name, base, head, gate, expected in cases:
        for side, source, entry in [('base', base, UNGATED if name == 'inherited_behavior' else GATE), ('head', head, gate)]:
            folder = root / name / side; folder.mkdir(parents=True, exist_ok=True)
            contract = {**baseline, 'generated_exact': name == 'generator_drift'}
            if name == 'changed_contract' and side == 'head': contract['allowed_axioms'] = ['Subject.oracle']
            (folder/'contract.json').write_text(json.dumps(contract, sort_keys=True)+'\n')
            (folder/'Subject.lean').write_text(source)
            (folder/'Consumer.lean').write_text(CONSUMER)
            (folder/'Gate.lean').write_text(entry)
            if name == 'generator_drift':
                emitted = BAD if side == 'head' else GOOD
                (folder/'Generate.lean').write_text('def main : IO Unit := IO.print '+json.dumps(emitted)+'\n')
        labels.append({'id': name, 'expected': expected, 'authority': 'HUMAN_AUTHORED_CALIBRATION'})
    (root/'labels.json').write_text(json.dumps(labels, indent=2)+'\n')

if __name__ == '__main__':
    import sys
    make(sys.argv[1])
