import test from 'node:test';
import assert from 'node:assert/strict';
import {checkFiniteWarrantQuotient,hashFiniteUniverse} from
  '../../integrations/mathgraph-check-github/finite-warrant-quotient-v1.mjs';
import {l4CommentObservationCase,auditL4CommentObservation,
  previewL4AdvisoryCheck,L4_PROOF_RECEIPT_ID,L4_PROOF_ARTIFACT_SHA256,
  L4_PRODUCTION_SHA} from './case.mjs';

// The independently supplied admission policy is simulated in tests only.
// A real host must authenticate the Lean receipt, repository SHA and table
// digest through channels outside the analyzed submission.
function qualified(){
 const c=l4CommentObservationCase();
 return {expectedUniverseSha256:hashFiniteUniverse(c.universe),
   allowedSourceShas:[L4_PRODUCTION_SHA],
   qualifiedLeanProofReceiptIds:[L4_PROOF_RECEIPT_ID],
   qualifiedArtifactDigests:[L4_PROOF_ARTIFACT_SHA256]};
}

test('frozen L4 runtime success cannot distinguish a legal comment from raw SOH',()=>{
 const c=l4CommentObservationCase(),r=auditL4CommentObservation(qualified());
 assert.equal(c.protected_requirement,'NoRawSOH (necessary normative character restriction)');
 assert.equal(c.observation,'TokenParser.parseYaml success');
 assert.equal(c.universe.rows[0].alpha_key,c.universe.rows[1].alpha_key);
 assert.notEqual(c.universe.rows[0].protected_status,c.universe.rows[1].protected_status);
 assert.equal(r.status,'FINITE_COUNTEREXAMPLE');
 assert.equal(r.terminal_form,'NAMED_OBSTRUCTION');
 assert.equal(r.target_decidability,'TARGET_NOT_DECIDABLE_FROM_PROJECTION');
 assert.equal(r.frozen_parser_normative_iff,'REJECTED');
 assert.equal(r.complete_yaml_grammar,'UNKNOWN');
 assert.equal(r.universal_preservation,'NOT_ESTABLISHED');
});

test('an in-band case manifest does not qualify its own proof or universe',()=>{
 const c=l4CommentObservationCase();
 assert.equal(auditL4CommentObservation({}).status,'UNKNOWN');
 const policy=qualified();delete policy.qualifiedLeanProofReceiptIds;
 assert.equal(auditL4CommentObservation(policy).status,'UNKNOWN');
 const noArtifact=qualified();delete noArtifact.qualifiedArtifactDigests;
 assert.equal(auditL4CommentObservation(noArtifact).status,'UNKNOWN');
 assert.equal(checkFiniteWarrantQuotient(c.universe).status,'UNKNOWN');
});

test('source change and changed source-observation rows revoke admission',()=>{
 const policy=qualified();policy.allowedSourceShas=['f'.repeat(40)];
 assert.equal(auditL4CommentObservation(policy).status,'UNKNOWN');
 const c=l4CommentObservationCase(),trusted=qualified();
 c.universe.rows[1].protected_status='OBSERVED';
 assert.equal(checkFiniteWarrantQuotient(c.universe,trusted).status,'UNKNOWN');
});

test('a same-observation positive finite pair is not a full correctness proof',()=>{
 const c=l4CommentObservationCase();
 c.universe.rows[1]={...c.universe.rows[1],alpha_key:'parser:rejected',protected_status:'BLOCKED'};
 const authority={expectedUniverseSha256:hashFiniteUniverse(c.universe),
   allowedSourceShas:[L4_PRODUCTION_SHA]};
 const result=checkFiniteWarrantQuotient(c.universe,authority);
 assert.equal(result.status,'FINITE_PRESERVED');
 assert.equal(result.target_decidability,'NOT_REFUTED_BY_FINITE_ROWS');
 assert.equal(result.universal_preservation,'NOT_ESTABLISHED');
});

test('existing MathGraph Check advisory publisher can preview the qualified no-go only',()=>{
 const result=auditL4CommentObservation(qualified());
 const preview=previewL4AdvisoryCheck(result,L4_PRODUCTION_SHA);
 assert.equal(preview.head_sha,L4_PRODUCTION_SHA);
 assert.equal(preview.conclusion,'neutral');
 assert.equal(preview.status,'completed');
 assert.match(preview.output.summary,/NoRawSOH/);
 assert.match(preview.output.summary,/UNKNOWN.*complete YAML grammar/i);
 assert.match(preview.output.summary,/not replayed/i);
 assert.doesNotMatch(preview.output.title,/verified|complete|proven/i);
 assert.throws(()=>previewL4AdvisoryCheck(result,'f'.repeat(40)),/UNBOUND_SOURCE/);
 assert.throws(()=>previewL4AdvisoryCheck(auditL4CommentObservation({}),L4_PRODUCTION_SHA),/UNQUALIFIED/);
});
