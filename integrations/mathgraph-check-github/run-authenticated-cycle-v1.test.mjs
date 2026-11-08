import test from 'node:test';
import assert from 'node:assert/strict';
import {makeLiveReadbackReport} from './run-authenticated-cycle-v1.mjs';

const source={repository:'metalogiclabs/mathgraph',pr:273,
 base_sha:'b'.repeat(40),head_sha:'a'.repeat(40)};
const snapshot=(status,conclusion)=>({
 input:{evidence:[{id:'github-check:1',name:'native',conclusion,check_run_id:1}]},
 result:{subject:source,status,results:[{id:'native',status}]},plans:[],
});

test('green native CI is observed while intended behavior remains unverified',()=>{
 const r=makeLiveReadbackReport(snapshot('OBSERVED','success'));
 assert.equal(r.status,'OBSERVED');
 assert.equal(r.scope,'GITHUB_CHECK_RUN_OBSERVATION_ONLY');
 assert.equal(r.requirement_assurance.status,'UNKNOWN');
 assert.equal(r.requirement_assurance.reason,'INTENDED_REQUIREMENT_NOT_ADMITTED_IN_THIS_RUN');
 assert.equal(r.requirement_assurance.source_to_claim,'NOT_ESTABLISHED');
 assert.equal(r.requirement_assurance.observation_sufficiency,'NOT_ESTABLISHED');
 assert.equal(r.requirement_assurance.terminal_form,null);
 assert.equal(r.requirement_assurance.next_action,'QUALIFY_REQUIREMENT_AND_SEPARATING_PROBES');
 assert.equal(r.evidence.length,1);
});

test('failed native CI is not automatically interpreted as a semantic requirement refutation',()=>{
 const r=makeLiveReadbackReport(snapshot('BLOCKED','failure'));
 assert.equal(r.status,'BLOCKED');
 assert.equal(r.requirement_assurance.status,'UNKNOWN');
 assert.equal(r.requirement_assurance.terminal_form,null);
 assert.equal(r.requirement_assurance.proof_replay,'NOT_PERFORMED');
});

test('missing readback cannot manufacture source or intent assurance',()=>{
 assert.throws(()=>makeLiveReadbackReport({}),/INVALID_AUTHENTICATED_SNAPSHOT/);
});
