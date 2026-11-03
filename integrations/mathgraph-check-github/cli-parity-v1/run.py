"""One fixed CLI-contract runner; no model, source-defined commands or native credentials."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,tarfile,urllib.request
from rules import compare_case,effects,safe_path,project_closure,shared,lake_config,workspace_hashes
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def run(cmd,timeout=180):
    try:
        r=subprocess.run(cmd,capture_output=True,timeout=timeout)
        try:return subprocess.CompletedProcess(cmd,r.returncode,r.stdout.decode('utf-8'),r.stderr.decode('utf-8'))
        except UnicodeDecodeError:return subprocess.CompletedProcess(cmd,125,'','NON_UTF8_OUTPUT')
    except subprocess.TimeoutExpired:return subprocess.CompletedProcess(cmd,124,'','TIMEOUT')
def must(cmd,timeout=240):
    r=run(cmd,timeout)
    if r.returncode:raise ValueError('TRUSTED_SETUP_FAILED:'+r.stderr[-1200:])
    return r.stdout.strip()
def acquire(repo,revision,out):
    with urllib.request.urlopen('https://codeload.github.com/'+repo+'/tar.gz/'+revision,timeout=50) as r:data=r.read(50_000_001)
    if len(data)>50_000_000:raise ValueError('ARCHIVE_LIMIT')
    archive=out/(revision+'.tar.gz');archive.write_bytes(data);folder=out/(revision+'-tree');folder.mkdir()
    with tarfile.open(archive) as t:
        ms=t.getmembers()
        if len(ms)>20000 or sum(x.size for x in ms)>150_000_000:raise ValueError('EXTRACTION_LIMIT')
        t.extractall(folder,filter='data')
    if any(p.is_symlink() for p in folder.rglob('*')):raise ValueError('SOURCE_SYMLINK')
    roots=list(folder.iterdir())
    if len(roots)!=1:raise ValueError('SOURCE_ROOT_AMBIGUOUS')
    return roots[0],sha(archive)

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--pr',type=int,required=True);p.add_argument('--base',required=True);p.add_argument('--head',required=True);p.add_argument('--snapshot',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    if not all(re.fullmatch('[a-f0-9]{40}',s) for s in [args.base,args.head]):raise ValueError('INVALID_REVISION')
    out=Path(args.output).resolve();out.mkdir();logs=out/'logs';logs.mkdir();contract=json.loads((HERE/'contract.json').read_text());allcases=json.loads((HERE/'cases.json').read_text())
    profile=next(x for x in contract['profiles'] if x['id']==args.profile);cases=allcases[args.profile];repo=contract['repository']
    pr,diff=shared.hosted_snapshot(json.loads(Path(args.snapshot).read_text()),repo,args.pr,args.base,args.head)
    files=shared.pinned_files(diff,args.base,args.head);paths={x['filename']:x['status'] for x in files}
    if paths.get(profile['base_entry'])!='removed' or paths.get(profile['head_entry']) not in ['added','modified']:raise ValueError('CLI_MIGRATION_SCOPE_MISMATCH')
    report={'schema':'mathgraph.cli-parity.report.v1','repository':repo,'pr':args.pr,'base_sha':args.base,'head_sha':args.head,'profile':args.profile,'controller_sha':os.environ.get('MATHGRAPH_CONTROLLER_SHA') or os.environ['GITHUB_SHA'],'contract_sha256':sha(HERE/'contract.json'),'cases_sha256':sha(HERE/'cases.json'),'state':'UNKNOWN','whole_pr_correctness':'UNKNOWN','metadata_acquisition':'AUTHENTICATED_INTAKE_SNAPSHOT','freshness':'PUBLISHER_RECHECK_REQUIRED','cases':[],'scope':profile['runtime_scope']}
    save(out/'result.json',report)
    base,bhash=acquire(repo,args.base,out);head,hhash=acquire(repo,args.head,out);report['archives']={'base':bhash,'head':hhash}
    oracle=base/profile['base_entry']
    if not oracle.is_file():raise ValueError('PYTHON_ORACLE_ABSENT')
    modules=project_closure(head,[profile['head_module'],*profile['extra_roots']]);selected=out/'selected';selected.mkdir()
    for m in modules:
        rel=Path(m.replace('.','/')+'.lean');dest=selected/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(head/rel,dest)
    identities={str(p.relative_to(selected)):sha(p) for p in selected.rglob('*.lean')};report['source_hashes']=identities;report['oracle_sha256']=sha(oracle)
    lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0'
    must(['docker','pull','ubuntu:24.04']);imagebase=must(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}']);image=out/'image';image.mkdir();(image/'Dockerfile').write_text('FROM '+imagebase+'\nRUN apt-get update && apt-get install -y --no-install-recommends python3 build-essential libgmp10 && rm -rf /var/lib/apt/lists/*\n');must(['docker','build','-t','mathgraph-cli-parity',str(image)],420)
    report['runtime']={'lean':must([str(lean/'bin/lean'),'--version']),'image_id':must(['docker','image','inspect','mathgraph-cli-parity','--format','{{.Id}}']),'base_image':imagebase}
    build=out/'build';build.mkdir();(build/'lean-toolchain').write_text(contract['toolchain']+'\n')
    (build/'lakefile.lean').write_text(lake_config(profile,modules))
    def permissions(folder):
        for q in [folder,*folder.rglob('*')]:
            if q.stat().st_uid==os.getuid():q.chmod(0o777 if q.is_dir() else 0o666)
    def docker(work,label,command,mounts=(),timeout=120):
        permissions(work);name='mg-cli-'+args.profile+'-'+label
        cmd=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','3g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','HOME=/tmp','-e','LANG=C.UTF-8','-e','PYTHONDONTWRITEBYTECODE=1','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-e','LEAN_PATH=/work/.lake/build/lib/lean','-v',str(lean)+':/opt/lean:ro','-v',str(work)+':/work:rw','-w','/work']
        for src,dest in mounts:cmd+=['-v',str(src)+':'+dest+':ro']
        r=run(cmd+['mathgraph-cli-parity']+command,timeout);run(['docker','rm','-f',name],20)
        (logs/(label+'.stdout')).write_text(r.stdout);(logs/(label+'.stderr')).write_text(r.stderr)
        return r
    targets=['cli']+(['L4YAML'] if profile['extra_roots'] else [])
    built=docker(build,'build',['lake','build',*targets],[(selected,'/source'),(build/'lakefile.lean','/work/lakefile.lean')],600);report['build_exit']=built.returncode
    if built.returncode:report['reason']='CLI_BUILD_FAILED';save(out/'result.json',report);return
    lib=build/'.lake/build/lib/lean';exe=build/'.lake/build/bin/cli'
    def observe(case,side,label,control=False):
        work=out/(case['id']+'-'+label);work.mkdir()
        for name,content in case['files'].items():
            q=work/safe_path(name);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(content)
        for item in case['repository_inputs']:
            if item['side'] not in ['base','head']:raise ValueError('INVALID_FIXTURE_SOURCE')
            source=(base if item['side']=='base' else head)/safe_path(item['path']);dest=work/safe_path(item['target']);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        exclude={profile['base_entry']} if side=='base' and not control else set()
        before=workspace_hashes(work,contract['limits'],exclude);(work/'scripts').mkdir(exist_ok=True);(work/'.lake/build/lib/lean').mkdir(parents=True)
        mounts=[(lib,'/work/.lake/build/lib/lean')]
        if control:
            marker=(contract['generator_provenance_lines'][1]+'\n' if case['comparison']['stdout']=='generator-provenance' else '')+'MATHGRAPH_NATIVE_OUTPUT_CONTROL\n'
            cmd=['python3','-c','import sys;sys.stdout.write('+repr(marker)+')']
        elif side=='base':
            path='/work/'+profile['base_entry'];target=work/profile['base_entry'];target.parent.mkdir(parents=True,exist_ok=True);target.touch();mounts.append((oracle,path));cmd=['python3',path,*case['base_args']]
        else:mounts.append((exe,'/program'));cmd=['/program',*case['head_args']]
        r=docker(work,label,cmd,mounts,contract['limits']['case_seconds']);after=workspace_hashes(work,contract['limits'],exclude)
        complete=r.returncode>=0 and r.returncode not in [124,125,126,127,137] and len(r.stdout.encode())+len(r.stderr.encode())<=contract['limits']['output_bytes']
        return {'complete':complete,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'effects':effects(before,after)}
    for i,case in enumerate(cases):
        b=observe(case,'base',f'{i}-base');again=observe(case,'base',f'{i}-repeat');h=observe(case,'head',f'{i}-head');result=compare_case(b,again,h,case,contract)
        report['cases'].append({'id':case['id'],'policy':case['comparison'],'base':b,'reference_repeat':again,'head':h,**result});save(out/'result.json',report)
    first=cases[0];normal=report['cases'][0];negative=observe(first,'head','negative',True);withdrawal=observe(first,'head','withdrawal')
    report['controls']={'reference_replay_qualified':all(c['base']['complete'] and c['base']['exit']==case['expected_base_exit'] and c['base']==c['reference_repeat'] for c,case in zip(report['cases'],cases)),'changed_native_output_detected':compare_case(normal['base'],normal['reference_repeat'],negative,first,contract)['state']=='DIFFERENCE','head_withdrawal_identical':normal['head']==withdrawal,'negative':negative,'withdrawal':withdrawal}
    report['source_preserved']=all(sha(selected/p)==h for p,h in identities.items()) and sha(oracle)==report['oracle_sha256']
    report['counts']={s:sum(c['state']==s for c in report['cases']) for s in ['PARITY','DIFFERENCE','UNKNOWN']}
    report['state']='CLI_BEHAVIOR_DIFFERENCE' if report['counts']['DIFFERENCE'] else 'CLI_PARITY_OBSERVED'
    if not all(report['controls'][k] for k in ['reference_replay_qualified','changed_native_output_detected','head_withdrawal_identical']) or not report['source_preserved'] or report['counts']['UNKNOWN']:report['state']='UNKNOWN'
    save(out/'result.json',report);print(json.dumps({'profile':args.profile,'state':report['state'],'counts':report['counts'],'controls':{k:v for k,v in report['controls'].items() if isinstance(v,bool)}}))

if __name__=='__main__':
    try:main()
    except Exception as e:
        import sys
        if '--output' in sys.argv:
            out=Path(sys.argv[sys.argv.index('--output')+1]);out.mkdir(exist_ok=True);p=out/'result.json';r=json.loads(p.read_text()) if p.exists() else {};save(p,{**r,'state':'UNKNOWN','reason':str(e)[-1500:]})
        raise
