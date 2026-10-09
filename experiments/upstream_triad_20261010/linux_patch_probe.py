#!/usr/bin/env python3
"""Validate minimal Linux rvgen DA fail-closed patch against pinned official fixtures."""
import difflib
import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import urllib.request

LINUX_SHA = 'af32da41b0327b9c6a37856ba82b6760d6c8d10e'
AUTOMATA_PATH = 'tools/verification/rvgen/rvgen/automata.py'
FIXTURES = [
    'tools/verification/rvgen/tests/specs/test_da.dot',
    'tools/verification/rvgen/tests/specs/test_da2.dot',
    'tools/verification/rvgen/tests/specs/test_ha.dot',
    'tools/verification/models/wwnr.dot',
    'tools/verification/models/wip.dot',
    'tools/verification/models/stall.dot',
    'tools/verification/models/deadline/nomiss.dot',
    'tools/verification/models/sched/nrp.dot',
    'tools/verification/models/sched/opid.dot',
    'tools/verification/models/sched/sco.dot',
    'tools/verification/models/sched/scpd.dot',
    'tools/verification/models/sched/snep.dot',
    'tools/verification/models/sched/snroc.dot',
    'tools/verification/models/sched/sssw.dot',
    'tools/verification/models/sched/sts.dot',
]

def fetch(path):
    url = f'https://raw.githubusercontent.com/torvalds/linux/{LINUX_SHA}/{path}'
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read().decode()

def load_module(module_name, filename):
    spec = importlib.util.spec_from_file_location(module_name, filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

def main():
    source = fetch(AUTOMATA_PATH)
    anchor = '            matrix[states_dict[src]][events_dict[event]] = dst'
    marker = '        transitions.sort(key=lambda t : (t.src, t.event))\n        return transitions'
    replacement = '''        transitions.sort(key=lambda t : (t.src, t.event))
        previous_key = None
        for transition in transitions:
            key = (transition.src, transition.event)
            if key == previous_key:
                raise AutomataError(
                    f"Duplicate transition for event {transition.event} in state {transition.src}")
            previous_key = key
        return transitions'''
    assert source.count(anchor) == 1 and source.count(marker) == 1, "upstream source changed"
    fixed = source.replace(marker, replacement)
    diff = ''.join(difflib.unified_diff(
        source.splitlines(keepends=True), fixed.splitlines(keepends=True),
        fromfile='a/tools/verification/rvgen/rvgen/automata.py',
        tofile='b/tools/verification/rvgen/rvgen/automata.py'))
    pathlib.Path('linux-rvgen-determinism.patch').write_text(diff)
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        (root/'orig.py').write_text(source)
        (root/'fixed.py').write_text(fixed)
        orig = load_module('rvgen_orig', root/'orig.py')
        patched = load_module('rvgen_patched', root/'fixed.py')
        successes = []
        expected_invalid = []
        for i,path in enumerate(FIXTURES):
            dot = root/f'fixture_{i}.dot'
            dot.write_text(fetch(path))
            try:
                before = orig.Automata(str(dot))
            except orig.AutomataError as e:
                expected_invalid.append((path, type(e).__name__, str(e)[:80]))
                continue
            after = patched.Automata(str(dot))
            assert [[str(x) for x in row] for row in before.function] == [
                [str(x) for x in row] for row in after.function
            ], path
            assert [s.name for s in before.states] == [s.name for s in after.states], path
            assert list(map(str,before.events)) == list(map(str,after.events)), path
            successes.append(path)
        assert len(successes) >= 10, (successes, expected_invalid)
        base = fetch('tools/verification/rvgen/tests/specs/test_da.dot')
        old_edge = '"state_a" -> "state_b" [ label = "event_1" ];'
        assert base.count(old_edge) == 1
        mutated = base.replace(old_edge, '"state_a" -> "state_b" [ label = "event_2" ];')
        pathlib.Path('linux-ambiguous-mutant.dot').write_text(mutated)
        (root/'mutant.dot').write_text(mutated)
        original = orig.Automata(str(root/'mutant.dot'))
        assert original.function, 'negative control not accepted by original'
        try:
            patched.Automata(str(root/'mutant.dot'))
        except patched.AutomataError as e:
            assert 'Duplicate transition' in str(e)
            print('PATCHED_RVGEN_REJECTED_MUTANT',str(e))
        else:
            raise AssertionError('patched rvgen still accepted contradictory transitions')
        # Edge case: the matrix's empty-cell sentinel is also a legal
        # syntactic DOT state name. The previous sentinel-based patch can
        # silently accept a collision when this destination is visited first.
        sentinel = base.replace('state_b', 'INVALID_STATE')
        bad_label = '"state_a" -> "INVALID_STATE" [ label = "event_1" ];'
        assert sentinel.count(bad_label) == 1
        sentinel = sentinel.replace(
            bad_label, '"state_a" -> "INVALID_STATE" [ label = "event_2" ];')
        reserved_path = root / 'sentinel_mutant.dot'
        reserved_path.write_text(sentinel)
        model = orig.Automata(str(reserved_path))
        offenders = [tr for tr in model.transitions
                     if str(tr.src) == 'state_a' and str(tr.event) == 'event_2']
        assert len(offenders) == 2
        offenders.sort(key=lambda tr: 0 if str(tr.dst) == 'INVALID_STATE' else 1)
        previous_guard = (
            '            if matrix[states_dict[src]][events_dict[event]] != self.invalid_state_str:\n'
            '                raise AutomataError("duplicate")\n' + anchor)
        legacy_source = source.replace(anchor, previous_guard)
        legacy_path = root / 'legacy.py'
        legacy_path.write_text(legacy_source)
        legacy = load_module('rvgen_legacy_guard', legacy_path)
        legacy_obj = object.__new__(legacy.Automata)
        legacy_obj.__dict__.update(model.__dict__)
        legacy_obj.transitions = [
            tr for tr in model.transitions
            if not (str(tr.src) == 'state_a' and str(tr.event) == 'event_2')
        ] + offenders
        # Demonstrate an actual pre-fix false negative under a deterministic
        # ordering, independently of the process's hash randomisation.
        legacy.Automata._Automata__create_matrix(legacy_obj)
        try:
            patched.Automata(str(reserved_path))
        except patched.AutomataError as e:
            assert 'Duplicate transition' in str(e)
        else:
            raise AssertionError('independent occupancy guard missed sentinel collision')
        print('LINUX_SENTINEL_COUNTEREXAMPLE old_guard_accepted, seen_guard_rejected')
        print('LINUX_PATCH_QUALIFIED', {
            'upstream_sha': LINUX_SHA,
            'baseline_fixture_count': len(FIXTURES),
            'positive_cases_preserved': len(successes),
            'original_error_fixtures': expected_invalid,
            'diff_sha256': hashlib.sha256(diff.encode()).hexdigest(),
            'patched_source_sha256': hashlib.sha256(fixed.encode()).hexdigest(),
        })
        print('LINUX_SCOPE: exact rvgen parser/matrix and pinned DOT fixtures; no kernel boot test')

if __name__=='__main__':
    main()
