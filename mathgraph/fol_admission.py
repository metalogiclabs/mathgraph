"""Independent Lean admission for a deliberately small first-order fragment.

Supported: ground unary facts, universally quantified unary implications, and a
single ground unary conjecture. No equality, functions, negation, existential
axioms, arithmetic or arbitrary TPTP/Lean code. Unsupported input stays UNKNOWN.

A Vampire status is a proposal, not a certificate. This boundary reconstructs an
independent proof, or a complete finite interpretation, and invokes Lean on that
exact problem. This is NOT a checker for arbitrary Vampire proof traces.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

from mathgraph.atp_tptp import FirstOrderResidual, ATPCandidateEvidence, _name
from mathgraph.crystal import content_id
from mathgraph.protected_future import ContinuationStatus as S, ProtectedContinuation as Edge, ProtectedContinuationMachine as Machine
from mathgraph.query_gateway import CrystalQuestion

INTERFACE = 'logic.first-order.entailment@1'
CHECKER_SUPPORT = 'checker:lean4:4.24.0:unary-horn-v1'
TOOLCHAIN = 'leanprover/lean4:v4.24.0'
ATOM = re.compile(r'\s*([a-z][A-Za-z0-9_]*)\s*\(\s*([a-z][A-Za-z0-9_]*)\s*\)\s*')
RULE = re.compile(r'\s*!\s*\[\s*([A-Z][A-Za-z0-9_]*)\s*\]\s*:\s*\(\s*([a-z][A-Za-z0-9_]*)\s*\(\s*([A-Z][A-Za-z0-9_]*)\s*\)\s*=>\s*([a-z][A-Za-z0-9_]*)\s*\(\s*([A-Z][A-Za-z0-9_]*)\s*\)\s*\)\s*')


@dataclass(frozen=True)
class CheckPlan:
    status: S
    constants: tuple[str, ...]
    predicates: tuple[str, ...]
    true_atoms: tuple[tuple[str, str], ...]
    lean_source: str


def prepare_check(r: FirstOrderResidual) -> CheckPlan:
    """Parse the *entire* allowed input, then construct a checkable result."""
    metadata = (r.problem_id, r.conjecture_name, r.boundary_ref, *r.source_refs)
    if any(not isinstance(s, str) or not s or any(ord(c) < 32 for c in s) for s in metadata):
        raise ValueError('invalid metadata / comment injection')
    names = [_name(n) for n, _ in r.axioms] + [_name(r.conjecture_name)]
    if len(set(names)) != len(names) or len(r.axioms) > 128:
        raise ValueError('duplicate exported name or input budget exceeded')
    goal = ATOM.fullmatch(r.conjecture)
    if goal is None:
        raise ValueError('unsupported conjecture; require a ground unary atom')
    goal_atom = goal.groups()
    parsed = []
    constants = {goal_atom[1]}
    predicates = {goal_atom[0]}
    for _, text in r.axioms:
        if not isinstance(text, str) or len(text) > 4096:
            raise ValueError('formula budget exceeded')
        fact, rule = ATOM.fullmatch(text), RULE.fullmatch(text)
        if fact:
            p, c = fact.groups(); parsed.append(('fact', p, c))
            constants.add(c); predicates.add(p)
        elif rule:
            var, p, x, q, y = rule.groups()
            if var != x or var != y:
                raise ValueError('free or differently scoped variable')
            parsed.append(('rule', p, q)); predicates.update((p, q))
        else:
            raise ValueError('unsupported first-order fragment')
    cs, ps = tuple(sorted(constants)), tuple(sorted(predicates))
    if len(cs) * len(ps) > 4096:
        raise ValueError('grounding budget exceeded')
    pn = {p: f'p{i}' for i, p in enumerate(ps)}
    cn = {c: f'c{i}' for i, c in enumerate(cs)}
    known: dict[tuple[str, str], str] = {}
    steps: list[str] = []

    def derive(atom: tuple[str, str], proof: str) -> None:
        if atom not in known:
            name = f'd{len(steps)}'
            known[atom] = name
            steps.append(f'  have {name} : {pn[atom[0]]} {cn[atom[1]]} := {proof}')

    for i, (kind, p, c) in enumerate(parsed):
        if kind == 'fact': derive((p, c), f'h{i}')
    changed = True
    while changed:
        size = len(known)
        for i, (kind, p, q) in enumerate(parsed):
            if kind == 'rule':
                for c in cs:
                    if (p, c) in known:
                        derive((q, c), f'h{i} {cn[c]} {known[(p, c)]}')
        changed = size != len(known)

    def formula(item: tuple[str, str, str], domain: str) -> str:
        kind, p, q = item
        return (f'{pn[p]} {cn[q]}' if kind == 'fact'
                else f'∀ x : {domain}, {pn[p]} x → {pn[q]} x')

    if goal_atom in known:
        params = ['(D : Type)'] + [f'({pn[p]} : D → Prop)' for p in ps]
        params += [f'({cn[c]} : D)' for c in cs]
        params += [f'(h{i} : {formula(item, "D")})' for i, item in enumerate(parsed)]
        source = 'theorem certificate\n  ' + '\n  '.join(params)
        source += f' : {pn[goal_atom[0]]} {cn[goal_atom[1]]} := by\n'
        source += '\n'.join(steps) + f'\n  exact {known[goal_atom]}\n'
        status = S.WARRANTED
    else:
        # Complete nonempty interpretation, not "bounded search found nothing".
        domain = 'ModelDomain'
        definitions = ['inductive ModelDomain where\n' + '\n'.join(f'  | {cn[c]}' for c in cs)]
        definitions += [f'def {cn[c]} : {domain} := .{cn[c]}' for c in cs]
        for p in ps:
            rows = '\n'.join(f'  | .{cn[c]} => {"True" if (p,c) in known else "False"}' for c in cs)
            definitions.append(f'def {pn[p]} : {domain} → Prop\n{rows}')
        constraints = [f'({formula(item, domain)})' for item in parsed]
        constraints.append(f'(¬ {pn[goal_atom[0]]} {cn[goal_atom[1]]})')
        proofs = []
        for kind, p, q in parsed:
            if kind == 'fact':
                proofs.append('True.intro')
            else:
                rows = '\n'.join(
                    f'    | .{cn[c]} => fun h => {"True.intro" if (q,c) in known else "False.elim h"}'
                    for c in cs)
                proofs.append(f'(fun x => match x with\n{rows})')
        proof = '(fun h => h)'
        for item in reversed(proofs):
            proof = f'And.intro ({item}) ({proof})'
        source = '\n'.join(definitions) + '\ntheorem certificate : '
        source += ' ∧ '.join(constraints) + ' :=\n  ' + proof + '\n'
        status = S.EXCLUDED
    source += '#print axioms certificate\n'
    return CheckPlan(status, cs, ps, tuple(sorted(known)), source)


def initial_query(r: FirstOrderResidual) -> tuple[Machine, CrystalQuestion]:
    """The state identity binds formulas, assumptions, boundary and provenance."""
    q = CrystalQuestion(r.id, INTERFACE, ('holds',), INTERFACE, (CHECKER_SUPPORT,))
    m = Machine(r.boundary_ref, (r.id,), (Edge(r.id, INTERFACE, ('holds',), S.UNKNOWN),))
    return m, q


def check_lean_source(source: str, *, lean: str, evidence_dir: Path) -> dict:
    """Internal generated-source checker. The executable/environment are trusted."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.encode()).hexdigest()
    path = evidence_dir / f'{digest}.lean'
    path.write_text(source, encoding='utf-8')
    env = {**os.environ, 'ELAN_TOOLCHAIN': TOOLCHAIN}
    record = {'accepted': False, 'reason': 'checker_failure', 'lean_source_sha256': digest,
              'lean_source_file': path.name, 'validation_mode': 'independent_reproof_or_model_check'}
    start = time.perf_counter()
    try:
        version = subprocess.run([lean, '--version'], text=True, capture_output=True, timeout=30, env=env)
        record['lean_version'] = version.stdout.strip()
        if version.returncode or not re.search(r'\b4\.24\.0\b', version.stdout):
            record['reason'] = 'checker_version_mismatch'
            return record
        proc = subprocess.run([lean, str(path.resolve())], text=True, capture_output=True, timeout=30, env=env)
        record.update(lean_stdout=proc.stdout, lean_stderr=proc.stderr, checker_returncode=proc.returncode)
        # Generated proof terms must be kernel checked without sorry/native axioms.
        if proc.returncode == 0 and "'certificate' does not depend on any axioms" in proc.stdout:
            record.update(accepted=True, reason='checked', axioms=[])
    except FileNotFoundError:
        record['reason'] = 'checker_unavailable'
    except subprocess.TimeoutExpired:
        record['reason'] = 'checker_timeout'
    except OSError as exc:
        record.update(reason='checker_unavailable', error=type(exc).__name__)
    finally:
        record['checker_wall_seconds'] = time.perf_counter() - start
    return record


@dataclass(frozen=True)
class AdmissionAttempt:
    machine: Machine
    status: S
    reason: str
    record: dict


def check_and_admit(m: Machine, q: CrystalQuestion, r: FirstOrderResidual,
                    candidate: ATPCandidateEvidence, *, lean: str = 'lean',
                    evidence_dir: Path) -> AdmissionAttempt:
    """Only an independently checked exact query can acquire authority."""
    def unknown(reason: str, extra: dict | None = None) -> AdmissionAttempt:
        return AdmissionAttempt(m, S.UNKNOWN, reason, {'reason': reason, **(extra or {})})

    if (m.boundary_ref != r.boundary_ref or q.source != r.id or q.source not in m.states
        or q.continuation != INTERFACE or q.interface_id != INTERFACE or q.outcome != ('holds',)):
        return unknown('question_problem_mismatch')
    if (candidate.residual_id != r.id or candidate.tptp_sha256 != r.tptp_sha256
        or candidate.problem_id != r.problem_id):
        return unknown('candidate_problem_mismatch')
    try:
        plan = prepare_check(r)
    except ValueError as exc:
        return unknown('unsupported_fragment', {'detail': str(exc)})
    expected_szs = 'Theorem' if plan.status is S.WARRANTED else 'CounterSatisfiable'
    expected_candidate = 'CANDIDATE_WARRANTED' if plan.status is S.WARRANTED else 'CANDIDATE_EXCLUDED'
    statuses = re.findall(r'^\s*[%#]?\s*SZS status\s+(\w+)', candidate.stdout, re.M)
    if (candidate.szs_status != expected_szs or candidate.candidate_status != expected_candidate
        or statuses != [expected_szs] or candidate.returncode != 0):
        return unknown('candidate_semantics_disagree')
    record = check_lean_source(plan.lean_source, lean=lean, evidence_dir=Path(evidence_dir))
    if not record['accepted']:
        return unknown(record['reason'], record)
    record.update(problem_id=r.problem_id, residual_id=r.id, tptp_sha256=r.tptp_sha256,
                  candidate_evidence_id=candidate.id, boundary_ref=r.boundary_ref,
                  status=plan.status.value, question_id=q.id,
                  terminal_form='VERIFIED_PROOF' if plan.status is S.WARRANTED else 'FINITE_COUNTERMODEL',
                  constants=list(plan.constants), predicates=list(plan.predicates),
                  true_atoms=[list(atom) for atom in plan.true_atoms],
                  parser_boundary='unary-ground-facts-and-universal-unary-implications-v1')
    receipt = content_id({k:v for k,v in record.items() if k != 'checker_wall_seconds'}, prefix='admission')
    record['receipt_id'] = receipt
    edge = Edge(q.source, q.continuation, q.outcome, plan.status,
                support_refs=(CHECKER_SUPPORT,),
                evidence_refs=(receipt, candidate.id, f'tptp-sha256:{r.tptp_sha256}',
                               f'lean-source-sha256:{record["lean_source_sha256"]}'))
    # Remove only the exact answered UNKNOWN; keep other knowledge and conflicts.
    remaining = tuple(e for e in m.continuations if not
                      (e.source == q.source and e.continuation == q.continuation
                       and e.outcome == q.outcome and e.status is S.UNKNOWN))
    if edge not in remaining:
        remaining += (edge,)
    updated = Machine(m.boundary_ref, m.states, remaining)
    return AdmissionAttempt(updated, plan.status, 'independently_checked', record)
