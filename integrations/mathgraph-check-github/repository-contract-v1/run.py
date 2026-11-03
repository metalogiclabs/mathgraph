"""One fixed owned-fork contract across independently pinned PR requests.

Native compilation + protected finite regression only. No whole-PR approval.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,sys,tarfile,urllib.request
HERE=Path(__file__).resolve().parent
LEGACY=HERE.parents[2]/'experiments/check-l4-pr-matrix-v1'
sys.path.insert(0,str(LEGACY))
from native import run,must,sha
from native_modules import chunk_result
from contract import scope,closure,comparison

def write(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pr',type=int,required=True);parser.add_argument('--base',required=True);parser.add_argument('--head',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    for revision in [args.base,args.head]:
        if not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('INVALID_REVISION')
    if args.pr<1:raise ValueError('INVALID_PR')
    out=Path(args.output).resolve();out.mkdir();logs=out/'logs';logs.mkdir()
    contract_path=HERE/'contract.json';contract=json.loads(contract_path.read_text());repo=contract['repository']
    if repo!='metalogiclabs/L4YAML':raise ValueError('REPOSITORY_NOT_ENABLED')
    controller=os.environ['GITHUB_SHA']
    report={'schema':'mathgraph.repository-contract.report.v1','repository':repo,'pr':args.pr,'base_sha':args.base,'head_sha':args.head,'controller_sha':controller,'contract_sha256':sha(contract_path),'state':'UNKNOWN','whole_pr_correctness':'UNKNOWN','semantic_authority':contract['authority'],'arms':{}}
    write(out/'result.json',report)
    def api(path):
        with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+path,headers={'User-Agent':'MathGraph-Repository-Contract','Accept':'application/vnd.github+json'}),timeout=40) as r:return json.load(r)
    def pinned(pr):
        return pr['head']['sha']==args.head and pr['base']['sha']==args.base and all(pr[x]['repo']['full_name']==repo and not pr[x]['repo']['private'] for x in ['head','base'])
    pr=api('/pulls/'+str(args.pr))
    if not pinned(pr):raise ValueError('PR_IDENTITY_CHANGED')
    files=[]
    for page in range(1,11):
        batch=api(f'/pulls/{args.pr}/files?per_page=100&page={page}');files+=batch
        if len(batch)<100:break
    if len(files)!=pr['changed_files']:raise ValueError('INCOMPLETE_CHANGED_FILES')
    selection=scope(files);report['scope']=selection;report['changed_files']=len(files);write(out/'snapshot.json',{'base_sha':args.base,'head_sha':args.head,'files':files});write(out/'result.json',report)
    def download(revision,path,digest):
        with urllib.request.urlopen(f'https://raw.githubusercontent.com/{repo}/{revision}/{path}',timeout=40) as r:data=r.read(1_000_001)
        if len(data)>1_000_000 or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('FROZEN_REFERENCE_IDENTITY_MISMATCH')
        return data.decode()
    # Frozen oracle construction, never evaluated against head-controlled tests.
    inputs=out/'input';inputs.mkdir();(inputs/'oracles').mkdir();config=json.loads((LEGACY/'module-config.json').read_text());acquired=[]
    for m in config:
        acquired.append({**m,'source':download(m['head_sha'],m['path'],m['source_sha256'])})
        if m.get('oracle_path'):(inputs/'oracles'/f"{m['n']}.py").write_text(download(m['base_sha'],m['oracle_path'],m['oracle_sha256']))
        if m.get('grammar_sha256'):(inputs/'SurfaceNode.lean').write_text(download(m['head_sha'],'L4YAML/Surface/Node.lean',m['grammar_sha256']))
    write(inputs/'module-inputs.json',acquired)
    lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0';must(['docker','pull','ubuntu:24.04'])
    base_image=must(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}'])
    image=out/'image';image.mkdir();(image/'Dockerfile').write_text('FROM '+base_image+'\nRUN apt-get update && apt-get install -y --no-install-recommends python3 build-essential libgmp10 && rm -rf /var/lib/apt/lists/*\n')
    must(['docker','build','-t','mathgraph-repository-contract',str(image)],420)
    report['runtime']={'lean':must([str(lean/'bin/lean'),'--version']),'image_id':must(['docker','image','inspect','mathgraph-repository-contract','--format','{{.Id}}']),'base_image':base_image}
    def permissions(folder):
        for p in [folder,*folder.rglob('*')]:
            if p.stat().st_uid==os.getuid():p.chmod(0o777 if p.is_dir() else 0o666)
    def execute(work,label,command,source=None,audit=None,timeout=150):
        permissions(work);name='mg-contract-'+label
        mounts=['-v',str(lean)+':/opt/lean:ro','-v',str(work)+':/work:rw','-v',str(LEGACY)+':/controller:ro']
        if source:mounts+=['-v',str(source)+':/source:ro','-v',str(work/'lakefile.lean')+':/work/lakefile.lean:ro']
        if audit:mounts+=['-v',str(audit)+':/audit:ro']
        cmd=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','3g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','HOME=/tmp','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-e','LEAN_PATH=/work/.lake/build/lib/lean','-w','/work',*mounts,'mathgraph-repository-contract']+command
        r=run(cmd,timeout);run(['docker','rm','-f',name],20);(logs/(label+'.log')).write_text(r.stdout+r.stderr);return r
    g=execute(out,'corpus',['python3','/controller/make_module_probes.py','/work/input','/work/corpus.json'])
    if g.returncode:raise ValueError('FROZEN_CORPUS_GENERATION_FAILED')
    corpus=json.loads((out/'corpus.json').read_text());digest=sha(out/'corpus.json')
    expected=(HERE/'corpus.sha256').read_text().strip()
    if digest!=expected or sum(len(x['probes']) for x in corpus)!=contract['regression']['expected_cases']:raise ValueError('FROZEN_CORPUS_CHANGED')
    report['corpus_sha256']=digest;write(out/'result.json',report)
    protected=[m['module'] for m in corpus]
    def acquire(revision,label):
        archive=out/(label+'.tar.gz')
        with urllib.request.urlopen('https://codeload.github.com/'+repo+'/tar.gz/'+revision,timeout=45) as r:data=r.read(50_000_001)
        if len(data)>50_000_000:raise ValueError('SNAPSHOT_TOO_LARGE')
        archive.write_bytes(data);folder=out/(label+'-source');folder.mkdir()
        with tarfile.open(archive) as t:
            members=t.getmembers()
            if len(members)>20000 or sum(x.size for x in members)>150_000_000:raise ValueError('SNAPSHOT_EXTRACTION_LIMIT')
            t.extractall(folder,filter='data')
        children=list(folder.iterdir())
        if len(children)!=1 or any(p.is_symlink() for p in folder.rglob('*')):raise ValueError('UNSAFE_SOURCE_TREE')
        return children[0],sha(archive)
    def arm(revision,label):
        tree,archive_hash=acquire(revision,label);roots=protected+[m for m in selection['modules']+selection['deleted_modules'] if (tree/Path(m.replace('.','/')+'.lean')).is_file()]
        dependencies=closure(tree,roots);source=out/(label+'-selected');source.mkdir()
        for module in dependencies:
            rel=Path(module.replace('.','/')+'.lean');dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(tree/rel,dest)
        identities={str(p.relative_to(source)):sha(p) for p in source.rglob('*.lean')}
        work=out/(label+'-work');work.mkdir();(work/'lean-toolchain').write_text(contract['toolchain']+'\n')
        (work/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage mathgraphContract where\n  leanOptions := #[⟨`autoImplicit, false⟩]\nlean_lib Scripts where\n  srcDir := "/source"\n  roots := #['+', '.join('`'+x for x in sorted(set(roots)))+']\n')
        result={'qualified':False,'source_sha':revision,'archive_sha256':archive_hash,'modules':dependencies,'roots':sorted(set(roots)),'source_hashes':identities,'failed':[],'unknown':[],'passed':0,'cases':0}
        build=execute(work,label+'-build',['lake','build','Scripts'],source=source,timeout=300);result['build_exit']=build.returncode
        if build.returncode:result['reason']='SOURCE_BUILD_FAILED';return result
        # Original source guards run during that build. External expectations are
        # separately mounted read-only, not inserted into the submitted tree.
        for m in corpus:
            audit=out/(label+'-audit-'+str(m['n']));audit.mkdir();header='import '+m['module']+'\nopen '+m['module']+'\nset_option maxRecDepth 100000\nset_option maxHeartbeats 4000000\n'
            (audit/'Pass.lean').write_text(header+'#guard true\n');(audit/'Fail.lean').write_text(header+'#guard false\n')
            good=execute(work,f"{label}-{m['n']}-true",['lean','/audit/Pass.lean'],source,audit)
            bad=execute(work,f"{label}-{m['n']}-false",['lean','/audit/Fail.lean'],source,audit)
            controls=good.returncode==0 and bad.returncode==1 and 'did not evaluate to `true`' in bad.stdout+bad.stderr and len(re.findall(r'\berror:',bad.stdout+bad.stderr))==1
            if not controls:result['reason']='NATIVE_CONTROLS_FAILED';return result
            for start in range(0,len(m['probes']),64):
                probes=m['probes'][start:start+64];(audit/'Audit.lean').write_text(header+''.join('#guard ('+x['expression']+') == ('+x['expected']+')\n' for x in probes))
                r=execute(work,f"{label}-{m['n']}-{start}",['lean','/audit/Audit.lean'],source,audit);state=chunk_result(r.returncode,r.stdout+r.stderr,len(probes))
                result['cases']+=len(probes)
                if not state['qualified']:result['unknown'].extend(f"{m['n']}:{start+i}" for i in range(len(probes)));continue
                result['passed']+=len(probes)-len(state['failed']);result['failed'].extend(f"{m['n']}:{start+i}" for i in state['failed'])
        same=all(sha(source/path)==digest for path,digest in identities.items())
        result['qualified']=same and not result['unknown'] and result['cases']==contract['regression']['expected_cases']
        if not same:result['reason']='SOURCE_IDENTITY_CHANGED';result['failed']=[];result['passed']=0
        return result
    for side,revision in [('base',args.base),('head',args.head)]:
        try:report['arms'][side]=arm(revision,side)
        except Exception as error:report['arms'][side]={'qualified':False,'failed':[],'reason':type(error).__name__+': '+str(error)[-1000:]}
        write(out/'result.json',report)
    report['state']=comparison(report['arms']['base'],report['arms']['head'])
    if not pinned(api('/pulls/'+str(args.pr))):report['state']='STALE'
    report['production_deployment']='UNCHANGED';report['whole_pr_correctness']='UNKNOWN';write(out/'result.json',report)
    print(json.dumps({'pr':args.pr,'state':report['state'],'uncovered':selection['uncovered'],'contract':report['contract_sha256'],'corpus':digest}))
    if report['state'] in ['UNKNOWN','STALE']:sys.exit(1)

if __name__=='__main__':
    try:main()
    except Exception as error:
        # Preserve setup failures without manufacturing native results.
        if '--output' in sys.argv:
            out=Path(sys.argv[sys.argv.index('--output')+1]);out.mkdir(exist_ok=True)
            existing=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
            write(out/'result.json',{**existing,'state':'UNKNOWN','reason':type(error).__name__+': '+str(error)[-1500:]})
        raise
