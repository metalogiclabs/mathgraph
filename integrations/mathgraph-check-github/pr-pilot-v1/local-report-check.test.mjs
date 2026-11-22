import test, {before, after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, readFile, writeFile, rm, access, chmod, symlink} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {REPORT_CASES,REPORT_PROFILE,reportProbePlan} from './report-integrity.mjs';
import {renderProbe} from '../lean-investigator-v1/contracts.mjs';

const here=fileURLToPath(new URL('.',import.meta.url));
const cli=join(here,'local-report-check.mjs');
const lean=process.env.MATHGRAPH_LEAN_BIN;
let root,repo,original,repaired,changed,broken,absent;
function git(args){const p=spawnSync('git',['-C',repo,...args],{encoding:'utf8'});assert.equal(p.status,0,p.stderr);return p.stdout.trim();}
async function commit(text,message){
 await writeFile(join(repo,'Tests/SuiteRunner/Reports.lean'),text);
 git(['add','.']);git(['-c','user.name=Check Test','-c','user.email=check-test@example.invalid','commit','-qm',message]);
 return git(['rev-parse','HEAD']);
}
before(async()=>{
 root=await mkdtemp(join(tmpdir(),'mathgraph-report-test-'));repo=join(root,'repo');
 await mkdir(join(repo,'Tests/SuiteRunner'),{recursive:true});git(['init','-q']);
 original=await commit(await readFile(new URL('../../../experiments/check-report-integrity-v1/original.lean',import.meta.url),'utf8'),'original');
 const fixed=await readFile(new URL('../../../experiments/check-report-integrity-v1/candidate.lean',import.meta.url),'utf8');
 repaired=await commit(fixed,'repair');
 changed=await commit(fixed+'\n-- A later source revision; retained expectations stay identical.\n','later revision');
 broken=await commit(fixed+'\ndef brokenLocalCheck := noSuchIdentifier\n','compile failure');
 git(['rm','Tests/SuiteRunner/Reports.lean']);git(['-c','user.name=Check Test','-c','user.email=check-test@example.invalid','commit','-qm','module removed']);absent=git(['rev-parse','HEAD']);
});
after(async()=>{if(root)await rm(root,{recursive:true,force:true});});

async function invoke(name,base,head,extra=[]){
 await access(cli);
 const out=join(root,name);
 const p=spawnSync(process.execPath,[cli,'--repo',repo,'--base',base,'--head',head,'--out',out,...(lean&&!extra.includes('--lean')?['--lean',lean]:[]),...extra],{encoding:'utf8',timeout:180000,maxBuffer:1024*1024});
 assert.equal(p.error,undefined,p.error?.message);
 return {process:p,result:JSON.parse(await readFile(join(out,'result.json'),'utf8')),text:await readFile(join(out,'report.md'),'utf8'),out};
}

test('local entry point can be invoked without the private App',async()=>{
 const p=spawnSync(process.execPath,[cli,'--help'],{encoding:'utf8'});
 assert.equal(p.status,0,p.stderr);
 assert.match(p.stdout,/--repo/);assert.match(p.stdout,/--base/);assert.match(p.stdout,/--head/);
});
test('missing module produces a concrete UNKNOWN instead of a borrowed historical result',async()=>{
 const r=await invoke('absent',original,absent);
 assert.equal(r.process.status,2);assert.equal(r.result.status,'UNKNOWN');
 assert.match(r.result.reason,/MODULE_ABSENT/);assert.equal(r.result.cost.model_calls,0);
});
test('missing local Lean is UNKNOWN with retained source identities',async()=>{
 const r=await invoke('no-lean',original,repaired,['--lean',join(root,'missing-lean')]);
 assert.equal(r.process.status,2);assert.equal(r.result.status,'UNKNOWN');
 assert.equal(r.result.subjects.head.revision,repaired);assert.match(r.result.reason,/LEAN/);
});
test('output directories are immutable across attempts',async()=>{
 const out=join(root,'existing');await mkdir(out);await writeFile(join(out,'keep.txt'),'retained');
 const p=spawnSync(process.execPath,[cli,'--repo',repo,'--base',original,'--head',repaired,'--out',out],{encoding:'utf8'});
 assert.equal(p.status,2);assert.equal(await readFile(join(out,'keep.txt'),'utf8'),'retained');
 assert.match(p.stderr,/OUTPUT_ALREADY_EXISTS/);
});
test('incomplete observations cannot retain passing group labels',async()=>{
 const {assessRevision}=await import('./local-report-check.mjs');
 const hash=x=>createHash('sha256').update(x).digest('hex');
 const source='synthetic reducer input; not a native evidence claim';
 const good={exit_code:0,guard_false:false,other_errors:false};
 const row=(id,expression)=>({id,...good,test_file_sha256:hash(renderProbe(REPORT_PROFILE,expression))});
 const arm={build_exit:0,repository_gate_exit:0,gate_kind:'SELECTED_MODULE_BUILD',source_sha256:hash(source),
  controls:{pass:good,fail:{exit_code:1,guard_false:true,other_errors:false}},
  probes:reportProbePlan().tests.map(t=>row(t.id,t.expression)),
  cases:REPORT_CASES.map(c=>row(c.id,'(junitCases '+JSON.stringify(c.input)+').toOption.isSome == '+c.accepted))};
 assert.equal(assessRevision(arm,source).complete,true);
 for(const mutate of [a=>a.cases.pop(),a=>{a.controls.fail.guard_false=false;},a=>{a.source_sha256='f'.repeat(64);}]){
  const changed=structuredClone(arm);mutate(changed);const result=assessRevision(changed,source);
  assert.equal(result.complete,false);assert.ok(result.groups.every(g=>g.execution==='UNKNOWN'));
 }
});
test('early UNKNOWN report does not claim unexecuted reference or nonexistent evidence',async()=>{
 const {renderLocalReport}=await import('./local-report-check.mjs');
 const report=renderLocalReport({status:'UNKNOWN',reason:'MODULE_ABSENT',subjects:{},evidence:{},cost:{wall_seconds:0,native_processes:null}});
 assert.doesNotMatch(report,/is independently replayed|`native.json`|`reference.json`/);
});

test('native repair, later compatible revision and withdrawal use the same retained cases',{skip:!lean},async()=>{
 const forward=await invoke('forward',original,repaired);
 assert.equal(forward.process.status,0,forward.process.stderr+forward.process.stdout);
 assert.equal(forward.result.status,'OBSERVED_AGREEMENT');
 assert.equal(forward.result.base.mismatches.length,6);assert.equal(forward.result.head.mismatches.length,0);
 assert.equal(forward.result.base.observations.length,19);assert.equal(forward.result.head.observations.length,19);
 assert.equal(forward.result.comparison[0].change,'RESOLVED_FAILURE');
 assert.equal(forward.result.human_trial,'NOT_RUN');assert.equal(forward.result.cost.model_calls,0);
 assert.match(forward.text,/six|6/);assert.match(forward.text,/HtmlReport/);
 assert.doesNotMatch(forward.text,/github\.com\/[^\s]+\/actions\/runs\/\d/);

 const later=await invoke('later',repaired,changed);
 assert.equal(later.process.status,0,later.process.stderr+later.process.stdout);
 assert.equal(later.result.status,'OBSERVED_AGREEMENT');assert.equal(later.result.head.observations.length,19);
 assert.notEqual(later.result.subjects.base.source_sha256,later.result.subjects.head.source_sha256);
 assert.equal(later.result.method.plan_sha256,forward.result.method.plan_sha256);
 assert.equal(later.result.method.corpus_sha256,forward.result.method.corpus_sha256);
 assert.ok(later.result.cost.native_processes>0);

 const reverse=await invoke('withdrawal',repaired,original);
 assert.equal(reverse.process.status,1);assert.equal(reverse.result.status,'OBSERVED_MISMATCH');
 assert.equal(reverse.result.head.mismatches.length,6);assert.equal(reverse.result.comparison[0].change,'NEW_FAILURE');

 const same=await invoke('same',repaired,repaired);
 assert.equal(same.process.status,0);assert.ok(same.result.comparison.every(r=>r.change==='BOTH_PASS'));
 const {assessRevision}=await import('./local-report-check.mjs');
 const payload=JSON.parse(await readFile(join(forward.out,'request.json'),'utf8'));
 const native=JSON.parse(await readFile(join(forward.out,'native.json'),'utf8'));
 for(const mutate of [
   n=>{n.head.controls.fail.guard_false=false;},
   n=>{n.head.cases.pop();},
   n=>{n.head.cases[0].test_file_sha256='f'.repeat(64);},
   n=>{n.head.probes[0].other_errors=true;},
   n=>{n.head.source_sha256='e'.repeat(64);}
 ]){
   const n=structuredClone(native);mutate(n);
   const assessment=assessRevision(n.head,payload.sources.head.source);
   assert.equal(assessment.complete,false);assert.ok(assessment.groups.every(g=>g.execution==='UNKNOWN'));
 }
});
test('compilation failure is UNKNOWN, not an observed discrepancy',{skip:!lean},async()=>{
 const r=await invoke('broken',repaired,broken);
 assert.equal(r.process.status,2);assert.equal(r.result.status,'UNKNOWN');
 assert.equal(r.result.head.complete,false);assert.equal(r.result.head.mismatches.length,0);
});
test('Lean launcher selection preserves argv0 before identifying the actual toolchain',{skip:!lean},async()=>{
 const launcher=join(root,'toolchain-launcher'),link=join(root,'lean');
 await writeFile(launcher,'#!/usr/bin/env python3\nimport os,sys\nfrom pathlib import Path\nif Path(sys.argv[0]).name != "lean":\n print("Toolchain launcher, not Lean")\n sys.exit(0)\nos.execv('+JSON.stringify(lean)+', ['+JSON.stringify(lean)+', *sys.argv[1:]])\n');
 await chmod(launcher,0o755);await symlink(launcher,link);
 const r=await invoke('launcher',repaired,repaired,['--lean',link]);
 assert.equal(r.process.status,0,r.process.stdout+r.process.stderr);
 assert.match(r.result.runtime.lean,/version 4\.35\.0/);
});
