import test from 'node:test';import assert from 'node:assert/strict';
import {buildCheck,admitPublication} from './presentation.mjs';
const sha='a'.repeat(40),r={context:{verifier_sha:sha,run_id:123},status:'UNKNOWN',stage:'native-initial',reason:'DEPENDENCY_SETUP_FAILED',subject:{repository:'metalogiclabs/gnss_lib_py',source_repository:'Stanford-NavLab/gnss_lib_py',pr:1,head_sha:'b'.repeat(40)}};
test('UNKNOWN presentation shows actual stage, source and cause',()=>{const c=buildCheck(r,{sha,runId:123});assert.match(c.output.summary,/DEPENDENCY_SETUP_FAILED/);assert.match(c.output.summary,/native-initial/);assert.match(c.output.summary,/Stanford-NavLab/);assert.doesNotMatch(c.output.summary,/No eligible source was investigated/);assert.equal(c.conclusion,'neutral');});
test('stale report cannot publish',()=>assert.throws(()=>buildCheck(r,{sha:'c'.repeat(40),runId:123})));
test('GitHub Actions cannot impersonate registered MathGraph App',()=>assert.throws(()=>admitPublication({head_sha:sha,conclusion:'neutral',name:'MathGraph Check / generic Python investigation',app:{id:15368,slug:'github-actions'}},sha)));
test('actual registered App response is accepted',()=>assert.equal(admitPublication({head_sha:sha,conclusion:'neutral',name:'MathGraph Check / generic Python investigation',app:{id:5308912,slug:'mathgraph-check'}},sha),true));
test('published advisory distinguishes shared failures from head-only defects',()=>{
 const p={...r,probes:[{id:'shared_case',base:{execution:'CANDIDATE_FAILURE_REPRODUCED'},head:{execution:'CANDIDATE_FAILURE_REPRODUCED'},delta:{status:'SHARED_FAILURE'}}]};
 const c=buildCheck(p,{sha,runId:123});
 assert.match(c.output.summary,/SHARED_FAILURE/);
 assert.match(c.output.summary,/not a proof of PR causality/i);
});
