from pathlib import Path
import subprocess,tempfile,json,urllib.request,hashlib
root=Path('subject').resolve();out=Path('email-repro').resolve();out.mkdir()
def run(args,timeout=1800):
 p=subprocess.run(args,cwd=root,text=True,capture_output=True,timeout=timeout)
 return p
revision=run(['git','rev-parse','HEAD']).stdout.strip()
assert not run(['git','status','--porcelain']).stdout.strip()
snippet="""DIR=$(mktemp -d)
printf '%s' '<testsuite><testcase name="a" name="b"/></testsuite>' > "$DIR/python-ffi-junit.xml"
lake exe suiterunner --reports "$DIR"
lean_code=$?
printf '\\nLEAN_EXIT=%s\\n' "$lean_code"
test -f "$DIR/python-ffi-tests.html"
printf 'LEAN_HTML=%s\\n' "$?"
cp "$DIR/python-ffi-tests.html" "$EVIDENCE_DIR/lean-report.html"
rm -f "$DIR/python-ffi-tests.html"
git show 5b8e558d:scripts/generate-test-reports.py > /tmp/gen.py
git_code=$?
python3 /tmp/gen.py "$DIR"
python_code=$?
printf 'GIT_SHOW_EXIT=%s\\nPYTHON_EXIT=%s\\n' "$git_code" "$python_code"
test -f "$DIR/python-ffi-tests.html"
printf 'PYTHON_HTML=%s\\n' "$?"
"""
import os
env=dict(os.environ,EVIDENCE_DIR=str(out))
p=subprocess.run(['bash','-c',snippet],cwd=root,text=True,capture_output=True,timeout=1800,env=env)
(out/'repro.log').write_text(p.stdout+p.stderr)
print(p.stdout[-2000:],p.stderr[-1000:],flush=True)
assert 'LEAN_EXIT=0' in p.stdout and 'LEAN_HTML=0' in p.stdout and 'GIT_SHOW_EXIT=0' in p.stdout and 'PYTHON_EXIT=1' in p.stdout and 'PYTHON_HTML=1' in p.stdout
assert 'ParseError' in p.stderr
assert 'Passed: 1' in (out/'lean-report.html').read_text()
links=[]
for url in ['https://github.com/nasa-jpl/L4YAML/blob/5b8e558d/scripts/generate-test-reports.py','https://mathgraph-check-webhook-pilot.metalogiclabs-check.workers.dev/pilot']:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MathGraph-public-repro-check'}),timeout=60) as r:
  body=r.read();links.append({'url':url,'status':r.status,'final_url':r.url,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
 assert links[-1]['status']==200 and '/login' not in links[-1]['final_url']
result={'revision':revision,'status':'PASS','clean_checkout':True,'one_file':True,'absolute_dir':True,'lean_exit':0,'lean_html':True,'python_exit':1,'python_html':False,'git_show_exit':0,'anonymous_links':links}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
