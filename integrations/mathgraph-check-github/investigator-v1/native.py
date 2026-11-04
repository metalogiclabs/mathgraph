"""No-secret native adapter. Repository/model code runs only in Docker, offline."""
from pathlib import Path
import subprocess, json, hashlib, os, sys, tarfile, urllib.request, shutil, ast, re, tomllib, xml.etree.ElementTree as ET

def junit_result(text):
    if not text:return dict(tests=0,failures=0,errors=0,skipped=0)
    root=ET.fromstring(text);rows=list(root.iter('testsuite'))
    if not rows:raise ValueError('NO_JUNIT_SUITES')
    keys=['tests','failures','errors','skipped']
    if any(any(k not in row.attrib for k in keys) for row in rows):raise ValueError('MISSING_JUNIT_COUNTERS')
    return {k:sum(int(row.attrib[k]) for row in rows) for k in keys}

def sandbox_command(image,name,repo,audit,results,command,data=None,subject_files=()):
    return ['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','2g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','HOME=/tmp','-e','PYTHONPATH=/runner:/repo','-e','PYTHONDONTWRITEBYTECODE=1','-e','MPLCONFIGDIR=/tmp/matplotlib','-e','MG_SUBJECT_FILES='+json.dumps(list(subject_files)),'-v',repo+':/repo:ro','-v',audit+':/audit:ro','-v',results+':/results','-v',str(Path(__file__).parent.resolve())+':/runner:ro','-w','/repo']+(['-v',data+':/repo/data:rw'] if data else [])+[image]+command

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(x):return json.dumps(x,separators=(',',':'),ensure_ascii=False)
def execute(args,timeout=240):return subprocess.run(args,capture_output=True,text=True,timeout=timeout)
def must(args,timeout=240):
    r=execute(args,timeout)
    if r.returncode:raise RuntimeError(str(args[:3])+': '+(r.stdout+r.stderr)[-4000:])
    return r.stdout.strip()

def main():
    phase=sys.argv[1];root=Path(sys.argv[2] if len(sys.argv)>2 else 'investigation').resolve()
    load=lambda n:json.loads((root/(n+'.json')).read_text())
    state=load('state')
    if state['state']!='PROBES_PROPOSED':return
    manifest=load('manifest');context=manifest['context']
    assert context=={'verifier_sha':os.environ['GITHUB_SHA'],'run_id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT'])}
    for name,h in manifest['hashes'].items():
        assert '/' not in name and sha((root/name).read_bytes())==h,'ARTIFACT_BYTES_CHANGED'
    if phase=='repair' and load('repair-state')['state']!='PATCH_PROPOSED':return
    snapshot=load('snapshot');plan=load('plan');test_digest=state['test_digest']
    assert snapshot['repository']=='metalogiclabs/gnss_lib_py' and snapshot['source_repository'] in ['Stanford-NavLab/gnss_lib_py','metalogiclabs/gnss_lib_py']
    workspace=Path('investigator-native-'+phase).resolve();workspace.mkdir(exist_ok=True)
    logs=root/'native-logs';logs.mkdir(exist_ok=True)
    def checkout(label,rev):
        assert len(rev)==40 and all(c in '0123456789abcdef' for c in rev)
        archive=workspace/(label+'.tar.gz');url='https://codeload.github.com/'+snapshot['source_repository']+'/tar.gz/'+rev
        with urllib.request.urlopen(url,timeout=45) as response:
            data=response.read(100_000_001)
        assert len(data)<=100_000_000
        archive.write_bytes(data);destination=workspace/label;destination.mkdir(exist_ok=True)
        with tarfile.open(archive) as t:t.extractall(destination,filter='data')
        children=[p for p in destination.iterdir() if p.is_dir()];assert len(children)==1
        initialize_metadata(children[0])
        return children[0]
    head=checkout('head',snapshot['head_sha'])
    for f in snapshot['files']:assert (head/f['path']).read_text()==f['head'],'HEAD_SOURCE_BYTES_CHANGED'
    audit=workspace/'audit';audit.mkdir(exist_ok=True)
    for t in plan['tests']:
        assert t['id'].replace('_','').isalnum() and t['id'][0].isalpha()
        validate_probe(t['code'])
        (audit/('test_'+t['id']+'.py')).write_text(t['code'])
    (audit/'mg_control_pass.py').write_text('def test_control():\n    assert 2 + 2 == 4\n')
    (audit/'mg_control_fail.py').write_text('def test_control():\n    assert False, "MG_EXPECTED_CONTROL_FAILURE"\n')
    # Dependency setup also occurs inside Docker, without credentials or host mounts.
    # Both revisions use this same trusted dependency-only environment.
    build=workspace/'build';build.mkdir(exist_ok=True)
    must(['docker','pull','python:3.12-slim-bookworm'],180)
    base_digest=must(['docker','image','inspect','python:3.12-slim-bookworm','--format','{{index .RepoDigests 0}}'])
    dependencies=['pytest==8.3.5','pytest-env==1.1.5','pytest-cov==6.1.1','numpy>=2.1,<3','pandas>=2,<3','georinex<=1.16.1','unlzw3>=0.2.3,<0.3','pynmea2>=1.19,<2','scipy>=1.14,<2','matplotlib>=3.10,<4','plotly>=5.24,<6','kaleido==0.2.1','requests>=2.32,<3','xarray<=2024.7.0']
    (build/'Dockerfile').write_text('FROM '+base_digest+'\nRUN python -m pip wheel --wheel-dir /wheels '+' '.join("'"+d+"'" for d in dependencies)+'\nRUN python -m pip install --no-index --find-links /wheels '+' '.join("'"+d+"'" for d in dependencies)+'\nWORKDIR /repo\n')
    image='mathgraph-investigator:'+phase
    p=execute(['docker','build','-t',image,str(build)],600);(logs/(phase+'-build.log')).write_text(p.stdout+p.stderr)
    assert p.returncode==0,(p.stdout+p.stderr)[-4000:]
    image_id=must(['docker','image','inspect',image,'--format','{{.Id}}'])
    installed=must(['docker','run','--rm','--network','none','--read-only',image,'python','-m','pip','freeze'])
    (logs/(phase+'-pip-freeze.txt')).write_text(installed+'\n')
    results=workspace/'junit';results.mkdir(exist_ok=True);results.chmod(0o777)
    def protected_digest(repo):
        files=sorted((repo/'tests').rglob('*.py'));assert files,'NO_PROTECTED_TESTS'
        return sha(''.join(str(p.relative_to(repo))+'\0'+sha(p.read_bytes())+'\n' for p in files).encode())
    def pytest(repo,label,path,subject,test_hash,timeout=180):
        name='mg-'+phase+'-'+label.replace('_','-');xml=results/(label+'.xml')
        data=None
        if (repo/'data').is_dir():
            data_path=workspace/('data-'+label);shutil.copytree(repo/'data',data_path,dirs_exist_ok=True)
            for f in [data_path,*data_path.rglob('*')]:f.chmod(0o777 if f.is_dir() else 0o666)
            data=str(data_path)
        command=['env','MG_CASES_FILE=/results/'+label+'-cases.json','python','-m','pytest','-q','-p','mg_native_plugin','-p','no:cacheprovider',path,'--junitxml=/results/'+xml.name]
        timed_out=False
        try:p=execute(sandbox_command(image,name,str(repo),str(audit),str(results),command,data=data,subject_files=['/repo/'+f['path'] for f in snapshot['files']]),timeout)
        except subprocess.TimeoutExpired as e:
            timed_out=True;p=subprocess.CompletedProcess([],124,(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else (e.stdout or ''),(e.stderr or b'').decode() if isinstance(e.stderr,bytes) else (e.stderr or ''))
        finally:execute(['docker','rm','-f',name],20)
        output=p.stdout+p.stderr;(logs/(phase+'-'+label+'.log')).write_text(output)
        try:counts=junit_result(xml.read_text() if xml.exists() else '')
        except (ValueError,ET.ParseError):counts=dict(tests=0,failures=0,errors=1,skipped=0)
        cases_path=results/(label+'-cases.json')
        try:cases=json.loads(cases_path.read_text()) if cases_path.exists() else []
        except ValueError:cases=[]
        file_hash=sha((audit/Path(path).name).read_bytes()) if path.startswith('/audit/') else None
        return {'cases':cases,'test_file_sha256':file_hash,'subject_sha':subject,'test_digest':test_hash,'exit_code':p.returncode,'timeout':timed_out,**counts,'output':output[-3500:]}
    # Test harness controls run against the same imported package environment.
    passed=pytest(head,'control-pass','/audit/mg_control_pass.py',snapshot['head_sha'],test_digest)
    failed=pytest(head,'control-fail','/audit/mg_control_fail.py',snapshot['head_sha'],test_digest)
    assert passed['exit_code']==0 and passed['tests']==1 and failed['exit_code']==1 and failed['failures']==1,'NATIVE_CONTROLS_FAILED'
    def run_arm(repo,label,subject):
        probes=[]
        for t in plan['tests']:
            row=pytest(repo,label+'-'+t['id'],'/audit/test_'+t['id']+'.py',subject,test_digest,90);row['id']=t['id'];probes.append(row)
        protected=pytest(repo,label+'-protected','/repo/tests',subject,protected_digest(repo),240)
        return {'probes':probes,'protected':protected}
    common={'verifier_sha':context['verifier_sha'],'head_sha':snapshot['head_sha'],'test_digest':test_digest,'runtime':{'base_image':base_digest,'image_id':image_id,'python':'3.12','dependencies':'Trusted dependency-only wheel profile; target package never installed. Paired original/repaired replay uses one image; pip freeze retained'},'controls':{'pass':passed,'fail':failed}}
    if phase=='initial':
        base=checkout('base',snapshot['base_sha'])
        for f in snapshot['files']:assert (base/f['path']).read_text()==f['base'],'BASE_SOURCE_BYTES_CHANGED'
        report={**common,'arms':{'base':run_arm(base,'base',snapshot['base_sha']),'head':run_arm(head,'head',snapshot['head_sha'])}}
        (root/'native.json').write_text(json.dumps(report,indent=2)+'\n')
    elif phase=='repair':
        patch=load('patch');before=protected_digest(head)
        original_arm=run_arm(head,'repair-original',snapshot['head_sha'])
        for f in patch['files']:
            assert f['path'] in [x['path'] for x in snapshot['files']] and f['path'].endswith('.py') and '..' not in Path(f['path']).parts
            (head/f['path']).write_text(f['content'])
        assert protected_digest(head)==before,'PROTECTED_TESTS_CHANGED'
        report={**common,'patch_digest':load('repair-state')['patch_digest'],'original_arm':original_arm,'arm':run_arm(head,'repaired',snapshot['head_sha'])}
        (root/'native-repair.json').write_text(json.dumps(report,indent=2)+'\n')
    else:raise ValueError('UNKNOWN_NATIVE_PHASE')
    # Refresh the manifest only after trusted host collection. Native test reports
    # are interpreter/test-run observations, not proof of arbitrary program intent.
    files=sorted(p for p in root.glob('*.json') if p.name!='manifest.json')
    (root/'manifest.json').write_text(json.dumps({'context':context,'hashes':{p.name:sha(p.read_bytes()) for p in files}},indent=2)+'\n')
    print(json.dumps({'phase':phase,'probe_count':len(plan['tests']),'image_id':image_id}))
def validate_probe(text):
    tree=ast.parse(text)
    if not any(isinstance(x,ast.Assert) for x in ast.walk(tree)):raise ValueError('NO_ASSERTION_PROBE')
    bad={'os','sys','subprocess','socket','pathlib','ctypes','inspect','importlib','shutil','pickle','marshal','builtins'}
    imported=set()
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else [(node.module or '').split('.')[0]]
            if any(x in bad for x in names):raise ValueError('UNSUPPORTED_PROBE_IMPORT')
            for alias in node.names:
                imported.add(alias.asname or (alias.name.split('.')[0] if isinstance(node,ast.Import) else alias.name))
        if isinstance(node,ast.Call):
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
            if name in {'exec','eval','compile','__import__','open','exit','quit','skip','xfail','getattr','setattr','delattr','getenv','system','popen'}:raise ValueError('UNSUPPORTED_PROBE_CALL')
    # A model must not make a failing source contract pass by rewriting the
    # imported specimen before the assertion. Follow simple local aliases;
    # this syntactic screen is deliberately not claimed as general purity.
    aliases=set(imported)
    assignments=[n for n in ast.walk(tree) if isinstance(n,ast.Assign)]
    while True:
        old=len(aliases)
        for n in assignments:
            if isinstance(n.value,ast.Name) and n.value.id in aliases:
                aliases.update(t.id for target in n.targets for t in ast.walk(target) if isinstance(t,ast.Name))
        if len(aliases)==old:break
    def root_name(expr):
        while isinstance(expr,(ast.Subscript,ast.Attribute)):expr=expr.value
        return expr.id if isinstance(expr,ast.Name) else None
    mutators={'append','extend','insert','remove','pop','popitem','clear','update','setdefault','sort','reverse','add','discard','difference_update','intersection_update','symmetric_difference_update','__setitem__','__delitem__'}
    for node in ast.walk(tree):
        if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Delete)):
            targets=node.targets if isinstance(node,(ast.Assign,ast.Delete)) else [node.target]
            if any(isinstance(t,(ast.Subscript,ast.Attribute)) and root_name(t) in aliases for t in targets):
                raise ValueError('IMPORTED_SPECIMEN_MUTATION_REFUSED')
            if isinstance(node,ast.AugAssign) and root_name(node.target) in aliases:
                raise ValueError('IMPORTED_SPECIMEN_MUTATION_REFUSED')
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
            if node.func.attr in mutators and root_name(node.func.value) in aliases:
                raise ValueError('IMPORTED_SPECIMEN_MUTATION_REFUSED')
    return True

def initialize_metadata(repo):
    # Static distribution metadata enables importlib.metadata.version without
    # installing the target package or executing its build backend.
    config=tomllib.loads((repo/'pyproject.toml').read_text())
    project=config.get('project') or config.get('tool',{}).get('poetry',{})
    name=project.get('name');version=project.get('version')
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or not isinstance(version,str) or not re.fullmatch(r'[A-Za-z0-9_.+!-]+',version):raise ValueError('STATIC_PACKAGE_METADATA_REQUIRED')
    normalized=re.sub(r'[-_.]+','_',name)
    metadata=repo/(normalized+'-'+version+'.dist-info');metadata.mkdir(exist_ok=True)
    (metadata/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n')
    return metadata

if __name__=='__main__':
    try:main()
    except Exception as exc:
        root=Path(sys.argv[2] if len(sys.argv)>2 else 'investigation').resolve();root.mkdir(exist_ok=True)
        context={'verifier_sha':os.environ['GITHUB_SHA'],'run_id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT'])}
        reason=type(exc).__name__+': '+str(exc)[:1000]
        (root/'state.json').write_text(json.dumps({'context':context,'state':'UNKNOWN','stage':'native-'+sys.argv[1],'reason':reason})+'\n')
        (root/'native-error.json').write_text(json.dumps({'context':context,'stage':sys.argv[1],'reason':reason})+'\n')
        files=sorted(p for p in root.glob('*.json') if p.name!='manifest.json')
        (root/'manifest.json').write_text(json.dumps({'context':context,'hashes':{p.name:sha(p.read_bytes()) for p in files}})+'\n')
        print(json.dumps({'status':'UNKNOWN','stage':sys.argv[1],'reason':reason}))
