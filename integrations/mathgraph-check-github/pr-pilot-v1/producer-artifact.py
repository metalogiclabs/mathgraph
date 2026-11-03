"""Bounded ZIP reader for authenticated producer artifacts; never extracts files."""
import hashlib
import io
import json
import re
import sys
import zipfile


def read_artifact(data):
    if len(data) > 20 * 1024 * 1024:
        raise ValueError('PRODUCER_ARCHIVE_TOO_LARGE')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist()
        if len(infos)>512 or len({i.filename for i in infos})!=len(infos):
            raise ValueError('PRODUCER_ARCHIVE_AMBIGUOUS')
        if sum(i.file_size for i in infos)>40*1024*1024:
            raise ValueError('PRODUCER_ARCHIVE_TOO_LARGE')
        names=[i.filename for i in infos if '/' not in i.filename and i.filename.endswith('.json')]
        if any(not re.fullmatch(r'[a-z][a-z0-9_-]*\.json',n) for n in names):
            raise ValueError('PRODUCER_JSON_NAME_INVALID')
        raw={n:z.read(n).decode('utf-8') for n in names}
        manifest=json.loads(raw['manifest.json'])
        if sorted(manifest['hashes'])!=sorted(n for n in raw if n!='manifest.json'):
            raise ValueError('PRODUCER_MANIFEST_INCOMPLETE')
        for n,h in manifest['hashes'].items():
            if hashlib.sha256(raw[n].encode()).hexdigest()!=h:
                raise ValueError('PRODUCER_BYTES_CHANGED')
        return raw


if __name__=='__main__':
    try:
        data=sys.stdin.buffer.read(20*1024*1024+1)
        print(json.dumps(read_artifact(data)))
    except Exception:
        print(json.dumps({'error':'PRODUCER_ARTIFACT_INVALID'}))
        sys.exit(1)
