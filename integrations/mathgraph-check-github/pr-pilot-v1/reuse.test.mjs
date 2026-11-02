import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {rebindFrozenPlan} from './reuse.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
const ctx={verifier_sha:'a'.repeat(40),run_id:2,attempt:1};const request={repository:'metalogiclabs/L4YAML',number:2,base_sha:'b'.repeat(40),head_sha:'c'.repeat(40),command:'fix'};
const plan={summary:'frozen',tests:[{id:'a',expression:'true',hypothesis:'boundary',contract:'documented'}]};
const prior={context:{...ctx,run_id:1},snapshot:{...request,command:'check',source:'original',source_sha256:hash('original')},plan,state:{state:'PROBES_PROPOSED',test_digest:hash(JSON.stringify(plan.tests))},assessment:{status:'CANDIDATE_ASSERTION_FAILURE'}};
test('fix reuses exact probes and original source without model regeneration',()=>{const r=rebindFrozenPlan(prior,request,ctx);assert.deepEqual(r.plan,plan);assert.equal(r.state.model_calls,0);assert.equal(r.snapshot.command,'fix');assert.equal(r.state.proposal_origin.run_id,1);});
test('changed source, different PR, failed check or same-run input cannot rebind',()=>{for(const p of [{...prior,snapshot:{...prior.snapshot,source:'changed'}},{...prior,snapshot:{...prior.snapshot,number:3}},{...prior,assessment:{status:'UNKNOWN'}},{...prior,context:ctx}])assert.throws(()=>rebindFrozenPlan(p,request,ctx));});
