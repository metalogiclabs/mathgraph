import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {capabilities,parseOperatorArgs,runOperator} from '../../bin/mathgraph-check.mjs';

test('operator must explicitly select supported scope and cannot narrow a numerical run',()=>{
 const common=['--repo','repo','--base','A','--head','B','--out','out'];
 assert.throws(()=>parseOperatorArgs(common),/SELECT_SUPPORTED_PROFILE/);
 assert.throws(()=>parseOperatorArgs(['--profile','invented',...common]),/SELECT_SUPPORTED_PROFILE/);
 assert.throws(()=>parseOperatorArgs(['--profile','telemetry-integer-identity-v1',...common,'--profiles','one']),/SUBPROFILE/);
 assert.throws(()=>parseOperatorArgs(['--profile','l4yaml-retained-v1',...common,'--profile','l4yaml-retained-v1']),/INVALID_PROFILE/);
 assert.equal(parseOperatorArgs(['--profile','l4yaml-retained-v1',...common]).options.profiles.length,5);
});

test('capabilities publish both scopes without broadening catalogue coverage',()=>{
 const c=capabilities();assert.equal(c.permission,'ADVISORY_ONLY');assert.equal(c.profiles.length,2);
 assert.equal(c.profiles[0].checks.length,5);assert.equal(c.profiles[1].cases,108);
 assert.match(c.profiles[0].boundary,/not 104 executable detectors/);
 assert.equal(c.operator_use,'NOT_RUN');
});

test('unavailable source remains UNKNOWN with preserved artifacts through the public entry',async()=>{
 const root=await mkdtemp(join(tmpdir(),'check-operator-'));
 try{
  const out=join(root,'run');
  const run=await runOperator(['--profile','telemetry-integer-identity-v1','--repo',join(root,'missing'),
   '--base','HEAD','--head','HEAD','--out',out]);
  assert.equal(run.exit_code,2);assert.equal(JSON.parse(run.text).status,'UNKNOWN');
  const r=JSON.parse(await readFile(join(out,'result.json'),'utf8'));
  assert.equal(r.base.complete,false);assert.equal(r.head.complete,false);
  assert.equal(r.permission,'ADVISORY_ONLY');assert.equal(r.release.profile,'telemetry-integer-identity-v1');
  assert.ok(r.release.entry_files['bin/mathgraph-check.mjs']);
  assert.match(await readFile(join(out,'report.md'),'utf8'),/LOCAL_REPOSITORY_UNAVAILABLE/);
  await assert.rejects(runOperator(['--profile','telemetry-integer-identity-v1','--repo',root,
   '--base','HEAD','--head','HEAD','--out',out]),/EEXIST/);
 }finally{await rm(root,{recursive:true,force:true});}
});
