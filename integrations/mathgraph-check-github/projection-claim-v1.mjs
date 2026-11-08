/**
 * Pure Check adapter for a independently qualified finite projection witness.
 * A protected verdict may not be inferred from a lossy downstream observation
 * when two admitted source states have the same observation but opposite
 * independently bound verdicts. Positive finite search remains UNKNOWN.
 *
 * The `authority` argument belongs to the trusted host, never the checked PR
 * or model. This module does not fetch or verify the underlying proof bytes.
 */
import {createHash} from 'node:crypto';
import {checkFiniteWarrantQuotient,hashFiniteUniverse} from './finite-warrant-quotient-v1.mjs';

export const PROJECTION_SCHEMA='mathgraph.projection-claim.v1';
const SHA40=/^[a-f0-9]{40}$/;
const ID=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
 (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const exact=(x,ks)=>object(x)&&Object.keys(x).length===ks.length&&
 ks.every(k=>Object.hasOwn(x,k));
const canonical=x=>Array.isArray(x)?x.map(canonical):object(x)?
 Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;

/** A contract digest ties the meaning of the protected verdict to its rows. */
export function digestProjectionClaim(subject,claim){
 return createHash('sha256').update(JSON.stringify(canonical({subject,claim}))).digest('hex');
}

const unknown=(reason,subject=null,id=null)=>({schema:PROJECTION_SCHEMA,status:'UNKNOWN',
 reason,subject,permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
 universal_sufficiency:'NOT_ESTABLISHED',terminal_form:null,
 results:id?[{id,status:'UNKNOWN',reason}]:[],claim_dependencies:[],evidence:[],
 checked_scope:'NONE',witness:null});

/**
 * `subject` is from independently read GitHub PR metadata. `claim` is a
 * proposed statement, not a source of trust. `authority` must bind both the
 * reviewed claim contract and exact finite universe out-of-band.
 */
export function checkProjectionClaim(subject,claim,authority={}){
 if(!exact(subject,['repository','pr','base_sha','head_sha'])||
   !REPO.test(subject.repository)||!Number.isSafeInteger(subject.pr)||subject.pr<1||
   !SHA40.test(subject.base_sha)||!SHA40.test(subject.head_sha)||
   !exact(claim,['id','statement','observation','universe'])||
   typeof claim.id!=='string'||!ID.test(claim.id)||
   typeof claim.statement!=='string'||!claim.statement.trim()||claim.statement.length>1000||
   typeof claim.observation!=='string'||!claim.observation.trim()||
   claim.observation.length>256||!object(claim.universe))
   return unknown('INVALID_PROJECTION_CLAIM');
 let digest;
 try{digest=digestProjectionClaim(subject,claim);}catch{return unknown('INVALID_PROJECTION_CONTRACT',subject,claim.id);}
 if(!object(authority)||!Array.isArray(authority.allowedRepositories)||
   !authority.allowedRepositories.includes(subject.repository)||
   authority.expectedHeadSha!==subject.head_sha||
   authority.expectedContractSha256!==digest)
   return unknown('INDEPENDENT_CONTRACT_AND_SOURCE_ADMISSION_REQUIRED',subject,claim.id);
 if(!Array.isArray(claim.universe.rows)||
   claim.universe.rows.some(r=>!object(r)||r.source_sha!==subject.head_sha))
   return unknown('WITNESS_NOT_BOUND_TO_CURRENT_PR_HEAD',subject,claim.id);
 const finite=checkFiniteWarrantQuotient(claim.universe,authority);
 if(finite.status!=='FINITE_COUNTEREXAMPLE'||
   finite.target_decidability!=='TARGET_NOT_DECIDABLE_FROM_PROJECTION')
   return unknown('NO_QUALIFIED_OPPOSITE_VERDICTS',subject,claim.id);

 // UNKNOWN vs OBSERVED is only a warrant-status distinction; it is not a
 // semantic opposite-verdict pair. Preserve the stronger qualified pair even
 // if an earlier UNKNOWN or provenance mismatch was encountered first.
 const grouped=new Map();let pair=null;
 for(const row of [...claim.universe.rows].sort((a,b)=>a.id.localeCompare(b.id))){
   let group=grouped.get(row.alpha_key);
   if(!group){group={};grouped.set(row.alpha_key,group);}
   if(row.protected_status==='OBSERVED'&&!group.observed)group.observed=row;
   if(row.protected_status==='BLOCKED'&&!group.blocked)group.blocked=row;
 }
 for(const [alpha_key,g] of grouped){
   if(g.observed&&g.blocked){pair={alpha_key,left:g.observed,right:g.blocked};break;}
 }
 if(!pair)return unknown('NO_QUALIFIED_OPPOSITE_VERDICTS',subject,claim.id);

 const evidenceId='projection:'+hashFiniteUniverse(claim.universe);
 const result={id:claim.id,status:'BLOCKED',reason:'PROTECTED_VERDICT_NOT_DECIDABLE_FROM_OBSERVATION',
   statement:claim.statement,observation:claim.observation,
   terminal_form:'NAMED_OBSTRUCTION',witness:pair};
 return {schema:PROJECTION_SCHEMA,status:'BLOCKED',
   reason:'QUALIFIED_SOURCE_BOUND_PROJECTION_OBSTRUCTION',subject,
   permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
   universal_sufficiency:'NOT_ESTABLISHED',terminal_form:'NAMED_OBSTRUCTION',
   checked_scope:'AUTHENTICATED_FINITE_PAIR_ONLY',witness:pair,
   contract_sha256:digest,universe_sha256:finite.universe_sha256,
   results:[result],claim_dependencies:[{id:claim.id,requires:[evidenceId]}],
   evidence:[{id:evidenceId,source_sha:subject.head_sha,
     universe_sha256:finite.universe_sha256,status:'ADMITTED_FINITE_WITNESS'}]};
}
