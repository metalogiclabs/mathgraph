import hashlib,io,json,zipfile,unittest,importlib.util
from pathlib import Path
path=Path(__file__).resolve().parents[2]/'integrations/mathgraph-check-github/pr-pilot-v1/producer-artifact.py'
spec=importlib.util.spec_from_file_location('producer_artifact',path);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)

class ArchiveTests(unittest.TestCase):
    def archive(self,changed=False,extra=False,duplicate=False):
        raw='{"state":"original"}';manifest={'hashes':{'state.json':hashlib.sha256(raw.encode()).hexdigest()}}
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('state.json','{"state":"changed"}' if changed else raw)
            z.writestr('manifest.json',json.dumps(manifest))
            if extra:z.writestr('extra.json','{}')
            if duplicate:z.writestr('state.json',raw)
        return b.getvalue()
    def test_actual_bytes_are_returned_not_a_favorable_label(self):
        self.assertEqual(reader.read_artifact(self.archive())['state.json'],'{"state":"original"}')
    def test_changed_bytes_missing_seal_and_duplicate_names_fail(self):
        for changes in [dict(changed=True),dict(extra=True),dict(duplicate=True)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):reader.read_artifact(self.archive(**changes))
    def test_nonzip_and_oversize_fail(self):
        with self.assertRaises(Exception):reader.read_artifact(b'not a zip')
        with self.assertRaises(ValueError):reader.read_artifact(b'x'*(20*1024*1024+1))

if __name__=='__main__':unittest.main()
