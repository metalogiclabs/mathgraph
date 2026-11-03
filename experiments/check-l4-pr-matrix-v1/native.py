"""Research-only fixed-command replay of reviewed owned-fork controls.

No model, no source-controlled commands, no credentials or network in containers.
Baseline contract authority is the experiment owner; this does not infer intent.
"""
from pathlib import Path
import json, os, re, shutil, subprocess, sys, hashlib, tarfile, urllib.request
from assess import compare, issues

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args, timeout=120):
    try: return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired: return subprocess.CompletedProcess(args, 124, '', 'TIMEOUT')
def must(args, timeout=180):
    r=run(args, timeout)
    if r.returncode: raise RuntimeError((r.stdout+r.stderr)[-1500:])
    return r.stdout.strip()

def main():
    config=json.loads(Path(sys.argv[1]).read_text()); out=Path(sys.argv[2]).resolve(); out.mkdir(exist_ok=True)
    revision=config['fixture_sha']; assert re.fullmatch('[0-9a-f]{40}', revision)
    archive=out/'subject.tar.gz'
    with urllib.request.urlopen('https://codeload.github.com/metalogiclabs/L4YAML/tar.gz/'+revision, timeout=45) as r: archive.write_bytes(r.read(50_000_001))
    assert archive.stat().st_size <= 50_000_000
    extracted=out/'subject'; extracted.mkdir()
    with tarfile.open(archive) as t: t.extractall(extracted, filter='data')
    subject=next(extracted.iterdir())/'MathGraphAuditFixtures'
    lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0'
    must(['docker','pull','ubuntu:24.04'])
    base=must(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}'])
    build=out/'image'; build.mkdir()
    (build/'Dockerfile').write_text('FROM '+base+'\nRUN apt-get update && apt-get install -y --no-install-recommends build-essential libgmp10 && rm -rf /var/lib/apt/lists/*\n')
    must(['docker','build','-t','mathgraph-audit-matrix',str(build)],420)
    logs=out/'logs';logs.mkdir()
    def execute(folder, label, cmd):
        assert re.fullmatch('[a-z0-9-]+',label)
        name='mg-matrix-'+label
        args=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','2g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-e','HOME=/tmp','-e','LEAN_PATH=/work/.lake/build/lib/lean:/work','-v',str(lean)+':/opt/lean:ro','-v',str(folder)+':/work:rw','-w','/work','mathgraph-audit-matrix']+cmd
        r=run(args);run(['docker','rm','-f',name],20)
        (logs/(label+'.log')).write_text(r.stdout+r.stderr)
        return r
    def prepare(folder):
        (folder/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage checkfixture\nlean_lib Subject\nlean_lib Consumer\nlean_exe gate where\n  root := `Gate\n  supportInterpreter := true\n')
        (folder/'lean-toolchain').write_text('leanprover/lean4:v4.35.0\n')
        for p in [folder,*folder.rglob('*')]:p.chmod(0o777 if p.is_dir() else 0o666)
    def arm(case, side, contract):
        src=subject/case/side; folder=out/(case+'-'+side);shutil.copytree(src,folder);prepare(folder)
        identity={p.name:sha(p) for p in src.iterdir() if p.is_file()}
        label=(case+'-'+side).replace('_','-')
        row={'complete':False,'hashes':identity,'contract_changed':json.loads((src/'contract.json').read_text())!=contract}
        r=execute(folder,label+'-build',['lake','build','gate']);row['build_exit']=r.returncode
        # A broken gate's unrelated compiler error is not a contract counterexample.
        if r.returncode: return row
        row['consumer_reached']=(folder/'.lake/build/lib/lean/Consumer.olean').is_file()
        row['gate_exit']=execute(folder,label+'-gate',['.lake/build/bin/gate']).returncode
        (folder/'Audit.lean').write_text(contract['consumer'])
        (folder/'Probe.lean').write_text(contract['probe'])
        (folder/'Axioms.lean').write_text('import Subject\n#print axioms '+contract['declaration']+'\n')
        for p in folder.glob('*.lean'):p.chmod(0o666)
        c=execute(folder,label+'-contract',['lean','Audit.lean']);b=execute(folder,label+'-probe',['lean','Probe.lean']);a=execute(folder,label+'-axioms',['lean','Axioms.lean'])
        def outcome(r, signature):
            if r.returncode==0:return 'PASS'
            return 'FAIL' if r.returncode==1 and re.search(signature,r.stdout+r.stderr) else 'UNKNOWN'
        row['contract']=outcome(c,r'(?i)error: (application )?type mismatch')
        row['behavior']=outcome(b,r'did not evaluate to `true`')
        text=a.stdout+a.stderr
        matches=re.findall(r"depends on axioms: \[([^\]]*)\]",text)
        no_axioms='does not depend on any axioms' in text
        axiom_known=a.returncode==0 and (no_axioms or len(matches)==1)
        axioms=[s.strip() for s in matches[0].split(',') if s.strip()] if matches else []
        row['unapproved_axioms']=[x for x in axioms if x not in contract['allowed_axioms']]
        row['generation']='NOT_REQUIRED'
        if contract['generated_exact']:
            g=execute(folder,label+'-generate',['lean','--run','Generate.lean'])
            row['generation']='UNKNOWN' if g.returncode else ('PASS' if g.stdout==(folder/'Subject.lean').read_text() else 'FAIL')
        row['complete']=axiom_known and row['contract']!='UNKNOWN' and row['behavior']!='UNKNOWN' and row['generation']!='UNKNOWN' and row['gate_exit'] in [0,1]
        if any(sha(folder/p)!=h for p,h in identity.items()):row['complete']=False;row['reason']='SOURCE_MUTATED'
        row['issues']=issues(row) if row['complete'] else []
        return row
    # Labels are used only after native evidence collection and admission.
    labels=json.loads((subject/'labels.json').read_text()); results=[]
    for item in labels:
        case=item['id'];assert re.fullmatch('[a-z_]+',case)
        contract=json.loads((subject/case/'base/contract.json').read_text())
        b=arm(case,'base',contract);h=arm(case,'head',contract)
        result={'id':case,'base':b,'head':h,'outcome':compare(b,h),'authority':'AUTHORED_CALIBRATION'}
        result['expected']=item['expected'];result['matches_label']=result['outcome']==item['expected'];results.append(result)
        (out/'controls.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({'id':case,'outcome':result['outcome'],'matches':result['matches_label']}),flush=True)
    report={'controller_sha':os.environ['GITHUB_SHA'],'fixture_sha':revision,'toolchain':must([str(lean/'bin/lean'),'--version']),'image':must(['docker','image','inspect','mathgraph-audit-matrix','--format','{{.Id}}']),'base_image':base,'archive_sha256':sha(archive),'controls':results}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if not all(r['matches_label'] for r in results):sys.exit(1)

if __name__=='__main__':main()
