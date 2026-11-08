import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {admitSignedProjectionReview,projectionReviewBytes} from './signed-projection-review-v1.mjs';

const head='a'.repeat(40),base='b'.repeat(40);
const artifact='c'.repeat(64);
const keys=generateKeyPairSync('ed25519');
const otherKeys=generateKeyPairSync('ed25519');
const reviewerKeys={'independent-reviewer-v1':keys.publicKey.export({type:'spki',format:'pem'})};
function fixture(){
 const subject={repository:'metalogiclabs/L4YAML',pr:32,base_sha:base,head_sha:head};
 const payload={schema:'mathgraph.projection.review.v1',subject,
  claim:{id:'no-raw-soh',statement:'Parser must exclude raw U+0001 comments',
   observation:'parseYaml success',universe:{schema:'mathgraph.finite-warrant-quotient.v1',
    scope:'reviewed-two-input-pair',rows:[
     {id:'legal',source_sha:head,alpha_key:'parseYaml=success',protected_status:'OBSERVED'},
     {id:'illegal',source_sha:head,alpha_key:'parseYaml=success',protected_status:'BLOCKED'},
    ]}},
  evidence:{receipt_ref:'github-actions:42420433923/job/128547467405',
    artifact_sha256:artifact}};
 return {subject,payload};
}
function signed(payload,privateKey=keys.privateKey,key_id='independent-reviewer-v1'){
 const review={key_id,payload};
 return {...review,signature_b64:sign(null,projectionReviewBytes(review),privateKey).toString('base64')};
}
test('independent reviewer signature admits a bounded source-bound obstruction',()=>{
 const {subject,payload}=fixture();
 const r=admitSignedProjectionReview(subject,signed(payload),reviewerKeys);
 assert.equal(r.status,'BLOCKED');
 assert.equal(r.terminal_form,'NAMED_OBSTRUCTION');
 assert.equal(r.review.key_id,'independent-reviewer-v1');
 assert.equal(r.review.artifact_sha256,artifact);
 assert.equal(r.review.proof_replay,'NOT_PERFORMED');
 assert.equal(r.universal_sufficiency,'NOT_ESTABLISHED');
});
test('review signature covers requirement, verdict rows and receipt digest',()=>{
 const {subject,payload}=fixture();
 for(const mutate of [
  x=>{x.claim.statement='Claim changed';},
  x=>{x.claim.universe.rows[1].protected_status='OBSERVED';},
  x=>{x.evidence.artifact_sha256='d'.repeat(64);},
 ]){
  const envelope=signed(structuredClone(payload));mutate(envelope.payload);
  assert.equal(admitSignedProjectionReview(subject,envelope,reviewerKeys).status,'UNKNOWN');
 }
});
test('same signed packet does not apply to a changed authenticated PR head',()=>{
 const {subject,payload}=fixture(),envelope=signed(payload);
 assert.equal(admitSignedProjectionReview({...subject,head_sha:'d'.repeat(40)},envelope,reviewerKeys).status,'UNKNOWN');
});
test('unknown issuer, in-band key, wrong signer and malformed signature fail closed',()=>{
 const {subject,payload}=fixture();
 assert.equal(admitSignedProjectionReview(subject,signed(payload),{}).status,'UNKNOWN');
 const inband={...signed(payload),public_key:keys.publicKey.export({type:'spki',format:'pem'})};
 assert.equal(admitSignedProjectionReview(subject,inband,{}).status,'UNKNOWN');
 assert.equal(admitSignedProjectionReview(subject,signed(payload,otherKeys.privateKey),reviewerKeys).status,'UNKNOWN');
 assert.equal(admitSignedProjectionReview(subject,{...signed(payload),signature_b64:'AAAA'},reviewerKeys).status,'UNKNOWN');
 assert.equal(admitSignedProjectionReview(null,null,null).status,'UNKNOWN');
});
test('empty evidence or a signed no-collision never yields a universal guarantee',()=>{
 const {subject,payload}=fixture();
 payload.evidence.receipt_ref='';
 assert.equal(admitSignedProjectionReview(subject,signed(payload),reviewerKeys).status,'UNKNOWN');
 payload.evidence.receipt_ref='github-actions:42420433923/job/128547467405';
 payload.claim.universe.rows[1].alpha_key='parseYaml=failure';
 const r=admitSignedProjectionReview(subject,signed(payload),reviewerKeys);
 assert.equal(r.status,'UNKNOWN');
 assert.equal(r.universal_sufficiency,'NOT_ESTABLISHED');
});
