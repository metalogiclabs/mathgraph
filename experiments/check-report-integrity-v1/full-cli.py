from pathlib import Path
import hashlib,json,subprocess,sys,os
root=Path(sys.argv[1]).resolve();controller=Path(__file__).resolve().parent;out=Path('report-full-cli-evidence').resolve();out.mkdir(exist_ok=True)
source=root/'Tests/SuiteRunner/Reports.lean';original=source.read_text();expected=(controller/'original.lean').read_text();assert original==expected
candidate=(controller/'candidate.lean').read_text();assert hashlib.sha256(candidate.encode()).hexdigest()=='6a417259978445c5c5609910fcd5d514c1ddbf9cd7e17678d6fecd03b4381513'
def run(label,args,timeout=1500):
 p=subprocess.run(args,cwd=root,text=True,capture_output=True,timeout=timeout);(out/(label+'.log')).write_text(p.stdout+p.stderr);return p.returncode
fixtures=json.loads((Path(__file__).resolve().parents[2]/'integrations/mathgraph-check-github/pr-pilot-v1/report-cases.json').read_text())
selected=[c for c in fixtures if c['group'] in ['new_refusals','valid_controls']]
results={}
for arm,text in [('original',original),('candidate',candidate),('withdrawn',original)]:
 source.write_text(text);assert run(arm+'-build',['lake','build','suiterunner'])==0
 rows=[]
 for c in selected:
  d=out/arm/c['id'];d.mkdir(parents=True,exist_ok=True);(d/'python-ffi-junit.xml').write_text(c['input'])
  code=run(arm+'-'+c['id'],['.lake/build/bin/suiterunner','--reports',str(d)],120)
  rows.append({'id':c['id'],'expected_acceptance':c['accepted'],'exit':code,'html_written':(d/'python-ffi-tests.html').exists()})
 results[arm]=rows
 if arm=='candidate':
  assert all(r['exit']==(0 if r['expected_acceptance'] else 1) and r['html_written']==r['expected_acceptance'] for r in rows),rows
  assert run('candidate-full-build',['lake','build'])==0
  assert run('candidate-test-executables',['lake','build','tests','demo','limittests'])==0
  assert run('candidate-all-tests',['lake','run','run-all-tests'])==0
 else:assert all(r['exit']==0 and r['html_written'] for r in rows),rows
assert results['original']==results['withdrawn']
(out/'result.json').write_text(json.dumps({'status':'WARRANTED_BOUNDED','source_head':os.environ['SUBJECT_HEAD'],'scope':'Actual full pinned repository, original Reports import retained, actual suiterunner --reports; full candidate build and repository tests; withdrawal restores six false-green cases. Not general XML conformance.','arms':results},indent=2))
print('Actual CLI: six malformed reports green originally, refused after repair; six valid controls preserved; withdrawal restores green. Full candidate repository build/tests passed.')
