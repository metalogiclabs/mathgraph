"""Independent finite XML acceptance reference; no subject code is executed."""
import hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
p=Path(__file__);data=p.with_name('report-cases.json').read_bytes();rows=json.loads(data)
records=[]
for c in rows:
 try: ET.fromstring(c['input']);accepted=True
 except ET.ParseError: accepted=False
 records.append({**c,'observed_acceptance':accepted})
result={'runner_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'corpus_sha256':hashlib.sha256(data).hexdigest(),'records':records}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
