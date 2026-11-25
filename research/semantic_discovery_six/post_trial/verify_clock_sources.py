"""Read-only static qualification of the post-trial clock evidence.

Requires the pinned public Git repositories under ROOT/sources. Writes only
the requested report. Does not compile or simulate a Simulink/Lustre model.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

FRET = 'cf0f913cc15c41705e803593297e89cd6056b839'
MODELS = '133447a8943721eaa1d16acf1ba5845b67a98df1'


def audit(root):
    identities = []

    def blob(repository, revision, path):
        cwd = root / 'sources' / repository
        data = subprocess.check_output(['git', 'show', revision + ':' + path], cwd=cwd)
        git_hash = subprocess.check_output(['git', 'rev-parse', revision + ':' + path], cwd=cwd, text=True).strip()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == git_hash
        identities.append({'repository': repository, 'commit': revision, 'path': path,
                           'git_blob': git_hash, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        return data

    timing_path = 'fret-electron/docs/_media/user-interface/examples/timing.md'
    timing = blob('aerospace', FRET, timing_path).decode()
    assert 'Time units are currently ignored' in timing
    assert 'which are in charge of interpreting the time units' in timing
    instructions = blob('aerospace', FRET, 'caseStudies/LMCPS/LMCPS_instructions.md').decode()
    assert 'https://github.com/hbourbouh/lm_challenges' in instructions
    requirements = json.loads(blob('aerospace', FRET, 'caseStudies/LMCPS/LM_requirements.json'))
    selected = next(r for r in requirements['requirements'] if r['reqid'] == 'NN-003A')
    specification = blob('lm_challenges', MODELS, 'FRET_CoCoSim/5_nn/FRET/NNSpec.lus').decode()
    source_texts = re.findall(r'\(\* Req text: (.*?)\*\)', specification, re.S)
    normalize = lambda text: ' '.join(text.split())
    assert normalize(selected['fulltext']) in [normalize(t) for t in source_texts]
    assert 'guarantee "NN-003A" OT(200,0,FTP)' in specification
    original_configurations = []
    for path in ['FRET_CoCoSim/5_nn/nn_12B.mdl', 'original_models/5_nn/nn_12B.mdl']:
        text = blob('lm_challenges', MODELS, path).decode('latin-1')
        fixed = re.findall(r'^\s*FixedStep\s+"([^"]+)"', text, re.M)
        solver = re.findall(r'^\s*Solver\s+"([^"]+)"', text, re.M)
        assert fixed == ['auto'] and solver == ['ode45']
        original_configurations.append({'path': path, 'FixedStep': fixed[0], 'Solver': solver[0]})
    configurations = []
    for filename in ['nn_12B_with_contracts.slx', 'nn_12B_with_contracts_PP.slx']:
        path = 'FRET_CoCoSim/5_nn/CoCoSim/' + filename
        raw = blob('lm_challenges', MODELS, path)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = ET.fromstring(archive.read('simulink/configSetInfo.xml'))
            active = [e for e in info.iter('ConfigSet') if e.get('Active') == 'true']
            assert len(active) == 1
            part = active[0].get('PartName').lstrip('/')
            config = ET.fromstring(archive.read(part))
            values = {}
            for key in ['FixedStep', 'Solver', 'StartTime', 'StopTime']:
                found = [e.text for e in config.iter('P') if e.get('Name') == key]
                assert len(found) == 1
                values[key] = found[0]
            assert float(values['FixedStep']) == 1.0
            assert values['Solver'] == 'FixedStepDiscrete'
            assert float(values['StartTime']) == 0.0
            assert float(values['StopTime']) == 100.0
            diagram = ET.fromstring(archive.read('simulink/blockdiagram.xml'))
            contracts = [e.get('Name') for e in diagram.iter('Block') if e.get('Name') == 'nn_12B_NNSpec']
            assert len(contracts) == 1
            sources = []
            for block in diagram.iter('Block'):
                if block.get('BlockType') != 'FromWorkspace':
                    continue
                sample = [e.text for e in block if e.tag == 'P' and e.get('Name') == 'SampleTime']
                assert len(sample) == 1 and float(sample[0]) == 1.0
                sources.append({'name': block.get('Name'), 'sample_time': sample[0]})
            assert len(sources) == 3
            configurations.append({'path': path, 'active_configuration': part, 'parameters': values,
                                   'contract_subsystem': contracts[0], 'workspace_sources': sources})
    return {'status': 'PASSED_STATIC_SOURCE_QUALIFICATION', 'identities': identities,
            'timing_documentation': {'path': timing_path, 'units_are_ignored': True,
                                    'physical_interpretation_delegated_to_downstream_tools': True},
            'matching_named_requirement': selected['reqid'],
            'matching_requirement_text': selected['fulltext'], 'configurations': configurations,
            'base_mdl_configurations': original_configurations,
            'vendor_parameter_semantics': 'https://www.mathworks.com/help/simulink/gui/fixedstepsizefundamentalsampletime.html',
            'warranted_scope': 'Stored active settings of these exact two linked verification models: base fixed step 1, starting at 0, stopping at 100. Vendor documentation specifies fixed step size in seconds.',
            'not_established': ['Native MATLAB/Simulink compilation or execution', 'Native Lustre/CoCoSpec execution',
                                'Exact end-to-end binding of the frozen scalar abstraction to model behavior',
                                'A completed 200-second simulation', 'Continuous-time or deployed-system correctness',
                                'A new NASA defect', 'Comparative MathGraph advantage'],
            'original_frozen_trial_outcomes': 'UNCHANGED',
            'novelty': 'The unit-handling boundary was documented before the trial; investigators rediscovered it from restricted inputs.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root.resolve())
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'git_blobs_verified': len(report['identities']),
                      'active_models_checked': len(report['configurations']), 'output': str(args.out)}))
