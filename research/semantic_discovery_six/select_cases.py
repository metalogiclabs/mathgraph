"""Deterministic source-only selection, performed after public prompt/broker freeze.

Do not print case content or outcome labels before both investigators lock outputs.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def pinned_files(repository):
    raw = subprocess.check_output(['git', 'ls-tree', '-r', '-z', '--full-tree', 'HEAD'], cwd=repository)
    result = {}
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        header, path = entry.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        if kind == 'blob' and mode in ('100644', '100755'):
            result[path.decode()] = oid
    return result


def blob(repository, oid):
    return subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=repository)


def digest(data):
    return sha256(data).hexdigest()


def smt_forms(text):
    tokens = re.findall(r';[^\n]*|"(?:[^"]|"")*"|\|[^|]*\||[()]|[^()\s]+', text)
    stack, forms = [], []
    for token in tokens:
        if token.startswith(';'):
            continue
        if token == '(':
            stack.append([])
        elif token == ')':
            if not stack:
                raise ValueError('unbalanced SMT')
            form = stack.pop()
            (stack[-1] if stack else forms).append(form)
        elif stack:
            stack[-1].append(token)
        else:
            raise ValueError('SMT atom outside command')
    if stack:
        raise ValueError('unbalanced SMT')
    return forms


def smt_text(node):
    return '(' + ' '.join(map(smt_text, node)) + ')' if isinstance(node, list) else node


def pure_boolean(forms):
    variables = set()
    for f in forms:
        if f[:1] == ['declare-const'] and len(f) == 3 and f[2] == 'Bool':
            variables.add(f[1])
        elif f[:1] == ['declare-fun'] and len(f) == 4 and f[2:] == [[], 'Bool']:
            variables.add(f[1])
        elif f[:1] in (['declare-fun'], ['declare-const'], ['define-fun']):
            return False
    def allowed(x):
        if isinstance(x, str):
            return x in variables or x in {'true', 'false'}
        return bool(x) and x[0] in {'not', 'and', 'or', 'xor', '=>', '=', 'distinct', 'ite'} and all(allowed(y) for y in x[1:])
    assertions = [f[1] for f in forms if f[:1] == ['assert'] and len(f) == 2]
    return len(variables) <= 10 and bool(assertions) and all(allowed(a) for a in assertions)


def walk_requirements(value, pointer=''):
    if isinstance(value, dict):
        semantics = value.get('semantics')
        if (value.get('reqid') and isinstance(value.get('fulltext'), str)
                and isinstance(semantics, dict) and isinstance(semantics.get('CoCoSpecCode'), str)
                and semantics['CoCoSpecCode']):
            yield pointer, value
        else:
            for k, v in value.items():
                yield from walk_requirements(v, pointer + '/' + str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk_requirements(v, pointer + '/' + str(i))


def eligible(sources):
    pool = {'yaml': [], 'aerospace': [], 'mathematics': []}
    yf = pinned_files(sources / 'yaml')
    for rel in sorted(x for x in yf if x.endswith('/in.yaml') or x == 'in.yaml'):
        other = str(Path(rel).with_name('in.json'))
        if other not in yf or str(Path(rel).with_name('error')) in yf:
            continue
        a, b = blob(sources / 'yaml', yf[rel]), blob(sources / 'yaml', yf[other])
        if max(len(a), len(b)) > 4096:
            continue
        try:
            expected = json.loads(b)
            payload = a.decode('utf-8')
        except (ValueError, UnicodeError):
            continue
        pool['yaml'].append({'origin': rel, 'raw': a, 'expected_raw': b,
                             'view': {'requirement': {'expected_json': expected},
                                      'candidate': {'yaml': payload, 'engine': 'PyYAML6.0.3 SafeLoader'},
                                      'requested_scope': 'Exact published fixture result, preserving JSON value types and structure; no whole-language conformance.'}})
    seen = set()
    af = pinned_files(sources / 'aerospace')
    for file in sorted(x for x in af if x.startswith('caseStudies/') and x.endswith('.json')):
        if any(x in file.lower() for x in ('liftpluscruise', 'sounding', 'rocket')):
            continue
        raw = blob(sources / 'aerospace', af[file])
        try:
            document = json.loads(raw)
        except (ValueError, UnicodeError):
            continue
        for pointer, r in walk_requirements(document):
            if r['reqid'].startswith('LPC_'):
                continue
            key = (r['reqid'], r['fulltext'])
            if key in seen:
                continue
            seen.add(key)
            rel = file + '#' + pointer
            variables = document.get('variables', []) if isinstance(document, dict) else []
            pool['aerospace'].append({'origin': rel, 'raw': raw,
                'view': {'requirement': {'text': r['fulltext']},
                         'candidate': {'formula': r['semantics']['CoCoSpecCode'], 'language': 'CoCoSpec/Lustre temporal expression'},
                         'source_record': r, 'source_variables': variables,
                         'requested_scope': 'Check source-to-formula equivalence on traces of lengths1-3: all Boolean assignments and numeric alphabets {-1,0,1} plus numeric literals in the requirement and each literal plus/minus1. Derive signal types from original source declarations or state unresolved type/frame obligations. Cap exhaustive cohort at4096 traces; above this cap preserve UNKNOWN for full cohort coverage. A concrete separating trace still refutes transfer. No universal correspondence, runtime or flight approval is requested.'}})
    fallback = []
    seen_smt = set()
    mf = pinned_files(sources / 'mathematics')
    for rel in sorted(x for x in mf if x.endswith('.smt2')):
        raw = blob(sources / 'mathematics', mf[rel])
        if len(raw) > 8192:
            continue
        try:
            forms = smt_forms(raw.decode('utf-8'))
        except (ValueError, UnicodeError):
            continue
        commands = [x[0] for x in forms if x]
        if commands.count('check-sat') != 1 or any(x in commands for x in ('push', 'pop', 'reset', 'reset-assertions', 'check-sat-assuming')):
            continue
        after_query = commands[commands.index('check-sat') + 1:]
        if any(x in after_query for x in ('assert', 'declare-fun', 'declare-const', 'define-fun', 'set-logic')):
            continue
        if sum(x in ('declare-fun', 'declare-const') for x in commands) > 10:
            continue
        statuses = [x[2] for x in forms if len(x) == 3 and x[:2] == ['set-info', ':status']]
        clean = [x for x in forms if x[:1] != ['set-info']]
        normalized = '\n'.join(map(smt_text, clean)) + '\n'
        if digest(normalized.encode()) in seen_smt:
            continue
        seen_smt.add(digest(normalized.encode()))
        row = {'origin': rel, 'raw': raw, 'hidden_external_status': statuses,
               'view': {'requirement': {'smt2': normalized},
                        'candidate': {'engine': 'Z3 4.15.4', 'task': 'Native solver verdict for exactly these assertions; independently justify correspondence/result before a decisive warrant.'},
                        'requested_scope': 'The exact declared mathematical satisfiability problem; a solver status alone is not an independently verified proof. Keep current authority distinct from mathematical truth.'}}
        fallback.append(row)
        if pure_boolean(forms):
            pool['mathematics'].append(row)
    if len(pool['mathematics']) < 2:
        pool['mathematics'] = fallback
    return pool


def select(sources, destination, freeze):
    start = time.time()
    protocol_bytes = (HERE / 'protocol.json').read_bytes()
    p = json.loads(protocol_bytes)
    for domain, pin in p['repositories'].items():
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=sources / domain, text=True).strip()
        if actual != pin['commit']:
            raise ValueError('SOURCE_PIN_MISMATCH:' + domain)
    files = ['protocol.json', 'common_prompt.txt', 'mathgraph_prompt.txt', 'conventional_prompt.txt',
             'select_cases.py', 'broker.py', 'adjudication_prompt.txt']
    for name in files:
        path = 'research/semantic_discovery_six/' + name
        frozen = subprocess.check_output(['git', 'show', freeze + ':' + path], cwd=REPO)
        if frozen != (HERE / name).read_bytes():
            raise ValueError('FREEZE_MISMATCH:' + name)
    core = subprocess.check_output(['git', 'show', freeze + ':mathgraph_check/warrant_resolution.py'], cwd=REPO)
    if core != (REPO / 'mathgraph_check/warrant_resolution.py').read_bytes():
        raise ValueError('FROZEN_KIT_MISMATCH')
    if destination.exists():
        raise ValueError('REFUSE_OCCUPIED_TRIAL_DESTINATION')
    destination.mkdir(parents=True)
    pool = eligible(sources)
    private = destination / 'private'
    private.mkdir()
    roster, selected, originals = {}, [], []
    for domain, rows in pool.items():
        if len(rows) < 2:
            (private / 'selection_failure.json').write_text(json.dumps({'domain': domain, 'eligible': len(rows)}))
            raise ValueError('INSUFFICIENT_ELIGIBLE_CASES:' + domain)
        rank = lambda r: digest(protocol_bytes + domain.encode() + r['origin'].encode())
        ordered = sorted(rows, key=rank)
        roster[domain] = [{'origin': r['origin'], 'source_sha256': digest(r['raw']), 'rank': rank(r)} for r in ordered]
        for i, row in enumerate(ordered[:2]):
            case_id = domain[:1] + '-' + rank(row)[:12]
            withdrawn = domain in ('aerospace', 'mathematics') and i == 1
            context = {'source_receipt': 'WITHDRAWN' if withdrawn else 'CURRENT',
                       'event': 'Explicit experimental source-authority withdrawal; source bytes remain visible.' if withdrawn else 'Pinned published case-study/test source, not operational approval.'}
            card = {'case_id': case_id, 'domain': domain, 'context': context,
                    'provenance': {**p['repositories'][domain], 'origin': row['origin'] if domain != 'mathematics' else 'withheld-until-adjudication-to-mask-outcome-bearing-filenames', 'source_sha256': digest(row['raw'])},
                    **row['view']}
            selected.append(card)
            original = {'case_id': case_id, 'domain': domain, 'origin': row['origin'],
                        'raw_source': row['raw'].decode('utf-8'),
                        'hidden_external_status': row.get('hidden_external_status'),
                        'source_sha256': digest(row['raw'])}
            if 'expected_raw' in row:
                original['raw_expected_json'] = row['expected_raw'].decode('utf-8')
            originals.append(original)
    for arm in ('mathgraph', 'conventional'):
        root = destination / arm
        (root / 'inputs').mkdir(parents=True)
        (root / 'work').mkdir()
        (root / 'results').mkdir()
        (root / 'kit').mkdir()
        for card in selected:
            (root / 'inputs' / (card['case_id'] + '.json')).write_text(json.dumps(card, indent=2, ensure_ascii=False) + '\n')
        (root / 'kit/warrant_resolution.py').write_bytes(core)
        (root / 'kit/README.txt').write_text('Existing MathGraph warrant resolver, identical in both arms. It assumes externally qualified receipts; it does not verify source interpretation or solver/certificate correctness. No outcomes or suspected defects are supplied.\n')
    (private / 'originals.json').write_text(json.dumps(originals, indent=2, ensure_ascii=False) + '\n')
    (private / 'selection_roster.json').write_text(json.dumps(roster, indent=2) + '\n')
    receipt = {'freeze_commit': freeze, 'protocol_sha256': digest(protocol_bytes),
               'eligible': {k: len(v) for k, v in pool.items()},
               'cases': [{'case_id': c['case_id'], 'domain': c['domain'], 'input_sha256': digest(json.dumps(c, indent=2, ensure_ascii=False).encode() + b'\n')} for c in selected],
               'selection_seconds': time.time() - start,
               'holdout_boundary': p['holdout'], 'context_interventions': p['controls']}
    (destination / 'selection_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'eligible': receipt['eligible'], 'cases': receipt['cases'], 'freeze_commit': freeze}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze', required=True)
    a = parser.parse_args()
    select(a.sources.resolve(), a.out.resolve(), a.freeze)
