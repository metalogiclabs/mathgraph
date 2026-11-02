import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {runGenericSemantEq} from './generic-semanteq-run-v1.mjs';
import {runGenericLeanConsumer} from './generic-lean-consumer-run-v1.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const source='import Init\ntheorem original (n : Nat) : n + 0 = n := by simp\n';
const candidateSource='import Init\ntheorem candidate (n : Nat) : n = n := by rfl\n';
const consumerSource='import Candidate\ntheorem MathGraphConsumer.original_claim (n : Nat) : n + 0 = n := by\n  exact candidate n\n';
const projectDir=process.env.MATHGRAPH_SEMANTEQ_PROJECT;

test('parallel consumer replay cannot taint SemantEq source cleanliness or provenance', {skip:!projectDir},async()=>{
 const common={reference:{path:'Original.lean',source},candidate:{path:'Candidate.lean',source:candidateSource},
  expectedReferenceSha:sha(source),projectDir,timeoutMs:60000};
 const [semantic,consumer]=await Promise.all([
  runGenericSemantEq(common),
  runGenericLeanConsumer({...common,consumerSource,expectedConsumerSha:sha(consumerSource),
   consumerName:'MathGraphConsumer.original_claim'})
 ]);
 assert.equal(semantic.execution_status,'EXECUTED');
 assert.equal(semantic.formal_statement_relation,'NATIVE_CERTIFIED_EQUIVALENT');
 assert.equal(semantic.tool_metadata.dirty,false);
 assert.equal(consumer.original_target_status,'NATIVE_CONSUMER_ACCEPTED');
 assert.equal(consumer.evidence_warrant,'UNKNOWN');
});
