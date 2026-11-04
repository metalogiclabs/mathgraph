import unittest
from native import junit_result, sandbox_command
class NativeTests(unittest.TestCase):
    def test_junit_success_and_failure(self):
        self.assertEqual(junit_result('<testsuites><testsuite tests="2" failures="1" errors="0" skipped="0"/></testsuites>')['failures'],1)
    def test_missing_xml_cannot_be_pass(self):
        self.assertEqual(junit_result('')['tests'],0)
    def test_missing_counters_are_not_assumed_success(self):
        with self.assertRaises(ValueError): junit_result('<testsuites><testsuite/></testsuites>')
    def test_container_has_no_network_or_privileged_access(self):
        cmd=sandbox_command('image','name','/tmp/repo','/tmp/audit','/tmp/results',['python','-m','pytest'])
        self.assertIn('none',cmd);self.assertIn('--read-only',cmd);self.assertIn('--cap-drop=ALL',cmd)
        self.assertFalse(any('OPENAI' in x or 'TOKEN' in x or 'docker.sock' in x for x in cmd))
        self.assertIn('/tmp/audit:/audit:ro',cmd)
if __name__=='__main__': unittest.main()

class ProbeShapeTests(unittest.TestCase):
    def test_empty_function_refused(self):
        import native
        with self.assertRaises(ValueError): native.validate_probe('def test_x():\n    pass\n')
    def test_assertion_probe_supported(self):
        import native
        self.assertTrue(native.validate_probe('def test_x():\n    assert 2 == 2\n'))
    def test_unsafe_import_refused(self):
        import native
        with self.assertRaises(ValueError): native.validate_probe('import os\ndef test_x():\n    assert os.getenv("KEY") is None\n')

class MetadataTests(unittest.TestCase):
    def test_static_package_metadata_without_running_build_backend(self):
        import tempfile
        from pathlib import Path
        import native
        from importlib.metadata import PathDistribution
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'pyproject.toml').write_text('[tool.poetry]\nname="example-package"\nversion="1.2.3"\n')
            output=native.initialize_metadata(root)
            self.assertEqual(PathDistribution(output).version,'1.2.3')
            self.assertFalse((root/'example_package').exists())

class FixtureMountTests(unittest.TestCase):
    def test_only_fixture_data_mount_is_writable(self):
        from native import sandbox_command
        cmd=sandbox_command('image','n','/tmp/repo','/tmp/audit','/tmp/results',['python'],data='/tmp/data')
        self.assertIn('/tmp/data:/repo/data:rw',cmd)
        self.assertIn('/tmp/repo:/repo:ro',cmd)
        self.assertIn('/tmp/audit:/audit:ro',cmd)

class SubjectExecutionTests(unittest.TestCase):
    def test_native_receipt_distinguishes_subject_execution_from_trivial_assertions(self):
        import json, os, subprocess, sys, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix='mg-native-reach-') as d:
            root=Path(d);repo=root/'repo';audit=root/'audit';repo.mkdir();audit.mkdir()
            (repo/'target.py').write_text('def increment(x):\n    return x + 1\n')
            (audit/'test_reach.py').write_text(
                'from target import increment\n'
                'def test_calls_source():\n    assert increment(2) == 3\n'
                'def test_asserts_true():\n    assert 1 + 1 == 2\n')
            receipt=root/'cases.json'
            env={**os.environ,'PYTHONPATH':str(Path(__file__).parent)+os.pathsep+str(repo),
                'MG_CASES_FILE':str(receipt),'MG_AUDIT_DIR':str(audit),
                'MG_SUBJECT_FILES':json.dumps([str(repo/'target.py')])}
            p=subprocess.run([sys.executable,'-m','pytest','-q','-p','mg_native_plugin',
                              '-p','no:cacheprovider',str(audit/'test_reach.py')],
                             capture_output=True,text=True,cwd=root,env=env,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            results=json.loads(receipt.read_text())
            by_name={x['id'].split('::')[-1]:x for x in results}
            self.assertGreater(by_name['test_calls_source']['subject_lines_reached'],0)
            self.assertEqual(by_name['test_asserts_true']['subject_lines_reached'],0)
