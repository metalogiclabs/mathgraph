"""Finite differential replay of four pinned L4YAML tool modules.

This is a research profile with explicit adapters, not hosted arbitrary-PR support.
"""
from pathlib import Path
import json,os,re,shutil,sys,urllib.request
from native import run,must,sha

def chunk_result(code,text,count):
    errors=list(re.finditer(r'Audit\.lean:(\d+):\d+: error: ([^\n]+)',text))
    failed={int(x.group(1))-5 for x in errors if x.group(2)=='Expression'}
    guard_false=text.count('did not evaluate to `true`')
    decisive=(code==0 and not re.search(r'\berror:',text)) or (code==1 and len(errors)==len(failed)==guard_false and guard_false>0 and all(0<=i<count for i in failed) and len(re.findall(r'\berror:',text))==len(errors))
    return {'qualified':bool(decisive),'failed':sorted(failed) if decisive else []}

def record_result(path,context,results,report):
    results.append(report)
    pending=path.with_suffix('.tmp')
    pending.write_text(json.dumps({**context,'modules':results},indent=2)+'\n')
    pending.replace(path)

def main():
    config=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]).resolve();out.mkdir();inputs=out/'input';inputs.mkdir();(inputs/'oracles').mkdir()
    def download(revision,path,digest):
        assert re.fullmatch('[a-f0-9]{40}',revision)
        assert all(re.fullmatch('[A-Za-z0-9_.-]+',x) and x not in ['.','..'] for x in path.split('/'))
        with urllib.request.urlopen(f'https://raw.githubusercontent.com/metalogiclabs/L4YAML/{revision}/{path}',timeout=45) as r:data=r.read(1_000_001)
        assert len(data)<=1_000_000
        import hashlib
        assert hashlib.sha256(data).hexdigest()==digest
        return data.decode()
    acquired=[]
    for m in config:
        source=download(m['head_sha'],m['path'],m['source_sha256']);acquired.append({**m,'source':source})
        if m.get('oracle_path'):(inputs/'oracles'/f"{m['n']}.py").write_text(download(m['base_sha'],m['oracle_path'],m['oracle_sha256']))
        if m.get('grammar_sha256'):(inputs/'SurfaceNode.lean').write_text(download(m['head_sha'],'L4YAML/Surface/Node.lean',m['grammar_sha256']))
    (inputs/'module-inputs.json').write_text(json.dumps(acquired)+'\n')
    lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0';must(['docker','pull','ubuntu:24.04'])
    base=must(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}'])
    image=out/'image';image.mkdir();(image/'Dockerfile').write_text('FROM '+base+'\nRUN apt-get update && apt-get install -y --no-install-recommends python3 libgmp10 && rm -rf /var/lib/apt/lists/*\n');must(['docker','build','-t','mathgraph-module-matrix',str(image)],420)
    controller=Path(__file__).resolve().parent;logs=out/'logs';logs.mkdir()
    def execute(folder,label,cmd,timeout=120):
        # Container-generated oleans belong to uid1000; the host runner must not
        # chmod another user's outputs on subsequent invocations.
        for p in [folder,*folder.rglob('*')]:
            if p.stat().st_uid==os.getuid():p.chmod(0o777 if p.is_dir() else 0o666)
        name='mg-module-'+label
        args=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','2g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','HOME=/tmp','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-e','LEAN_PATH=/work','-v',str(lean)+':/opt/lean:ro','-v',str(controller)+':/controller:ro','-v',str(folder)+':/work:rw','-w','/work','mathgraph-module-matrix']+cmd
        r=run(args,timeout);run(['docker','rm','-f',name],20);(logs/(label+'.log')).write_text(r.stdout+r.stderr);return r
    g=execute(out,'oracle-generation',['python3','/controller/make_module_probes.py','/work/input','/work/module-probes.json']);assert g.returncode==0,'ORACLE_GENERATION_UNKNOWN'
    manifest=json.loads((out/'module-probes.json').read_text());results=[]
    context={'controller_sha':os.environ['GITHUB_SHA'],'base_image':base,'image_id':must(['docker','image','inspect','mathgraph-module-matrix','--format','{{.Id}}']),'lean':must([str(lean/'bin/lean'),'--version']),'corpus_sha256':sha(out/'module-probes.json')}
    for m in manifest:
        folder=out/('module-'+str(m['n']));folder.mkdir();path=folder/m['path'];path.parent.mkdir(parents=True);path.write_text(next(a['source'] for a in acquired if a['n']==m['n']))
        label='pr-'+str(m['n']);b=execute(folder,label+'-build',['lean','-o',str(Path(m['path']).with_suffix('.olean')),m['path']])
        report={'pr':m['n'],'head_sha':m['head_sha'],'base_sha':m['base_sha'],'source_sha256':m['source_sha256'],'oracle_sha256':m['oracle_sha256'],'build_exit':b.returncode,'total':len(m['probes']),'failed':[],'unknown':[],'passed':0,'scope':'FINITE_PURE_MODULE_PARITY_ONLY','semantic_authority':m['oracle_authority']}
        if b.returncode:report['status']='UNKNOWN';report['reason']='MODULE_BUILD_FAILED';record_result(out/'result.json',context,results,report);continue
        def header():return 'import '+m['module']+'\nopen '+m['module']+'\nset_option maxRecDepth 100000\nset_option maxHeartbeats 4000000\n'
        (folder/'Pass.lean').write_text(header()+'#guard true\n');(folder/'Fail.lean').write_text(header()+'#guard false\n')
        good=execute(folder,label+'-control-pass',['lean','Pass.lean']);bad=execute(folder,label+'-control-fail',['lean','Fail.lean'])
        controls=good.returncode==0 and bad.returncode==1 and 'did not evaluate to `true`' in bad.stdout+bad.stderr
        if not controls:report['status']='UNKNOWN';report['reason']='NATIVE_CONTROLS_FAILED';record_result(out/'result.json',context,results,report);continue
        for start in range(0,len(m['probes']),64):
            probes=m['probes'][start:start+64];file=folder/'Audit.lean';file.write_text(header()+''.join('#guard ('+p['expression']+') == ('+p['expected']+')\n' for p in probes))
            r=execute(folder,label+'-chunk-'+str(start),['lean','Audit.lean']);text=r.stdout+r.stderr
            admitted=chunk_result(r.returncode,text,len(probes));failed=admitted['failed']
            if not admitted['qualified']:report['unknown'].extend(range(start,start+len(probes)));continue
            report['passed']+=len(probes)-len(failed)
            report['failed'].extend({'index':start+i,**probes[i]} for i in sorted(failed))
        if sha(path)!=m['source_sha256']:report['unknown']=list(range(len(m['probes'])));report['failed']=[];report['passed']=0
        report['status']='UNKNOWN' if report['unknown'] else ('CANDIDATE_PARITY_DIFFERENCE' if report['failed'] else 'NO_DIFFERENCE_IN_FINITE_CORPUS')
        record_result(out/'result.json',context,results,report);print(json.dumps({k:v for k,v in report.items() if k not in ['failed','unknown']}),flush=True)
    if len(results)!=len(config) or any(r['status']=='UNKNOWN' for r in results):sys.exit(1)

if __name__=='__main__':main()
