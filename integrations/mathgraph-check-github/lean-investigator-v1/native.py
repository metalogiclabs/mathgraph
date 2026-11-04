"""Generic closed Lean guard execution in offline, no-secret containers."""
from pathlib import Path
import subprocess,os,sys,json,hashlib,tarfile,urllib.request,re

def guard_outcome(code,output):
 false=bool(re.search(r'(?m)^.+\.lean:4:0: error: Expression\n  mathgraphCandidateProbe\ndid not evaluate to `true`\s*$',output))
 other=code not in [0,1] or (code==1 and (not false or len(re.findall(r'\berror:',output))!=1))
 return {'exit_code':code,'guard_false':false,'other_errors':other,'output':output[-5000:]}
def digest(data):return hashlib.sha256(data).hexdigest()
def run(args,timeout=240):
 try:return subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 except subprocess.TimeoutExpired:return subprocess.CompletedProcess(args,124,'','TIMEOUT')
def must(args,timeout=240):
 p=run(args,timeout)
 if p.returncode:raise RuntimeError('TRUSTED_SETUP_FAILED: '+(p.stdout+p.stderr)[-1500:])
 return p.stdout.strip()
def validate_snapshot(s):
 assert s['repository']=='metalogiclabs/L4YAML'
 assert s.get('method') in [None,'traceof-comments-v1']
 expected={'path':'Scripts/Ledger.lean','module':'Scripts.Ledger','namespace':'Scripts.Ledger','cli_path':'Scripts/Main/CheckScriptsLedger.lean','cli_module':'Scripts.Main.CheckScriptsLedger','toolchain':'leanprover/lean4:v4.35.0'}
 if s.get('method')=='traceof-comments-v1':
  expected={'path':'Scripts/TraceOf/Gen.lean','module':'Scripts.TraceOf.Gen','namespace':'Scripts.TraceOf.Gen','cli_path':'MathGraphGate.lean','cli_module':'MathGraphGate','toolchain':'leanprover/lean4:v4.35.0','gate_kind':'SELECTED_MODULE_BUILD'}
  assert s['cli_source']=='import Scripts.TraceOf.Gen\n\ndef main (_ : List String) : IO UInt32 := pure 0\n'
 assert all(s[k]==v for k,v in expected.items())
 assert re.fullmatch(r'[a-f0-9]{40}',s['head_sha'])
 if s.get('mode')=='OWNED_FORK_PR_PILOT':
  assert re.fullmatch(r'[a-f0-9]{40}',s['base_sha']) and s['command'] in ['check','fix']
  assert (isinstance(s['base_source'],str) or s.get('method')=='traceof-comments-v1' and s['base_source'] is None) and s['base_cli_source']==s['cli_source']
 return True

def runtime_context(env):
 context={'verifier_sha':env.get('MATHGRAPH_CONTROLLER_SHA',env['GITHUB_SHA']),'run_id':int(env['GITHUB_RUN_ID']),'attempt':int(env['GITHUB_RUN_ATTEMPT'])}
 if env.get('MATHGRAPH_CONTROLLER_SHA'):context['scheduler_sha']=env['GITHUB_SHA']
 assert re.fullmatch(r'[a-f0-9]{40}',context['verifier_sha']) and context['attempt']==1
 return context

def main():
 phase=sys.argv[1];root=Path(sys.argv[2] if len(sys.argv)>2 else 'lean-investigation').resolve()
 load=lambda name:json.loads((root/(name+'.json')).read_text())
 state=load('state')
 if state['state']!='PROBES_PROPOSED':return
 m=load('manifest');context=runtime_context(os.environ)
 assert context==m['context']
 for name,h in m['hashes'].items():assert '/' not in name and digest((root/name).read_bytes())==h
 if phase=='repair' and load('repair-state')['state']!='PATCH_PROPOSED':return
 snapshot=load('snapshot');plan=load('plan');validate_snapshot(snapshot)
 if snapshot.get('mode')=='OWNED_FORK_PR_PILOT':must(['node',str(Path(__file__).resolve().parent.parent/'pr-pilot-v1/admit-source.mjs'),str(root)])
 work=Path('lean-native-'+phase).resolve();work.mkdir(exist_ok=True)
 logs=root/'native-logs';logs.mkdir(exist_ok=True)
 def acquire(revision,label,source):
  url='https://codeload.github.com/'+snapshot['repository']+'/tar.gz/'+revision
  with urllib.request.urlopen(url,timeout=45) as response:data=response.read(100_000_001)
  assert len(data)<100_000_001
  archive=work/(label+'.tar.gz');archive.write_bytes(data);folder=work/label;folder.mkdir(exist_ok=True)
  with tarfile.open(archive) as t:t.extractall(folder,filter='data')
  folders=[p for p in folder.iterdir() if p.is_dir()];assert len(folders)==1;folder=folders[0]
  assert (folder/snapshot['path']).read_text()==source
  if snapshot.get('method')!='traceof-comments-v1':assert (folder/snapshot['cli_path']).read_text()==snapshot['cli_source']
  return folder
 repo=acquire(snapshot['head_sha'],'subject',snapshot['source'])
 base_repo=acquire(snapshot['base_sha'],'base-subject',snapshot['base_source']) if snapshot.get('base_source') is not None else None
 lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0';assert (lean/'bin/lean').exists()
 must(['docker','pull','ubuntu:24.04'],180);base=must(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}'])
 build=work/'image';build.mkdir(exist_ok=True)
 (build/'Dockerfile').write_text('FROM '+base+'\nRUN apt-get update && apt-get install -y --no-install-recommends build-essential libgmp10 && rm -rf /var/lib/apt/lists/*\n')
 image='mathgraph-lean-investigator:'+phase;p=run(['docker','build','-t',image,str(build)],420);(logs/(phase+'-image.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,'NATIVE_IMAGE_SETUP_FAILED'
 runtime={'base_image':base,'image_id':must(['docker','image','inspect',image,'--format','{{.Id}}']),'lean':must([str(lean/'bin/lean'),'--version'])}
 audit=work/'audit';audit.mkdir(exist_ok=True)
 for t in plan['tests']:
  assert re.fullmatch(r'[a-z][a-z0-9_]{0,39}',t['id']) and not t['id'].startswith('control_')
  code='import '+snapshot['module']+'\nopen '+snapshot['namespace']+'\ndef mathgraphCandidateProbe : Bool := ('+t['expression']+')\n#guard mathgraphCandidateProbe\n'
  (audit/(t['id']+'.lean')).write_text(code)
 for name,value in [('control_pass','true'),('control_fail','false')]:
  (audit/(name+'.lean')).write_text('import '+snapshot['module']+'\nopen '+snapshot['namespace']+'\ndef mathgraphCandidateProbe : Bool := '+value+'\n#guard mathgraphCandidateProbe\n')
 def project(label,source):
  p=work/label;(p/Path(snapshot['path']).parent).mkdir(parents=True,exist_ok=True);(p/Path(snapshot['cli_path']).parent).mkdir(parents=True,exist_ok=True)
  (p/snapshot['path']).write_text(source);(p/snapshot['cli_path']).write_text(snapshot['cli_source'])
  (p/'lean-toolchain').write_text(snapshot['toolchain']+'\n')
  (p/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage LeanProbe\nlean_lib Scripts where\n  roots := #[`'+snapshot['module']+']\nlean_exe gate where\n  root := `'+snapshot['cli_module']+'\n  supportInterpreter := true\n')
  for q in [p,*p.rglob('*')]:q.chmod(0o777 if q.is_dir() else 0o666)
  return p
 def execute(p,label,command,timeout=240):
  name='mg-lean-'+phase+'-'+label.replace('_','-')
  args=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','2g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-e','HOME=/tmp','-e','LEAN_PATH=/work/.lake/build/lib/lean','-v',str(lean)+':/opt/lean:ro','-v',str(p)+':/work:'+('rw' if command[:2]==['lake','build'] else 'ro'),'-v',str(audit)+':/audit:ro','-v',str(subjects[p.name])+':/subject:ro','-w','/work',image]+command
  r=run(args,timeout);run(['docker','rm','-f',name],20);(logs/(phase+'-'+label+'.log')).write_text(r.stdout+r.stderr)
  assert (p/snapshot['path']).read_text()==sources[p.name],'SOURCE_CHANGED_DURING_EXECUTION'
  assert (p/snapshot['cli_path']).read_text()==snapshot['cli_source'],'CLI_CHANGED_DURING_EXECUTION'
  return r
 sources={};subjects={}
 def arm(label,source,subject=repo):
  p=project(label,source);sources[label]=source;subjects[label]=subject
  b=execute(p,label+'-build',['lake','build','gate']);result={'build_exit':b.returncode,'source_sha256':digest(source.encode()),'probes':[]}
  if snapshot.get('method')=='traceof-comments-v1':result['gate_kind']='SELECTED_MODULE_BUILD'
  if b.returncode:result['repository_gate_exit']=None;return result
  good=execute(p,label+'-control-pass',['lean','/audit/control_pass.lean'])
  bad=execute(p,label+'-control-fail',['lean','/audit/control_fail.lean'])
  assert good.returncode==0 and guard_outcome(bad.returncode,bad.stdout+bad.stderr)['guard_false'],'NATIVE_CONTROLS_FAILED'
  result['controls']={'pass':guard_outcome(good.returncode,good.stdout+good.stderr),'fail':guard_outcome(bad.returncode,bad.stdout+bad.stderr)}
  assert result['controls']['fail']['exit_code']==1 and not result['controls']['fail']['other_errors']
  for t in plan['tests']:
   r=execute(p,label+'-'+t['id'],['lean','/audit/'+t['id']+'.lean']);row={'id':t['id'],**guard_outcome(r.returncode,r.stdout+r.stderr),'test_file_sha256':digest((audit/(t['id']+'.lean')).read_bytes())};result['probes'].append(row)
  gate=execute(p,label+'-repository-gate',['.lake/build/bin/gate','-C','/subject']);result['repository_gate_exit']=gate.returncode
  return result
 common={'context':context,'source_sha':snapshot['head_sha'],'test_digest':state['test_digest'],'runtime':runtime}
 if phase=='initial':
  report={**common,'arm':arm('original',snapshot['source'])};name='native'
  if base_repo is not None:report.update({'base_sha':snapshot['base_sha'],'base_arm':arm('base',snapshot['base_source'],base_repo)})
 elif phase=='repair':
  patch=load('patch');assert digest(patch['content'].encode())==patch['patched_sha256']
  report={**common,'patched_sha256':patch['patched_sha256'],'original':arm('paired-original',snapshot['source']),'repaired':arm('repaired',patch['content']),'withdrawn':arm('withdrawn',snapshot['source'])};name='native-repair'
 else:raise ValueError('UNKNOWN_PHASE')
 (root/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
 files=sorted(p for p in root.glob('*.json') if p.name!='manifest.json');(root/'manifest.json').write_text(json.dumps({'context':context,'hashes':{p.name:digest(p.read_bytes()) for p in files}})+'\n')
 print(json.dumps({'phase':phase,'tests':len(plan['tests']),'runtime':runtime}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  root=Path(sys.argv[2] if len(sys.argv)>2 else 'lean-investigation').resolve();root.mkdir(exist_ok=True)
  context=runtime_context(os.environ)
  reason=type(e).__name__+': '+str(e)[-1200:];(root/'state.json').write_text(json.dumps({'context':context,'state':'UNKNOWN','stage':'native-'+sys.argv[1],'reason':reason})+'\n')
  (root/'native-error.json').write_text(json.dumps({'context':context,'reason':reason})+'\n')
  files=sorted(p for p in root.glob('*.json') if p.name!='manifest.json');(root/'manifest.json').write_text(json.dumps({'context':context,'hashes':{p.name:digest(p.read_bytes()) for p in files}})+'\n')
  print(json.dumps({'status':'UNKNOWN','reason':reason}))
