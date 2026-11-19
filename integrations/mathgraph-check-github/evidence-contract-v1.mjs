// Pure, advisory MathGraph Check evidence adapter. No writes or code execution.
// The upstream caller MUST authenticate receipts; a boolean supplied in JSON is never trusted.
import {createHash} from "node:crypto";
const SHA=/^[a-f0-9]{40}$/;
const goodSHA=x=>typeof x==="string"&&SHA.test(x);
const normalized=x=>Array.isArray(x)?x.map(normalized):x&&typeof x==="object"?Object.fromEntries(Object.keys(x).sort().map(k=>[k,normalized(x[k])])):x;
export function inspectEvidence(input,{allowedRepositories=[],authenticatedEvidenceIds=[]}={}){
 const fail=reason=>({status:"UNKNOWN",reason,permission:"ADVISORY_ONLY"});
 const s=input?.subject,c=input?.carrier,es=input?.evidence,cs=input?.claims;
 if(!s||!goodSHA(s.base_sha)||!goodSHA(s.head_sha)||!Number.isSafeInteger(s.pr)||s.pr<1)return fail("INVALID_SUBJECT");
 if(!allowedRepositories.includes(s.repository))return fail("SUBJECT_NOT_ALLOWED");
 if(!c||!goodSHA(c.head_sha)||typeof c.repository!=="string")return fail("INVALID_CARRIER");
 if(!Array.isArray(es)||!Array.isArray(cs)||cs.length===0)return fail("NO_EVIDENCE_CONTRACT");
 const allowed=new Set(authenticatedEvidenceIds);
 const ids=new Set();
 for(const e of es){
   if(!e||typeof e.id!=="string"||ids.has(e.id))return fail("DUPLICATE_EVIDENCE");
   ids.add(e.id);
   if(e.subject_sha!==s.head_sha||!goodSHA(e.verifier_sha))return fail("EVIDENCE_SOURCE_MISMATCH");
   if(!allowed.has(e.id))return fail("EVIDENCE_UNAUTHENTICATED");
 }
 const results=cs.map(claim=>{
   if(!claim||!Array.isArray(claim.requires)||!claim.requires.length||typeof claim.id!=="string")return {id:claim?.id??"invalid",status:"UNKNOWN",reason:"INVALID_CLAIM"};
   const required=claim.requires.map(id=>es.find(e=>e.id===id));
   if(required.some(x=>!x))return {id:claim.id,status:"UNKNOWN",reason:"MISSING_SUPPORT"};
   if(required.some(x=>x.conclusion==="failure"))return {id:claim.id,status:"BLOCKED",reason:"REPORTED_REQUIRED_CHECK_FAILURE"};
   if(required.some(x=>x.conclusion!=="success"))return {id:claim.id,status:"UNKNOWN",reason:"NON_SUCCESS"};
   return {id:claim.id,status:"OBSERVED",reason:"CI_SUCCESS_NOT_SEMANTIC_WARRANT"};
 });
 return {status:results.some(x=>x.status==="BLOCKED")?"BLOCKED":results.some(x=>x.status==="UNKNOWN")?"UNKNOWN":"OBSERVED",permission:"ADVISORY_ONLY",subject:s,carrier:c,results,receipt_sha256:createHash("sha256").update(JSON.stringify(normalized(input))).digest("hex")};
}
