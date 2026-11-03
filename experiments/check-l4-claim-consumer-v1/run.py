"""Pinned retrospective claim -> native proof -> dependent consumer experiment."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,importlib.util
from rules import sha,remove_empty_ctors,admit
HERE=Path(__file__).resolve().parent
CLI=HERE.parents[1]/'integrations/mathgraph-check-github/cli-parity-v1'
sys.path.insert(0,str(CLI))
# Avoid the identically named experiment rules module in sys.modules.
spec=importlib.util.spec_from_file_location('cli_rules',CLI/'rules.py');cr=importlib.util.module_from_spec(spec);spec.loader.exec_module(cr)
# Only reviewed archive acquisition/command capture functions are reused.
spec=importlib.util.spec_from_file_location('cli_native',CLI/'run.py');native=importlib.util.module_from_spec(spec)
original=sys.modules['rules'];sys.modules['rules']=cr
try:spec.loader.exec_module(native)
finally:sys.modules['rules']=original

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot',required=True);parser.add_argument('--output',required=True);a=parser.parse_args()
    out=Path(a.output).resolve();out.mkdir();logs=out/'logs';logs.mkdir();c=json.loads((HERE/'contract.json').read_text());controller=os.environ['GITHUB_SHA']
    r={'schema':'mathgraph.claim-consumer.receipt.v1','controller_sha':controller,**{k:c[k] for k in ['repository','base_sha','head_sha']},'contract_sha256':sha((HERE/'contract.json').read_bytes()),'probes_sha256':{p.name:sha(p.read_bytes()) for p in (HERE/'probes').glob('*.lean')},'arms':{}}
    def save():
        (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');(out/'assessment.json').write_text(json.dumps(admit(r,controller),indent=2)+'\n')
    save()
    snapshot=json.loads(Path(a.snapshot).read_text());pr,diff=cr.shared.hosted_snapshot(snapshot,c['repository'],c['fork_pr'],c['base_sha'],c['head_sha']);cr.shared.pinned_files(diff,c['base_sha'],c['head_sha'])
    attribution=json.loads((HERE/'claim-source.json').read_text())
    if sha(snapshot['upstream_claim']['body'].encode())!=attribution['body_sha256']:raise ValueError('DECLARED_CLAIM_CHANGED')
    base,bhash=native.acquire(c['repository'],c['base_sha'],out);head,hhash=native.acquire(c['repository'],c['head_sha'],out);r['archive_sha256']={'base':bhash,'head':hhash}
    base_modules=cr.project_closure(base,[c['module'],'L4YAML.Surface.Node']);modules=cr.project_closure(head,[c['module'],'L4YAML.Surface.Node','Scripts.Main.GenTraceOf'])
    lib_modules=[m for m in modules if not m.startswith('Scripts.')]
    def hashes(root,ms):return {m:sha((root/Path(m.replace('.','/')+'.lean')).read_bytes()) for m in ms}
    bh,hh=hashes(base,base_modules),hashes(head,lib_modules);target_module=c['module'];r['shared_dependencies_identical']={k:v for k,v in bh.items() if k!=target_module}=={k:v for k,v in hh.items() if k!=target_module};r['surface_identical']=sha((base/c['source']).read_bytes())==sha((head/c['source']).read_bytes())
    if not r['shared_dependencies_identical'] or not r['surface_identical']:save();raise ValueError('SHARED_ENVIRONMENT_CHANGED')
    selected=out/'selected';selected.mkdir()
    for m in modules:
        rel=Path(m.replace('.','/')+'.lean');dest=selected/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(head/rel,dest)
    r['source_sha256']={'base':bh,'head':hashes(head,modules),'python_oracle':sha((base/'scripts/gen_traceof.py').read_bytes())}
    build=out/'build';build.mkdir();(build/'lean-toolchain').write_text(c['toolchain']+'\n');(build/'lakefile.lean').write_text(cr.lake_config({'head_module':'Scripts.Main.GenTraceOf'},modules))
    lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0';native.must(['docker','pull','ubuntu:24.04']);digest=native.must(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}']);image=out/'image';image.mkdir();(image/'Dockerfile').write_text('FROM '+digest+'\nRUN apt-get update && apt-get install -y --no-install-recommends python3 build-essential libgmp10 && rm -rf /var/lib/apt/lists/*\n');native.must(['docker','build','-t','mathgraph-claim-consumer',str(image)],420)
    r['runtime']={'lean':native.must([str(lean/'bin/lean'),'--version']),'base_image':digest,'image_id':native.must(['docker','image','inspect','mathgraph-claim-consumer','--format','{{.Id}}'])}
    def docker(label,command,work=build,mounts=(),timeout=90):
        for p in [work,*work.rglob('*')]:
            if p.stat().st_uid==os.getuid():p.chmod(0o777 if p.is_dir() else 0o666)
        name='mg-claim-'+label
        cmd=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','4g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','HOME=/tmp','-e','LANG=C.UTF-8','-e','PYTHONDONTWRITEBYTECODE=1','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-e','LEAN_PATH=/work/.lake/build/lib/lean','-v',str(lean)+':/opt/lean:ro','-v',str(work)+':/work:rw','-v',str(selected)+':/source:ro','-v',str(HERE/'probes')+':/probes:ro','-w','/work']
        for src,dest in mounts:cmd+=['-v',str(src)+':'+dest+':ro']
        result=native.run(cmd+['mathgraph-claim-consumer']+command,timeout);native.run(['docker','rm','-f',name],20)
        (logs/(label+'.stdout')).write_text(result.stdout);(logs/(label+'.stderr')).write_text(result.stderr)
        return {'exit':result.returncode,'complete':result.returncode>=0 and result.returncode not in [124,125,126,127,137] and len((result.stdout+result.stderr).encode())<=c['limits']['output_bytes'],'stdout':result.stdout,'stderr':result.stderr}
    initial=docker('initial-build',['lake','build','cli','L4YAML'],timeout=1200);r['initial_build']=initial;save()
    if initial['exit']!=0:raise ValueError('HEAD_DEPENDENCY_BUILD_FAILED')
    lib=build/'.lake/build/lib/lean';exe=build/'.lake/build/bin/cli'
    generation=out/'generation';generation.mkdir();(generation/'scripts').mkdir();(generation/'scripts/gen_traceof.py').touch();q=generation/c['source'];q.parent.mkdir(parents=True);shutil.copyfile(base/c['source'],q);(generation/'.lake/build/lib/lean').mkdir(parents=True)
    b=docker('python-generation',['python3','/work/scripts/gen_traceof.py'],generation,[(base/'scripts/gen_traceof.py','/work/scripts/gen_traceof.py'),(lib,'/work/.lake/build/lib/lean')]);h=docker('lean-generation',['/program'],generation,[(exe,'/program'),(lib,'/work/.lake/build/lib/lean')]);r['generation']={'base':b,'head':h};r['generator_outputs_match_checked_in']=b['exit']==h['exit']==0 and b['complete'] and h['complete'] and b['stdout']==(base/c['target']).read_text() and h['stdout']==(head/c['target']).read_text();save()
    if not r['generator_outputs_match_checked_in']:raise ValueError('GENERATED_MODULE_IDENTITY_UNCONFIRMED')
    target=selected/c['target'];original_target=target.read_text();deleted=remove_empty_ctors(h['stdout']);r['variant_sha256']={}
    weak=out/'WeakConsumer.lean';weak.write_text((HERE/'probes/WeakOffer.lean').read_text()+'\n'+(HERE/'probes/WeakConsumer.lean').read_text())
    for arm,content in [('base',b['stdout']),('head',h['stdout']),('head_deleted',deleted),('head_restored',h['stdout'])]:
        target.write_text(content);r['variant_sha256'][arm]=sha(content.encode());row={};r['arms'][arm]=row
        row['module']=docker(arm+'-module',['lake','build',c['module']],timeout=600);save()
        if row['module']['exit']!=0:raise ValueError('VARIANT_MODULE_BUILD_FAILED:'+arm)
        for key,filename in [('source_witness','SourceWitness.lean'),('strong_consumer','Consumer.lean'),('weak_offer','WeakOffer.lean'),('weak_consumer','WeakConsumer.lean')]:
            mounts=[(weak,'/probes/WeakConsumer.lean')] if key=='weak_consumer' else []
            row[key]=docker(arm+'-'+key,['lean','/probes/'+filename],mounts=mounts);save()
    target.write_text(original_target)
    r['law']=docker('weakening-law',['lean','/probes/WeakeningLaw.lean']);r['restoration_identical']=r['variant_sha256']['head']==r['variant_sha256']['head_restored'] and all(r['arms']['head'][k]==r['arms']['head_restored'][k] for k in c['arms']['head'] if k!='module');r['source_preserved']=hashes(base,base_modules)==bh and hashes(head,modules)==r['source_sha256']['head'] and sha((base/'scripts/gen_traceof.py').read_bytes())==r['source_sha256']['python_oracle'];save();print(json.dumps(admit(r,controller)))
    if admit(r,controller)['state']!='WARRANTED_BOUNDED':raise ValueError('CLAIM_CHAIN_UNQUALIFIED')

if __name__=='__main__':main()
