import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const here=fileURLToPath(new URL('.',import.meta.url));
const cli=join(here,'local-report-check.mjs'),lean=process.env.MATHGRAPH_LEAN_BIN;
let root,repo,original,candidate,broken,absent;
function git(args){const p=spawnSync('git',['-C',repo,...args],{encoding:'utf8'});assert.equal(p.status,0,p.stderr);return p.stdout.trim();}
async function commit(source,message){
 await writeFile(join(repo,'Tests/SuiteRunner/Reports.lean'),source);git(['add','.']);
 git(['-c','user.name=Check Test','-c','user.email=check-test@example.invalid','commit','-qm',message]);
 return git(['rev-parse','HEAD']);
}
before(async()=>{
 root=await mkdtemp(join(tmpdir(),'mathgraph-status-test-'));repo=join(root,'repo');
 await mkdir(join(repo,'Tests/SuiteRunner'),{recursive:true});git(['init','-q']);
 const source=await readFile(new URL('../../../experiments/check-report-integrity-v1/candidate.lean',import.meta.url),'utf8');
 original=await commit(source,'historical envelope repair retains status gap');
 const old='else if name == "failure" && isStart && cur.isSome then failed := true';
 assert.equal(source.split(old).length,2);
 const repaired=source.replace(old,'else if (name == "failure" || name == "error") && isStart && cur.isSome then failed := true');
 candidate=await commit(repaired,'controlled status repair');
 broken=await commit(repaired+'\ndef brokenStatusCheck := unknownStatusValue\n','compile failure');
 git(['rm','Tests/SuiteRunner/Reports.lean']);
 git(['-c','user.name=Check Test','-c','user.email=check-test@example.invalid','commit','-qm','module absent']);
 absent=git(['rev-parse','HEAD']);
});
after(async()=>{if(root)await rm(root,{recursive:true,force:true});});
async function invoke(name,base,head,{profile='junit-status-preservation-v1',extra=[]}={}){
 const out=join(root,name);
 const p=spawnSync(process.execPath,[cli,'--repo',repo,'--base',base,'--head',head,'--out',out,
  '--profile',profile,...(lean&&!extra.includes('--lean')?['--lean',lean]:[]),...extra],
  {encoding:'utf8',timeout:180000,maxBuffer:1024*1024});
 assert.equal(p.error,undefined,p.error?.message);
 let result,text;try{result=JSON.parse(await readFile(join(out,'result.json'),'utf8'));text=await readFile(join(out,'report.md'),'utf8');}catch{}
 return {p,result,text,out};
}

test('unsupported status profile is an explicit argument refusal',async()=>{
 const r=await invoke('bad-profile',original,original,{profile:'invented-profile'});
 assert.equal(r.p.status,2);assert.match(r.p.stderr,/UNSUPPORTED_PROFILE/);
});

test('status profile preserves missing-module and missing-runtime UNKNOWNs',async()=>{
 const missing=await invoke('missing-source',original,absent);
 assert.equal(missing.p.status,2);assert.equal(missing.result?.status,'UNKNOWN');assert.match(missing.result.reason,/MODULE_ABSENT/);
 const noLean=await invoke('missing-runtime',original,original,{extra:['--lean',join(root,'missing-lean')]});
 assert.equal(noLean.p.status,2);assert.equal(noLean.result?.status,'UNKNOWN');assert.match(noLean.result.reason,/LEAN/);
 assert.doesNotMatch(missing.text,/independently replayed|`native.json`/);
});

test('native status witness, repair, withdrawal and envelope checks remain distinct',{skip:!lean},async()=>{
 const baseline=await invoke('baseline',original,original);
 assert.equal(baseline.p.status,1,baseline.p.stdout+baseline.p.stderr);
 assert.equal(baseline.result.method.id,'junit-status-preservation-v1');
 assert.equal(baseline.result.head.observations.length,8);assert.equal(baseline.result.head.mismatches.length,4);
 const witness=baseline.result.head.observations.find(x=>x.id==='error_empty');
 assert.equal(witness.observed.accepted,true);assert.equal(witness.observed.rows[0][1],'PASS');
 assert.equal(witness.observed.summary.passed,1);assert.equal(witness.observed.summary.failed,0);
 assert.equal(witness.observed.summary.css,'pass');assert.equal(witness.expected.rows[0][1],'FAIL');
 assert.match(baseline.text,/XML acceptance/);assert.match(baseline.text,/Rendered/);

 const forward=await invoke('forward',original,candidate);
 assert.equal(forward.p.status,0,forward.p.stdout+forward.p.stderr);
 assert.equal(forward.result.base.mismatches.length,4);assert.equal(forward.result.head.mismatches.length,0);
 const fixed=forward.result.head.observations.find(x=>x.id==='error_empty');
 assert.equal(fixed.observed.rows[0][1],'FAIL');assert.equal(fixed.observed.summary.failed,1);
 assert.equal(fixed.observed.summary.css,'fail');
 const reverse=await invoke('reverse',candidate,original);
 assert.equal(reverse.p.status,1,reverse.p.stdout+reverse.p.stderr);assert.equal(reverse.result.head.mismatches.length,4);
 assert.equal(reverse.result.method.corpus_sha256,forward.result.method.corpus_sha256);
 const legacy=await invoke('legacy',original,candidate,{profile:'junit-report-integrity-v1'});
 assert.equal(legacy.p.status,0,legacy.p.stdout+legacy.p.stderr);
 assert.equal(legacy.result.base.observations.length,19);assert.equal(legacy.result.head.observations.length,19);
 assert.equal(legacy.result.base.mismatches.length,0);assert.equal(legacy.result.head.mismatches.length,0);

 const {assessStatusRevision}=await import('./report-status.mjs');
 const native=JSON.parse(await readFile(join(forward.out,'native.json'),'utf8'));
 const request=JSON.parse(await readFile(join(forward.out,'request.json'),'utf8'));
 for(const mutate of [a=>a.cases.pop(),a=>a.cases.push(a.cases[0]),a=>{a.cases[0].test_file_sha256='f'.repeat(64);},
  a=>{a.cases[0].observation={nonsense:true};},a=>{a.controls.fail.guard_false=false;},a=>{a.source_sha256='f'.repeat(64);}]){
  const arm=structuredClone(native.head);mutate(arm);const assessed=assessStatusRevision(arm,request.sources.head.source);
  assert.equal(assessed.complete,false);assert.ok(assessed.groups.every(g=>g.execution==='UNKNOWN'));
  assert.equal(assessed.observations.length,0);
 }
});

test('status compilation failure is incomplete evidence',{skip:!lean},async()=>{
 const r=await invoke('broken',candidate,broken);
 assert.equal(r.p.status,2);assert.equal(r.result.status,'UNKNOWN');
 assert.equal(r.result.head.complete,false);assert.equal(r.result.head.mismatches.length,0);
});
