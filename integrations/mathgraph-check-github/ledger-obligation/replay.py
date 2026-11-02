"""Frozen native gate protocol. Runs only on an owned push, without App/model secrets."""
from pathlib import Path
import subprocess, json, hashlib, os, shutil
BASE='219f133cc93172fea46b08d09edf9b3b6441c0a4'
REPAIR='821c715217f135c73abb643df2878557ca099380'
SUBJECT='metalogiclabs/L4YAML'
TOOLCHAIN='leanprover/lean4:v4.35.0'
ROOT=Path.cwd(); OUT=ROOT/'ledger-results'; OUT.mkdir(exist_ok=True)
WORK=ROOT/'ledger-work'; WORK.mkdir(exist_ok=True)
MARK='MG_GATE_ORACLE_EXECUTED'
PAYLOAD='\'print("'+MARK+'")\''
CASES=[('clean',"printf 'clean\\n'\n",False),('direct','python3 -c '+PAYLOAD+'\n',True),('no_bytecode','python3 -B -c '+PAYLOAD+'\n',True),('isolated','python3 -I -c '+PAYLOAD+'\n',True),('warning_option','python3 -W ignore -c '+PAYLOAD+'\n',True),('heredoc_data',"cat <<'EOF'\npython3 -c "+PAYLOAD+'\nEOF\n',False),('literal_backslashes','echo '+chr(92)*2+'\npython3 -c '+PAYLOAD+'\n',True)]

def run(args,cwd,timeout=180):
    return subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout)
def must(args,cwd,timeout=180):
    p=run(args,cwd,timeout)
    assert p.returncode==0,(args,(p.stdout+p.stderr)[-6000:])
    return p.stdout.strip()
def log(name,p):
    (OUT/name).write_text(p.stdout+p.stderr)
def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

repo=WORK/'subject'
must(['git','init','-q',str(repo)],ROOT)
for sha in [BASE,REPAIR]:
    must(['git','fetch','--depth=1','--no-tags','https://github.com/'+SUBJECT+'.git',sha],repo)
# Freeze regression text from the repaired commit and replay identically in all arms.
guard_source=must(['git','show',REPAIR+':Scripts/Ledger.lean'],repo)
guard_body=guard_source.split('-- BEGIN PYTHON OPTION REGRESSION GUARDS\n',1)[1].split('-- END PYTHON OPTION REGRESSION GUARDS',1)[0]
guards='import Scripts.Ledger\nopen Scripts.Ledger\n'+guard_body
(OUT/'frozen-regression-guards.lean').write_text(guards)
identities=[]; arms=[]
for arm,sha in [('original',BASE),('repaired',REPAIR),('withdrawn',BASE)]:
    must(['git','checkout','--detach',sha],repo)
    assert must(['git','rev-parse','HEAD'],repo)==sha
    w=WORK/arm; (w/'Scripts/Main').mkdir(parents=True,exist_ok=True)
    for rel in ['Scripts/Ledger.lean','Scripts/Main/CheckScriptsLedger.lean']:
        data=(repo/rel).read_bytes(); (w/rel).write_bytes(data)
        git_blob=must(['git','rev-parse',sha+':'+rel],repo)
        assert blob(data)==git_blob
        identities.append({'arm':arm,'source_sha':sha,'path':rel,'git_blob':git_blob,'sha256':hashlib.sha256(data).hexdigest()})
        (OUT/(arm+'-'+Path(rel).name)).write_bytes(data)
    (w/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage LedgerProbe\nlean_lib Scripts where\n  roots := #[`Scripts.Ledger]\nlean_exe gate where\n  root := `Scripts.Main.CheckScriptsLedger\n  supportInterpreter := true\n')
    (w/'lean-toolchain').write_text(TOOLCHAIN+'\n')
    p=run(['lake','build','gate'],w); log(arm+'-build.log',p)
    assert p.returncode==0,(arm,(p.stdout+p.stderr)[-6000:])
    (w/'Regression.lean').write_text(guards)
    p=run(['lake','env','lean','Regression.lean'],w);log(arm+'-guards.log',p)
    assert p.returncode in [0,1]
    guards_exit=p.returncode
    if arm!='repaired':
        # The old module built, and the identical guard file fails on actual #guard checks.
        assert guards_exit==1 and 'did not evaluate to `true`' in p.stdout and 'Fields missing' not in p.stdout and 'sorryAx' not in p.stdout and 'unknown identifier' not in p.stdout,p.stdout
    gate=str(w/'.lake/build/bin/gate');rows=[]
    for name,text,expected in CASES:
        fixture=w/'fixtures'/name;(fixture/'scripts').mkdir(parents=True,exist_ok=True)
        (fixture/'scripts/probe.sh').write_text(text)
        (fixture/'scripts/scripts-ledger.txt').write_text('# open: 0\n')
        (fixture/'lakefile.lean').write_text('')
        oracle=run(['bash','--noprofile','--norc','-c',text],fixture,20)
        observed=MARK in oracle.stdout.splitlines()
        log(arm+'-oracle-'+name+'.log',oracle)
        assert oracle.returncode==0 and observed==expected,(arm,name,oracle.stdout)
        p=run([gate,'-C',str(fixture)],w);log(arm+'-gate-'+name+'.log',p)
        assert p.returncode in [0,1],p.stderr
        rows.append({'id':name,'oracle_exit':oracle.returncode,'oracle_executed':observed,'gate_exit':p.returncode})
    probe=repo/'scripts/mathgraph_obligation_probe.sh';assert not probe.exists()
    exits=[]
    try:
        for name,text in [('baseline',None),('direct',CASES[1][1]),('no_bytecode',CASES[2][1]),('withdrawal',None)]:
            if text is None:
                if probe.exists():probe.unlink()
            else:probe.write_text(text)
            p=run([gate,'-C',str(repo)],w);log(arm+'-repository-'+name+'.log',p)
            assert p.returncode in [0,1],p.stderr
            exits.append(p.returncode)
    finally:
        if probe.exists():probe.unlink()
    clean=must(['git','status','--porcelain'],repo)==''
    arms.append({'id':arm,'source_sha':sha,'guards_exit':guards_exit,'rows':rows,'repository_exits':exits,'restored_clean':clean})
report={'schema':'mathgraph.ledger-obligation.v1','subject':{'repository':SUBJECT,'base_sha':BASE,'head_sha':REPAIR},'verifier':{'repository':'metalogiclabs/mathgraph','head_sha':os.environ['GITHUB_SHA'],'toolchain':TOOLCHAIN},'run':{'id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT'])},'cases':[x[0] for x in CASES],'arms':arms,'source_identities':identities,'boundary':'Finite controls over standalone native gate, not full L4YAML CI or arbitrary shell coverage'}
(OUT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
with (OUT/'SHA256SUMS').open('w') as out:
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name!='SHA256SUMS':out.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
print(json.dumps({'arms':[{k:a[k] for k in ['id','guards_exit','repository_exits']} for a in arms],'native_rows':sum(len(a['rows']) for a in arms)}))
