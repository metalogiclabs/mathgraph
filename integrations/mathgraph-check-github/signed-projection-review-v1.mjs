/**
 * Independent reviewer admission for a finite projection obstruction.
 * The signed payload binds the proposed claim, immutable source revision and
 * review metadata; the trusted public key is supplied out of band.
 * Signature verification is NOT proof-byte replay or correctness of the
 * reviewer's substantive judgment.
 */
import {createPublicKey,verify} from 'node:crypto';
import {checkProjectionClaim,digestProjectionClaim} from './projection-claim-v1.mjs';
import {hashFiniteUniverse} from './finite-warrant-quotient-v1.mjs';
import {corroborateLeanProofArtifact} from './proof-artifact-corroboration-v1.mjs';

export const SIGNED_REVIEW_SCHEMA='mathgraph.projection.review.v1';
const SHA256=/^[a-f0-9]{64}$/;
const KEY_ID=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$/;
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
 (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const exact=(x,ks)=>object(x)&&Object.keys(x).length===ks.length&&
 ks.every(k=>Object.hasOwn(x,k));
const canonical=x=>Array.isArray(x)?x.map(canonical):object(x)?
 Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;
const unknown=reason=>({schema:SIGNED_REVIEW_SCHEMA,status:'UNKNOWN',reason,
 permission:'ADVISORY_ONLY',terminal_form:null,
 universal_sufficiency:'NOT_ESTABLISHED',proof_replay:'NOT_PERFORMED',review:null,
 checked_scope:'NONE',results:[],claim_dependencies:[],evidence:[]});

/** Stable signature bytes, including the reviewer key ID but not signature. */
export function projectionReviewBytes({key_id,payload}){
 return Buffer.from(JSON.stringify(canonical({key_id,payload})),'utf8');
}

/**
 * `subject` comes from an authenticated source readback. `trustedKeys` comes
 * from the trusted host, never from an input PR, envelope, or model proposal.
 */
export function admitSignedProjectionReview(subject,envelope,trustedKeys={}){
 try{
  if(!exact(envelope,['key_id','payload','signature_b64'])||
    typeof envelope.key_id!=='string'||!KEY_ID.test(envelope.key_id)||
    !exact(envelope.payload,['schema','subject','claim','evidence'])||
    envelope.payload.schema!==SIGNED_REVIEW_SCHEMA||
    !exact(envelope.payload.evidence,['receipt_ref','artifact_sha256'])||
    typeof envelope.payload.evidence.receipt_ref!=='string'||
    !envelope.payload.evidence.receipt_ref.trim()||
    envelope.payload.evidence.receipt_ref.length>400||
    !SHA256.test(envelope.payload.evidence.artifact_sha256)||
    !object(trustedKeys)||!Object.hasOwn(trustedKeys,envelope.key_id)||
    !object(subject)||!object(envelope.payload.subject)||
    JSON.stringify(canonical(subject))!==JSON.stringify(canonical(envelope.payload.subject)))
   return unknown('REVIEW_STRUCTURE_SOURCE_OR_TRUST_ROOT_MISSING');
  const signature=envelope.signature_b64;
  if(typeof signature!=='string'||signature.length>100||
    !/^[A-Za-z0-9+/]+={0,2}$/.test(signature))
   return unknown('REVIEW_SIGNATURE_INVALID');
  const bytes=Buffer.from(signature,'base64');
  if(bytes.length!==64||bytes.toString('base64')!==signature)
   return unknown('REVIEW_SIGNATURE_INVALID');
  const key=createPublicKey(trustedKeys[envelope.key_id]);
  if(key.asymmetricKeyType!=='ed25519')return unknown('REVIEW_KEY_INVALID');
  const signed=projectionReviewBytes(envelope);
  if(signed.length>262144)return unknown('REVIEW_PACKET_TOO_LARGE');
  if(!verify(null,signed,key,bytes))return unknown('REVIEW_SIGNATURE_NOT_VERIFIED');

  const claim=envelope.payload.claim;
  const result=checkProjectionClaim(subject,claim,{
   allowedRepositories:[subject.repository],expectedHeadSha:subject.head_sha,
   expectedContractSha256:digestProjectionClaim(subject,claim),
   expectedUniverseSha256:hashFiniteUniverse(claim.universe),
   allowedSourceShas:[subject.head_sha],
  });
  if(result.status!=='BLOCKED')return unknown('SIGNED_REVIEW_HAS_NO_QUALIFIED_OBSTRUCTION');
  return {...result,review:{key_id:envelope.key_id,
    receipt_ref:envelope.payload.evidence.receipt_ref,
    artifact_sha256:envelope.payload.evidence.artifact_sha256,
    scope:'SIGNED_REVIEW_OF_FINITE_PACKET',proof_replay:'NOT_PERFORMED'}};
 }catch{
  return unknown('REVIEW_ADMISSION_INCOMPLETE');
 }
}

/**
 * Stronger, opt-in admission. A signed packet alone is insufficient here:
 * the archived bytes and the review's exact evidence identity must also
 * match a separate protected receipt policy. This corroborates historical
 * CI logs, NOT a fresh Lean kernel proof replay or full requirement proof.
 */
export function admitCorroboratedSignedProjectionReview(subject,envelope,trustedKeys,{
 archivePath,trustedReceipt}={}){
 const reviewed=admitSignedProjectionReview(subject,envelope,trustedKeys);
 if(reviewed.status!=='BLOCKED')return reviewed;
 if(!object(trustedReceipt)||
   !exact(envelope?.payload?.evidence,['receipt_ref','artifact_sha256'])||
   !Number.isSafeInteger(trustedReceipt.run)||!Number.isSafeInteger(trustedReceipt.job)||
   envelope.payload.evidence.receipt_ref!==
     `${trustedReceipt.repository}@${trustedReceipt.commit}:run-${trustedReceipt.run}:job-${trustedReceipt.job}:${trustedReceipt.theorem}`||
   envelope.payload.evidence.artifact_sha256!==trustedReceipt.artifact_sha256)
  return unknown('REVIEWED_PROOF_RECEIPT_NOT_INDEPENDENTLY_PINNED');
 const proof=corroborateLeanProofArtifact(archivePath,trustedReceipt);
 if(proof.status!=='CORROBORATED')
  return unknown('REVIEWED_PROOF_ARTIFACT_NOT_CORROBORATED:'+proof.reason);
 return {...reviewed,review:{...reviewed.review,
   artifact_corroboration:'CORROBORATED',
   evidence_kind:proof.evidence_kind,proof_replay:'NOT_PERFORMED'}};
}
