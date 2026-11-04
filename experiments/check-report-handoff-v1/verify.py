from pathlib import Path
import subprocess,sys,json,hashlib,shutil,time
root=Path(sys.argv[1]).resolve();arm=sys.argv[2];bundle=Path(__file__).resolve().parent
out=Path('handoff-'+arm).resolve();out.mkdir(exist_ok=True)
cases=json.loads((bundle/'cases.json').read_text());source=root/'Tests/SuiteRunner/Reports.lean';original=source.read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='670b65c829bffcc3dcafb2fbdfe8aee5a1ec8dede7ce4d0547d11bb600848fae'
checks=[];observations={};started=time.time()
def run(label,args,timeout=1800):
 t=time.time()
 try:
  p=subprocess.run(args,cwd=root,text=True,capture_output=True,timeout=timeout)
  code=p.returncode;log=p.stdout+p.stderr
 except subprocess.TimeoutExpired as e:
  code=124;log='TIMEOUT: '+str(e)
 (out/(label+'.log')).write_text(log)
 checks.append({'name':label,'command':args,'exit':code,'seconds':round(time.time()-t,2)})
 print(label,code,flush=True)
 return code
def observe(label,expected_original):
 rows=[]
 for c in cases:
  folder=out/label/c['id'];folder.mkdir(parents=True,exist_ok=True)
  (folder/'python-ffi-junit.xml').write_text(c['input'])
  code=run(label+'-'+c['id'],['.lake/build/bin/suiterunner','--reports',str(folder)],120)
  html=(folder/'python-ffi-tests.html').exists()
  accepted=True if expected_original and c['group']=='new_refusals' else c['accepted']
  rows.append({'id':c['id'],'group':c['group'],'requirement_accepts':c['accepted'],'exit':code,'html_written':html,'matches_observed_arm':code==(0 if accepted else 1) and html==accepted})
 observations[label]=rows
 return all(r['matches_observed_arm'] for r in rows)
try:
 if arm=='candidate':
  assert run('patch-check',['git','apply','--check',str(bundle/'report-reader.patch')])==0
  assert run('patch-apply',['git','apply',str(bundle/'report-reader.patch')])==0
  assert hashlib.sha256(source.read_bytes()).hexdigest()=='16d7ddff01434a386cd08a27b2e7a025e857bc182e2558dbfab28d85e529fb26'
 commands=[('full-build',['lake','build']),('test-executables',['lake','build','tests','demo','limittests'])]
 for gate in ['check-scripts-lean','check-theorem-keyword','check-import-closure','check-reflection-index','check-closure-log','check-serialization-proofs','check-gate-vocab','run-all-tests']:
  commands.append((gate,['lake','run',gate]))
 commands.append(('suiterunner',['lake','exe','suiterunner']))
 for label,args in commands:run(label,args)
 ready=run('reports-build',['lake','build','suiterunner'])==0
 correct=observe(arm,arm=='baseline') if ready else False
 battery_ok=all(c['exit']==0 for c in checks)
 if arm=='candidate' and ready:
  source.write_text(original)
  if run('withdrawn-build',['lake','build','suiterunner'])==0:correct=observe('withdrawn',True) and correct
  else:correct=False
 result={'status':'PASS' if battery_ok and correct else 'INCOMPLETE_OR_FAILED','upstream_branch':'fix-a-grammar-completeness','upstream_head':'8fdc991b6dfebe1114858f6649e15c5cea2e5eff','arm':arm,'checks':checks,'observations':observations,'battery_all_passed':battery_ok,'finite_observations_match':correct,'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'seconds':round(time.time()-started,2),'scope':'Pinned current integration branch; fixed 19-case corpus and listed native battery. Not main, generic XML conformance, arbitrary PR correctness or FGM classification.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 for name in ['source.json','report-reader.patch','cases.json']:
  shutil.copy2(bundle/name,out/name)
 if not (battery_ok and correct):sys.exit(1)
except Exception as e:
 (out/'error.json').write_text(json.dumps({'error':str(e),'checks':checks,'observations':observations},indent=2));raise
