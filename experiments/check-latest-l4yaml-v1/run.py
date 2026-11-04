import hashlib, json, os, pathlib, subprocess, urllib.request, xml.etree.ElementTree as ET

out=pathlib.Path('latest-evidence'); out.mkdir(exist_ok=True)
sources={
 'score':('97b28d41b57fb2cd9d38df3f3bd94138fb0c828b','Scripts/Matrix/Score.lean'),
 'reports':('1f5af2c7cb3c56acef7c581d1bb15986cdbebaa2','Tests/SuiteRunner/Reports.lean'),
 'hygiene':('2bc9ef4f77204a2567c252d7072d691ed37ced46','Scripts/Stats/Hygiene.lean')}
manifest={}
def native(name,source,probes):
 p=out/(name+'.lean');p.write_text(source+'\n'+ '\n'.join(probes)+'\n')
 r=subprocess.run([os.path.expanduser('~/.elan/bin/lean'),str(p)],text=True,capture_output=True,timeout=120)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 assert r.returncode==0,(name,r.stdout,r.stderr)
 return [x[len('OBS '):] for x in r.stdout.splitlines() if x.startswith('OBS ')]

texts={}
for key,(rev,path) in sources.items():
 b=urllib.request.urlopen('https://raw.githubusercontent.com/nasa-jpl/L4YAML/'+rev+'/'+path).read()
 texts[key]=b.decode();(out/(key+'-original.lean')).write_bytes(b)
 manifest[key]={'revision':rev,'path':path,'sha256':hashlib.sha256(b).hexdigest()}

# No function is rewritten. Reports imports a large HTML module it never uses;
# remove only that unused import for this selected pure-module replay.
report_source=texts['reports'].replace('public import Tests.SuiteRunner.HtmlReport\n','')
xml_cases=[
 '<testsuite><testcase name="ok"/></testsuite>',
 '<testsuites><testsuite><testcase name="first"/></testsuite>',
 '<testsuite><testcase name="a"></testsuite>',
 '<testsuite/><testsuite/>',
 'garbage<testsuite><testcase name="ok"/></testsuite>',
 '<testsuite><testcase name="ok"/></testsuite>garbage',
 '<testsuite><testcase name="a" name="b"/></testsuite>',
 '<testsuite><testcase name="&unknown;"/></testsuite>',
 '<testsuite><testcase name="a"/> &broken; </testsuite>',
 '<testsuite><testcase name="a"/></testsuite garbage>',
 '<testsuite><testcase name="a" time=1/></testsuite>',
 '<testsuite><!-- open',
 '<testsuite><testcase name="&#65;"/></testsuite>',
 '<testsuite><testcase name="a"><error message="oops"/></testcase></testsuite>',
]
probes=['#eval IO.println ("OBS " ++ toString (Tests.SuiteRunner.Reports.junitCases '+json.dumps(x)+').toOption.isSome)' for x in xml_cases]
observed=native('reports',report_source,probes)
assert len(observed)==len(xml_cases),observed
results=[]
for xml,obs in zip(xml_cases,observed):
 try: ET.fromstring(xml);expected=True
 except ET.ParseError:expected=False
 results.append({'input':xml,'xml_etree_accepts':expected,'lean_report_accepts':obs=='true','agreement':expected==(obs=='true')})

# Cross-language behavior obligation: distinct Python JSON integers remain distinct.
pairs=[('9007199254740992','9007199254740993'),('9007199254740993','9007199254740994'),('1','1.0'),('true','1'),('0.1','0.10000000000000001'),('100000000000000000000','100000000000000000001')]
probes=['#eval IO.println ("OBS " ++ toString (Scripts.Matrix.Score.streamsEqText '+json.dumps(a)+' '+json.dumps(b)+'))' for a,b in pairs]
numbers=native('score',texts['score'],probes)
for (a,b),got in zip(pairs,numbers):
 results.append({'left':a,'right':b,'python_equal':json.loads(a)==json.loads(b),'lean_observation':got})

# Existing fail-closed hygiene controls must remain intact.
native('hygiene',texts['hygiene'],[])
record={'boundary':'Pinned pure functions and original guards; Reports only removes an unused HtmlReport import. Not full repository replay.','manifest':manifest,'observations':results,'xml_disagreements':sum(not r['agreement'] for r in results if 'agreement' in r),'hygiene_original_guards':'PASS','devin_credit':'Truncation, mismatched roots, unquoted attributes and deadline issues already reported/fixed by Devin; do not count these as new findings. PR219 also has nonpublic flags; absence from public comments is not evidence Devin never flagged a case.'}
(out/'result.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
