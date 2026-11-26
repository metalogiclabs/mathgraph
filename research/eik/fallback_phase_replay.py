"""Replay a complete numerical cell where reusing a rounding correction fails.

The fixture is a projection of the rejected packed17/cap64 experiment, not a
competition candidate. Its 131,072-word cell was selected after the failure.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from hot_path_hints import BASE


FIXTURE = {
    'lo': 3197239296, 'hi': 3197370368, 'bits': 17,
    'packed': 872415794, 'base': 1064598608,
    'c1': 12614942, 'c2': -25339, 'cubic': 562,
    'original_source_sha256': '5c301ea63a4770bcae416180b6ecd3f86c241788b27b757834911dc59d662174',
    'first_input': 0xbe92003a, 'control_output': 0x3f407c39,
    'legacy_output': 0x3f407c38,
}


def project(source, legacy):
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong baseline')
    f = FIXTURE
    anchor = '        if (r_w <= 0xBF801000u) {'
    if source.count(anchor) != 1:
        raise ValueError('negative exp anchor')
    body = f'''        /* Rejected synthesis fixture: a complete 2^17-word cell. */
        if (r_w >= {f['lo']}u && r_w < {f['hi']}u) {{
            uint32_t u=r_w<<15, packed={f['packed']}u;
            int32_t s={f['c2']}+r_mulhsx_r({f['cubic']},u);
            s={f['c1']}+r_mulhsx_r(s,u);
            uint32_t q=packed+(uint32_t)r_mulhsx_r(s,u);
            if((q<<24)>packed) return {f['base']}u-(q>>8);
'''
    body += (f'            r_cV={f["base"]}u-(q>>8)+1u;goto r_negres_;\n'
             if legacy else '            r_cB=&r_exp8_r;goto r_negmain_;\n')
    return source.replace(anchor, body+'        }\n'+anchor)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--header', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--kit', type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    a.out = a.out.resolve()
    source = a.baseline.read_text()
    if hashlib.sha256(source.encode()).hexdigest() != BASE:
        raise ValueError('wrong baseline')
    sources = {'control': source, 'legacy': project(source, True), 'general': project(source, False)}
    files = {}
    for name, text in sources.items():
        c, so = a.out/(name+'.c'), a.out/(name+'.so')
        c.write_text(text)
        command = ['gcc', '-std=c11', '-O2', '-fno-builtin', '-ftrivial-auto-var-init=zero',
                   '-fPIC', '-shared', '-include', str(a.header.resolve()), str(c), '-o', str(so)]
        subprocess.run(command, check=True)
        files[name] = {'source_sha256': hashlib.sha256(c.read_bytes()).hexdigest(),
                       'library_sha256': hashlib.sha256(so.read_bytes()).hexdigest(), 'compile': command}
    harness = Path(__file__).with_name('full_range_diff.c')
    binary = a.out/'compare'
    subprocess.run(['gcc', '-std=c11', '-O2', str(harness), '-ldl', '-o', str(binary)], check=True)
    results = {}
    for name, expected_exit in [('legacy', 1), ('general', 0)]:
        command = [str(binary), str(a.out/'control.so'), str(a.out/(name+'.so')),
                   'eik_exp', str(FIXTURE['lo']), str(FIXTURE['hi'])]
        run = subprocess.run(command, text=True, capture_output=True)
        (a.out/(name+'-full-cell.txt')).write_text(run.stdout+run.stderr)
        if run.returncode != expected_exit:
            raise RuntimeError((name, run.returncode, run.stdout, run.stderr))
        results[name] = json.loads(run.stdout.splitlines()[-1])
    if a.kit:
        import sys
        sys.path.insert(0, str(a.kit.resolve()))
        from eik import toolchain as T
        from eik.emu import Core
        from eik.fingerprint import ids
        cases = {}
        for name in sources:
            core = Core(T.guest_image(a.out/(name+'.c'), 'rv32im'), 'rv32im')
            got, count = core.call('exp', FIXTURE['first_input'])
            cases[name] = {'output': got, 'instructions': count}
        assert cases['control']['output'] == FIXTURE['control_output']
        assert cases['legacy']['output'] == FIXTURE['legacy_output']
        assert cases['general']['output'] == FIXTURE['control_output']
        results['rv32im'] = cases
        results['fingerprint'] = ids()
    receipt = {'state': 'FINITE_COUNTERMODEL', 'kind': 'ROUNDING_CORRECTION_PHASE_MISMATCH',
               'boundary': 'Source-relative complete-cell native replay and optional fixed RV32IM case; no competition admission',
               'baseline_sha256': BASE, 'fixture': FIXTURE, 'files': files, 'results': results}
    (a.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'state': receipt['state'], 'results': results}, indent=2))


if __name__ == '__main__':
    main()
