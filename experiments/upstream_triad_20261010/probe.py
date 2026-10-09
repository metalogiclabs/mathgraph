#!/usr/bin/env python3
"""Bounded LLVM and Linux upstream opportunity probes; no universal claims."""
import argparse
import collections
import ctypes
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.request

LINUX_SHA = 'af32da41b0327b9c6a37856ba82b6760d6c8d10e'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def llvm():
    source = """#include <stdint.h>
extern uint8_t helper(uint8_t);
uint8_t src(uint8_t x) { return (uint8_t)(helper(x) ^ x); }
uint8_t tgt(uint8_t x) { return (uint8_t)((uint8_t)(x+1) ^ x); }
"""
    helpers = {
        'valid': '#include <stdint.h>\nuint8_t helper(uint8_t x) { return (uint8_t)(x+1); }\n',
        'mutant': '#include <stdint.h>\nuint8_t helper(uint8_t x) { return (uint8_t)(x+2); }\n',
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root/'caller.c').write_text(source)
        outcomes = {}
        for name, helper in helpers.items():
            (root/f'{name}.c').write_text(helper)
            so = root/f'{name}.so'
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-o', str(so),
                            str(root/'caller.c'), str(root/f'{name}.c')], check=True)
            lib = ctypes.CDLL(str(so))
            for function in (lib.src, lib.tgt):
                function.argtypes = [ctypes.c_uint8]
                function.restype = ctypes.c_uint8
            differences = [(x, lib.src(x), lib.tgt(x))
                           for x in range(256) if lib.src(x) != lib.tgt(x)]
            outcomes[name] = {'cases': 256, 'differences': len(differences),
                              'first_difference': differences[:1],
                              'binary_sha256': sha(so.read_bytes())}
        assert outcomes['valid']['differences'] == 0, outcomes
        assert outcomes['mutant']['differences'] == 256, outcomes
        print('LLVM_EXHAUSTIVE_8BIT_PROBE', json.dumps(outcomes, sort_keys=True))
        print('LLVM_BOUNDARY: finite-domain behaviour only; not Alive2 nor full LLVM IR')

def fetch_pinned(path):
    url = f'https://raw.githubusercontent.com/torvalds/linux/{LINUX_SHA}/{path}'
    with urllib.request.urlopen(url, timeout=45) as resp:
        data = resp.read()
    if not data:
        raise RuntimeError('empty pinned upstream response')
    return data

def linux():
    upstream_py = fetch_pinned('tools/verification/rvgen/rvgen/automata.py')
    upstream_dot = fetch_pinned('tools/verification/rvgen/tests/specs/test_da.dot')
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        package = root / 'rvgen'
        package.mkdir()
        (package/'__init__.py').write_text('')
        (package/'automata.py').write_bytes(upstream_py)
        baseline = root/'test_da.dot'
        baseline.write_bytes(upstream_dot)
        mutant = root/'test_da_ambiguous.dot'
        original = upstream_dot.decode('utf-8')
        last_brace = original.rfind('}')
        assert last_brace >= 0
        mutant.write_text(original[:last_brace] +
            '    "state_a" -> "state_b" [ label = "event_2" ];\n' +
            original[last_brace:])
        sys.path.insert(0, str(root))
        from rvgen.automata import Automata, AutomataError
        good = Automata(str(baseline))
        bad = Automata(str(mutant))
        def duplicates(aut):
            groups = collections.defaultdict(set)
            counts = collections.Counter()
            for transition in aut.transitions:
                k = (transition.src, transition.event)
                groups[k].add(transition.dst)
                counts[k] += 1
            return {str(k): {'count': counts[k], 'destinations': sorted(group)}
                    for k, group in groups.items() if counts[k] > 1}
        assert not duplicates(good)
        ambiguity = duplicates(bad)
        assert "('state_a', 'event_2')" in ambiguity, ambiguity
        assert len(ambiguity["('state_a', 'event_2')"]['destinations']) == 2
        assert bad.function
        def require_deterministic(aut):
            dups = duplicates(aut)
            if dups:
                raise AutomataError(f'non-deterministic (state,event) edges: {dups}')
            return aut
        require_deterministic(good)
        rejected = False
        try:
            require_deterministic(bad)
        except AutomataError:
            rejected = True
        assert rejected
        detail = {}
        snippet = ('from rvgen.automata import Automata; import sys; '
                   'a=Automata(sys.argv[1]); '
                   'print(a.function[[x.name for x in a.states].index("state_a")][a.events.index("event_2")])')
        for seed in range(32):
            env = dict(os.environ, PYTHONPATH=str(root), PYTHONHASHSEED=str(seed))
            proc = subprocess.run([sys.executable, '-c', snippet, str(mutant)], env=env,
                                  text=True, capture_output=True, check=True)
            target = proc.stdout.strip()
            detail.setdefault(target, []).append(seed)
        report = {
            'upstream_linux_sha': LINUX_SHA,
            'automata_py_sha256': sha(upstream_py),
            'base_dot_sha256': sha(upstream_dot),
            'baseline_deterministic': True,
            'mutant_duplicate': ambiguity,
            'upstream_accepts_ambiguous_mutant': True,
            'fail_closed_guard_rejects_mutant': rejected,
            'unpatched_targets_over_32_hash_seeds': detail,
        }
        print('LINUX_RVGEN_AMBIGUOUS_DA_PROBE', json.dumps(report, sort_keys=True))
        if len(detail) == 1:
            print('LINUX_NOTE: ambiguous input accepted but seed variance not observed')
        else:
            print('LINUX_NOTE: same input produces different transition targets by hash seed')
        print('LINUX_BOUNDARY: parser/matrix diagnostic, not live kernel verification')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target', choices=['llvm','linux'])
    {'llvm': llvm, 'linux': linux}[parser.parse_args().target]()
