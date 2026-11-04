from pathlib import Path
import json,subprocess,hashlib,os,xml.etree.ElementTree as ET
p=Path(__file__).parent;out=Path('report-integrity-evidence');out.mkdir(exist_ok=True)
cases=[
 ('prefix','new_refusals','garbage<testsuite><testcase name="ok"/></testsuite>',False),
 ('suffix','new_refusals','<testsuite><testcase name="ok"/></testsuite>garbage',False),
 ('duplicate','new_refusals','<testsuite><testcase name="a" name="b"/></testsuite>',False),
 ('attribute_entity','new_refusals','<testsuite><testcase name="&unknown;"/></testsuite>',False),
 ('content_entity','new_refusals','<testsuite><testcase name="a"/> &broken; </testsuite>',False),
 ('closing_content','new_refusals','<testsuite><testcase name="a"/></testsuite garbage>',False),
 ('empty','valid_controls','<testsuite/>',True),
 ('one','valid_controls','<testsuite><testcase name="ok"/></testsuite>',True),
 ('failure','valid_controls','<testsuite><testcase name="bad"><failure/></testcase></testsuite>',True),
 ('skip','valid_controls','<testsuite><testcase name="skip"><skipped/></testcase></testsuite>',True),
 ('comment_cdata','valid_controls','<testsuite><!-- &unknown; --><![CDATA[<ignored> &unknown;]]><testcase name="ok"/></testsuite>',True),
 ('entities','valid_controls','<?xml version="1.0"?><testsuite><testcase name="&#65;&#x42;&amp;"/></testsuite>',True),
 ('truncated','legacy_refusals','<testsuites><testsuite><testcase name="first"/></testsuite>',False),
 ('mismatch','legacy_refusals','<testsuite><testcase name="a"></testsuite>',False),
 ('two_roots','legacy_refusals','<testsuite/><testsuite/>',False),
 ('unquoted','legacy_refusals','<testsuite><testcase name="a" time=1/></testsuite>',False),
 ('open_comment','legacy_refusals','<testsuite><!-- open',False),
 ('open_tag','legacy_refusals','<testsuite><testcase name="a"',False),
 ('no_root','legacy_refusals','<?xml version="1.0"?>',False)]
records=[]
for id,group,text,expected in cases:
 try:ET.fromstring(text);accept=True
 except ET.ParseError:accept=False
 assert accept==expected
 records.append({'id':id,'group':group,'input':text,'accepted':expected})
(out/'fixtures.json').write_text(json.dumps(records,indent=2))
results={}
for arm,file in [('original','original.lean'),('candidate','candidate.lean'),('withdrawn','original.lean')]:
 source=(p/file).read_text();native=source.replace('public import Tests.SuiteRunner.HtmlReport\n','')
 for c in records:native+='\n#eval IO.println ("OBS " ++ toString (Tests.SuiteRunner.Reports.junitCases '+json.dumps(c['input'])+').toOption.isSome)\n'
 path=out/(arm+'.lean');path.write_text(native)
 r=subprocess.run([os.path.expanduser('~/.elan/bin/lean'),str(path)],text=True,capture_output=True,timeout=120)
 (out/(arm+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(arm,r.stdout,r.stderr)
 readings=[x[4:]=='true' for x in r.stdout.splitlines() if x.startswith('OBS ')]
 assert len(readings)==len(records)
 results[arm]={'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'rows':[{'id':c['id'],'passed':v==c['accepted'],'observed_acceptance':v} for c,v in zip(records,readings)]}
assert sum(not r['passed'] for r in results['original']['rows'])==6
assert all(r['passed'] for r in results['candidate']['rows'])
assert results['original']==results['withdrawn']
(out/'result.json').write_text(json.dumps({'status':'WARRANTED_BOUNDED','input_count':len(records),'reference':'Python xml.etree.ElementTree independent acceptance','scope':'Pure Reports module with unused HtmlReport import removed; original guards retained. Not full XML standards conformance or full repository replay.','arms':results},indent=2))
print('Original: 6/19 failures; candidate: 19/19 pass; withdrawn: same 6 failures.')
