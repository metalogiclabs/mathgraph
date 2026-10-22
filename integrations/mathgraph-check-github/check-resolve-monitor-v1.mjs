// Product facade: CHECK -> RESOLVE -> MONITOR. Pure functions; no Github writes.
// Evidence authenticity must be established by a trusted, external verifier.
// The state of a changed source is UNKNOWN until exact-head evidence is supplied.
import {inspectEvidence} from "./evidence-contract-v1.mjs";
const IDENT=/^[a-f0-9]{40}$/;
const pairs=x=>Array.isArray(x)?x:[];
export function check(input,authority){
 return inspectEvidence(input,authority);
}
export function resolve(report,plans={}){
 const claims=pairs(report?.results);
 return claims.filter(c=>c.status!=="OBSERVED").map(c=>{
  const candidates=pairs(plans[c.id]).filter(p=>p&&
   typeof p.id==="string"&&Number.isFinite(p.cost)&&p.cost>=0&&
   p.allowed===true&&p.source_authoritative===true);
  candidates.sort((a,b)=>a.cost-b.cost||a.id.localeCompare(b.id));
  return {claim:c.id,status:c.status,next:candidates.length?
   {experiment:candidates[0].id,cost:candidates[0].cost,kind:"PROPOSAL_NOT_EXECUTED"}:
   null,reason:candidates.length?"LOWEST_RECORDED_PERMITTED_PLAN":"NO_QUALIFIED_PLAN"};
 });
}
export function monitor(previous,next,{changedEvidenceIds=[],changedSources=[]}={}){
 const fail=reason=>({status:"UNKNOWN",reason,transitions:[],permission:"ADVISORY_ONLY"});
 if(!previous||!next||!previous.subject||!next.subject)return fail("MISSING_SNAPSHOT");
 if(previous.subject.repository!==next.subject.repository||previous.subject.pr!==next.subject.pr)return fail("SUBJECT_CHANGED");
 if(!IDENT.test(next.subject.head_sha??""))return fail("INVALID_NEXT_SOURCE");
 const changed=new Set(changedEvidenceIds);
 const sources=new Set(changedSources);
 const before=new Map(pairs(previous.results).map(c=>[c.id,c]));
 const after=new Map(pairs(next.results).map(c=>[c.id,c]));
 const deps=new Map(pairs(next.claim_dependencies).map(c=>[c.id,new Set(pairs(c.requires))]));
 const all=[...new Set([...before.keys(),...after.keys()])].sort();
 const shaChanged=previous.subject.head_sha!==next.subject.head_sha;
 const transitions=all.map(id=>{
   const b=before.get(id)?.status??"UNKNOWN", n=after.get(id)?.status??"UNKNOWN";
   const req=deps.get(id);
   const missingScope=!req;
   const impacted=missingScope||shaChanged||sources.has(next.subject.repository)||
      [...(req??[])].some(x=>changed.has(x));
   // No dependency closure proof means no silent carried-over authority.
   const status=impacted&&n==="OBSERVED"&&!next.independent_requalification?
      "UNKNOWN":n;
   return {claim:id,from:b,to:status,changed:b!==status,
     reason:status!==n?"REQUALIFICATION_REQUIRED":missingScope?
     "DEPENDENCY_SCOPE_UNKNOWN":impacted?"RECHECKED_OR_WITHDRAWN":"UNCHANGED"};
 });
 return {status:transitions.some(t=>t.to==="BLOCKED")?"BLOCKED":
   transitions.some(t=>t.to==="UNKNOWN")?"UNKNOWN":"OBSERVED",
   permission:"ADVISORY_ONLY",transitions};
}
