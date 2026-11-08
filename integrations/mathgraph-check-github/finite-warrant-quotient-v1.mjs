/**
 * Finite warrant non-amplification checker.
 * ker(alpha)|U subseteq ker(Phi_protected)|U, where Phi includes source SHA.
 * This is an enumerated finite check, never a universal equivalence proof.
 */
import {createHash} from 'node:crypto';
const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const ID=/^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,79}$/;
const STATE=new Set(['OBSERVED','BLOCKED','UNKNOWN']);
const stable=x=>Array.isArray(x)?x.map(stable):
  x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,stable(x[k])])):x;
export const hashFiniteUniverse=x=>createHash('sha256').update(JSON.stringify(stable(x))).digest('hex');
const unknown=(reason,scope=null)=>({schema:'mathgraph.finite-warrant-quotient.v1',
  status:'UNKNOWN',reason,scope,permission:'ADVISORY_ONLY',universal_preservation:'NOT_ESTABLISHED',
  target_decidability:'UNKNOWN',source_traceability:'UNKNOWN',required_change:'QUALIFY_FINITE_UNIVERSE',
  checked_states:0,witness:null});
export function checkFiniteWarrantQuotient(universe,authority={}){
 if(!universe||universe.schema!=='mathgraph.finite-warrant-quotient.v1'||
    typeof universe.scope!=='string'||!ID.test(universe.scope)||!Array.isArray(universe.rows)||
    universe.rows.length<2||universe.rows.length>2048)
   return unknown('INVALID_OR_EMPTY_FINITE_SCOPE');
 if(!universe.rows.every(r=>r&&typeof r==='object'&&!Array.isArray(r)&&
    Object.keys(r).length===4&&['id','source_sha','alpha_key','protected_status'].every(k=>Object.hasOwn(r,k))&&
    typeof r.id==='string'&&ID.test(r.id)&&typeof r.source_sha==='string'&&
    SHA40.test(r.source_sha)&&typeof r.alpha_key==='string'&&
    r.alpha_key.length<=256&&STATE.has(r.protected_status))||
    new Set(universe.rows.map(r=>r.id)).size!==universe.rows.length)
   return unknown('INVALID_FINITE_ROWS',universe.scope);
 const digest=hashFiniteUniverse(universe);
 // This source table needs an externally authenticated immutable identity.
 if(!authority||typeof authority!=='object'||Array.isArray(authority)||
    authority.expectedUniverseSha256!==digest||
    !Array.isArray(authority.allowedSourceShas)||
    universe.rows.some(r=>!authority.allowedSourceShas.includes(r.source_sha))||
    !SHA256.test(digest))
   return unknown('INDEPENDENT_UNIVERSE_ADMISSION_REQUIRED',universe.scope);
 const groups=new Map();
 const sorted=[...universe.rows].sort((a,b)=>a.id.localeCompare(b.id));
 let compared=0;
 let targetWitness=null,sourceWitness=null;
 for(const row of sorted){
   const prior=groups.get(row.alpha_key);
   if(prior){
     compared++;
     // Do not return at the first provenance collision. A later row can
     // expose the stronger claim-verdict obstruction for the same alpha.
     if(prior.source_sha!==row.source_sha&&!sourceWitness)
       sourceWitness={alpha_key:row.alpha_key,left:prior,right:row};
     if(prior.protected_status!==row.protected_status&&!targetWitness)
       targetWitness={alpha_key:row.alpha_key,left:prior,right:row};
   }else groups.set(row.alpha_key,row);
 }
 if(targetWitness||sourceWitness){
   const statusDiffers=targetWitness!==null;
   const sourceDiffers=sourceWitness!==null;
   return {schema:'mathgraph.finite-warrant-quotient.v1',scope:universe.scope,
        status:'FINITE_COUNTEREXAMPLE',reason:'CONSEQUENTIAL_COLLISION',
        permission:'ADVISORY_ONLY',universal_preservation:'NOT_ESTABLISHED',
        // A single admitted collision rules out a decoder of this protected
        // field from alpha on any domain containing both rows. The statuses
        // are themselves only as sound as the independently admitted table:
        // this does not establish the truth of an unbounded domain claim.
        target_decidability:statusDiffers?'TARGET_NOT_DECIDABLE_FROM_PROJECTION':
          'NOT_REFUTED_BY_FINITE_ROWS',
        source_traceability:sourceDiffers?'SOURCE_NOT_RECOVERABLE_FROM_PROJECTION':
          'NOT_REFUTED_BY_FINITE_ROWS',
        required_change:statusDiffers?'REFINE_OBSERVATION_OR_RESTRICT_DOMAIN':
          'PRESERVE_SOURCE_IDENTITY',
        protected_fields:['source_sha','protected_status'],
        universe_sha256:digest,checked_states:sorted.length,compared_merges:compared,
        witness:targetWitness??sourceWitness,source_witness:sourceWitness};
 }
 return {schema:'mathgraph.finite-warrant-quotient.v1',scope:universe.scope,
   status:'FINITE_PRESERVED',reason:'NO_CONSEQUENTIAL_COLLISION_IN_ENUMERATED_UNIVERSE',
   permission:'ADVISORY_ONLY',universal_preservation:'NOT_ESTABLISHED',
   target_decidability:'NOT_REFUTED_BY_FINITE_ROWS',
   source_traceability:'NOT_REFUTED_BY_FINITE_ROWS',
   required_change:'NO_GLOBAL_CONCLUSION',
   protected_fields:['source_sha','protected_status'],universe_sha256:digest,
   checked_states:sorted.length,compared_merges:compared,witness:null};
}
