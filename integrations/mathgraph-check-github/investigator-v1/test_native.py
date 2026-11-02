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
