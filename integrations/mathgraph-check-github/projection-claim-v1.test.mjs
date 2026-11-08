import test from 'node:test';
import assert from 'node:assert/strict';
import {hashFiniteUniverse} from './finite-warrant-quotient-v1.mjs';
import {checkProjectionClaim,digestProjectionClaim} from './projection-claim-v1.mjs';
import {l4CommentObservationCase,auditL4CommentObservation,L4_PRODUCTION_SHA,
 L4_PROOF_RECEIPT_ID,L4_PROOF_ARTIFACT_SHA256} from
 '../../experiments/check-l4-observation-ceiling-v1/case.mjs';

const a='a'.repeat(40),b='b'.repeat(40);
function fixture(rows=[
 {id:'compliant',source_sha:a,alpha_key:'CI=green',protected_status:'OBSERVED'},
 {id:'violating',source_sha:a,alpha_key:'CI=green',protected_status:'BLOCKED'},
]){
 const subject={repository:'metalogiclabs/mathgraph',pr:195,base_sha:b,head_sha:a};
 const claim={id:'no-raw-control',statement:'The raw input contains no U+0001',
   observation:'CI success bit',universe:{schema:'mathgraph.finite-warrant-quotient.v1',
     scope:'exact-head-character-contract',rows}};
 const authority={allowedRepositories:[subject.repository],expectedHeadSha:a,
   expectedContractSha256:digestProjectionClaim(subject,claim),
   expectedUniverseSha256:hashFiniteUniverse(claim.universe),allowedSourceShas:[a]};
 return {subject,claim,authority};
}

test('qualified opposite target verdicts are an advisory named obstruction',()=>{
 const x=fixture(),r=checkProjectionClaim(x.subject,x.claim,x.authority);
 assert.equal(r.status,'BLOCKED');
 assert.equal(r.terminal_form,'NAMED_OBSTRUCTION');
 assert.equal(r.results[0].status,'BLOCKED');
 assert.equal(r.results[0].id,'no-raw-control');
 assert.equal(r.results[0].witness.left.id,'compliant');
 assert.equal(r.results[0].witness.right.id,'violating');
 assert.equal(r.claim_dependencies[0].requires.length,1);
 assert.equal(r.permission,'ADVISORY_ONLY');
 assert.equal(r.intent_verification,'NOT_ESTABLISHED');
 assert.equal(r.universal_sufficiency,'NOT_ESTABLISHED');
});

test('missing host authority or self-authorized contract cannot promote',()=>{
 const x=fixture();
 assert.equal(checkProjectionClaim(x.subject,x.claim,{}).status,'UNKNOWN');
 const y=fixture();y.claim.statement='Ballot privacy is guaranteed';
 assert.equal(checkProjectionClaim(y.subject,y.claim,y.authority).status,'UNKNOWN');
});

test('changed source cannot carry the old same-observation witness',()=>{
 const x=fixture();x.subject.head_sha='c'.repeat(40);
 assert.equal(checkProjectionClaim(x.subject,x.claim,x.authority).status,'UNKNOWN');
 const y=fixture();y.claim.universe.rows[1].source_sha=b;
 y.authority.expectedContractSha256=digestProjectionClaim(y.subject,y.claim);
 y.authority.expectedUniverseSha256=hashFiniteUniverse(y.claim.universe);
 y.authority.allowedSourceShas.push(b);
 assert.equal(checkProjectionClaim(y.subject,y.claim,y.authority).status,'UNKNOWN');
});

test('provenance-only collision is not a semantic claim obstruction',()=>{
 const x=fixture([
  {id:'first',source_sha:a,alpha_key:'green',protected_status:'OBSERVED'},
  {id:'second',source_sha:a,alpha_key:'green',protected_status:'OBSERVED'},
 ]);
 const r=checkProjectionClaim(x.subject,x.claim,x.authority);
 assert.equal(r.status,'UNKNOWN');
 assert.equal(r.terminal_form,null);
});

test('finite non-collision is not a universal sufficiency theorem',()=>{
 const x=fixture([
  {id:'first',source_sha:a,alpha_key:'pass',protected_status:'OBSERVED'},
  {id:'second',source_sha:a,alpha_key:'fail',protected_status:'BLOCKED'},
 ]);
 const r=checkProjectionClaim(x.subject,x.claim,x.authority);
 assert.equal(r.status,'UNKNOWN');
 assert.equal(r.universal_sufficiency,'NOT_ESTABLISHED');
});

test('incomplete target verdicts and malformed schemas fail closed',()=>{
 const x=fixture([
  {id:'first',source_sha:a,alpha_key:'green',protected_status:'OBSERVED'},
  {id:'second',source_sha:a,alpha_key:'green',protected_status:'UNKNOWN'},
 ]);
 assert.equal(checkProjectionClaim(x.subject,x.claim,x.authority).status,'UNKNOWN');
 const y=fixture();y.claim.untrusted_verified=true;
 assert.equal(checkProjectionClaim(y.subject,y.claim,y.authority).status,'UNKNOWN');
 assert.equal(checkProjectionClaim(null,null,null).status,'UNKNOWN');
});

test('an UNKNOWN row cannot mask a later qualified opposite-verdict pair',()=>{
 const x=fixture([
  {id:'a-valid',source_sha:a,alpha_key:'green',protected_status:'OBSERVED'},
  {id:'b-incomplete',source_sha:a,alpha_key:'green',protected_status:'UNKNOWN'},
  {id:'c-invalid',source_sha:a,alpha_key:'green',protected_status:'BLOCKED'},
 ]);
 const r=checkProjectionClaim(x.subject,x.claim,x.authority);
 assert.equal(r.status,'BLOCKED');
 assert.deepEqual([r.results[0].witness.left.id,r.results[0].witness.right.id],['a-valid','c-invalid']);
});

test('historical qualified L4YAML case feeds the exact-source Check adapter only',()=>{
 const history=l4CommentObservationCase();
 const originalPolicy={expectedUniverseSha256:hashFiniteUniverse(history.universe),
   allowedSourceShas:[L4_PRODUCTION_SHA],
   qualifiedLeanProofReceiptIds:[L4_PROOF_RECEIPT_ID],
   qualifiedArtifactDigests:[L4_PROOF_ARTIFACT_SHA256]};
 assert.equal(auditL4CommentObservation(originalPolicy).status,'FINITE_COUNTEREXAMPLE');
 // Synthetic PR identity: no actual current PR or deployment is asserted.
 const subject={repository:'metalogiclabs/L4YAML',pr:999,
   base_sha:b,head_sha:L4_PRODUCTION_SHA};
 const claim={id:'L4-NORMATIVE-RUNTIME',
   statement:history.protected_requirement,
   observation:history.observation,universe:history.universe};
 const authority={...originalPolicy,allowedRepositories:[subject.repository],
   expectedHeadSha:subject.head_sha,
   expectedContractSha256:digestProjectionClaim(subject,claim)};
 const r=checkProjectionClaim(subject,claim,authority);
 assert.equal(r.status,'BLOCKED');
 assert.equal(r.results[0].witness.right.id,'raw-soh-comment');
 subject.head_sha='c'.repeat(40);
 assert.equal(checkProjectionClaim(subject,claim,authority).status,'UNKNOWN');
});
