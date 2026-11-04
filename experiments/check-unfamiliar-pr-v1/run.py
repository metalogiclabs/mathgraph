"""Prospective PR226 Python/Lean command comparison; diagnostic replay is explicitly controlled."""
from pathlib import Path
import subprocess,json,hashlib,shutil,sys,os
head=Path(sys.argv[1]).resolve();base=Path(sys.argv[2]).resolve();out=Path('unfamiliar-evidence').resolve();out.mkdir(exist_ok=True)
target='L4YAML/Proofs/Production/StreamAccum.lean';original=(head/target).read_bytes()
commands=[('park-top','park_top_price.py'),('vslot-top','vslot_top_price.py'),('mv-slot-top','mv_slot_top_price.py'),('open-map','open_map_price.py'),('park-nic0','park_nic0_price.py'),('landing-nic0','landing_nic0_price.py')]
project=out/'compiled';(project/'Scripts').mkdir(parents=True,exist_ok=True);shutil.copytree(head/'Scripts',project/'Scripts',dirs_exist_ok=True)
(project/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage Prospective\nlean_lib Scripts\nlean_exe price where\n  root := `Scripts.Main.Price\n  supportInterpreter := true\n')
(project/'lean-toolchain').write_text('leanprover/lean4:v4.35.0\n')
lean=Path.home()/'.elan/toolchains/leanprover--lean4---v4.35.0';assert (lean/'bin/lean').is_file()
def run(args,timeout=300):return subprocess.run(args,text=True,capture_output=True,timeout=timeout)
p=run(['docker','pull','ubuntu:24.04']);assert p.returncode==0
image=run(['docker','image','inspect','ubuntu:24.04','--format','{{index .RepoDigests 0}}']).stdout.strip();build=out/'image';build.mkdir(exist_ok=True)
(build/'Dockerfile').write_text('FROM '+image+'\nRUN apt-get update && apt-get install -y --no-install-recommends python3 build-essential libgmp10 && rm -rf /var/lib/apt/lists/*\n')
p=run(['docker','build','-t','mg-prospective',str(build)],600);(out/'image.log').write_text(p.stdout+p.stderr);assert p.returncode==0
for q in [project,*project.rglob('*')]:q.chmod(0o777 if q.is_dir() else 0o666)
common=['docker','run','--rm','--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit','128','--memory','2g','--cpus','2','--user','1000:1000','--tmpfs','/tmp:rw,nosuid,size=512m','-v',str(lean)+':/opt/lean:ro','-v',str(project)+':/compiled:rw','-e','HOME=/tmp','-e','PATH=/opt/lean/bin:/usr/bin:/bin','-w','/compiled','mg-prospective']
p=run(common+['lake','build','price'],600);(out/'native-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,'NATIVE_BUILD_FAILED'
rows=[]
for script,py in commands:
 for kind in ['ordinary','diagnostics','empty','missing']+(['payers'] if script in ['park-nic0','landing-nic0'] else []):
  for arm in ['python','lean']:
   root=out/(script+'-'+kind+'-'+arm);(root/Path(target).parent).mkdir(parents=True,exist_ok=True)
   if kind!='missing':(root/target).write_bytes(b'' if kind=='empty' else original)
   (root/'bin').mkdir(exist_ok=True)
   # Only downstream compiler diagnostics are replayed; both commands execute unchanged.
   (root/'bin/lake').write_text('#!/usr/bin/python3\nfrom pathlib import Path\nimport sys\np=Path('+repr(target)+')\nPath("observed-probe.lean").write_bytes(p.read_bytes())\n'+('print('+repr(target+':1:1: error: controlled replay\n'+target+':100:2: error: controlled replay\n'+target+':100:3: error: controlled replay\n'+target+':500:1: error: controlled replay')+')\n' if kind=='diagnostics' else '')+'sys.exit(1)\n');(root/'bin/lake').chmod(0o755)
   shutil.copy(base/'scripts'/py,root/py)
   for q in [root,*root.rglob('*')]:q.chmod(0o777 if q.is_dir() else 0o666)
   pos=['payers'] if kind=='payers' else []
   args=['python3',py]+pos if arm=='python' else ['/compiled/.lake/build/bin/price',script]+pos
   dock=common[:];dock[dock.index('PATH=/opt/lean/bin:/usr/bin:/bin')]='PATH=/work/bin:/opt/lean/bin:/usr/bin:/bin';dock[dock.index('/compiled')+0]='/work' # value following -w
   dock[dock.index('mg-prospective'):dock.index('mg-prospective')]=['-v',str(root)+':/work:rw']
   p=run(dock+args,90)
   outputs={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file() and f.name not in [py,'lake'] and '__pycache__' not in str(f)}
   rows.append({'script':script,'kind':kind,'arm':arm,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'files':outputs,'restored':not (root/target).exists() if kind=='missing' else (root/target).read_bytes()==(b'' if kind=='empty' else original)})
comparisons=[]
for i in range(0,len(rows),2):
 a,b=rows[i:i+2];strict=a['kind'] in ['ordinary','diagnostics','payers'];same=a['exit']==b['exit'] and a['stdout']==b['stdout'] and a['files']==b['files']
 comparisons.append({'script':a['script'],'kind':a['kind'],'strict_report_case':strict,'parity':same,'restored':a['restored'] and b['restored'],'python_exit':a['exit'],'lean_exit':b['exit']})
result={'status':'OBSERVED_NOT_YET_INTERPRETED','source_head':'d14e24e2de55fc2c5a4402db15b2d8cb5903d028','base':'8fdc991b6dfebe1114858f6649e15c5cea2e5eff','protocol_commit':'bd7de0314c48f4e95337bd8e3606718045688115','boundary':'Real unchanged commands; real selected native build/guards; identical actual source input; compiler-output replay only, not actual proof validity. Missing/empty failure outputs retained separately from strict report cases. No repair preloaded.','comparisons':comparisons,'observations':rows}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(comparisons,indent=2))
assert all(x['restored'] for x in comparisons),'SOURCE_RESTORATION_FAILED'
