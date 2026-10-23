// Bounded evidence-lifecycle engine. Each receipt must have been independently
// authenticated by the host. No report or event can self-attest its authority.
const SHA=/^[0-9a-f]{40}$/;
export function replayLifecycle({source,claims,events,authenticatedReceipts=[]}={}){
 const reject=reason=>({state:"UNKNOWN",reason,permission:"ADVISORY_ONLY",history:[]});
 if(!source||!SHA.test(source.sha??"")||typeof source.repository!=="string"||
    !Array.isArray(claims)||!claims.length||!Array.isArray(events))return reject("INVALID_SOURCE_OR_EVENTS");
 const known=new Set(authenticatedReceipts);
 const states=new Map();
 for(const c of claims){
  if(!c?.id||!Array.isArray(c.requires)||!c.requires.length||
     states.has(c.id))return reject("BAD_CLAIM_DEPENDENCIES");
  states.set(c.id,{status:"UNKNOWN",requires:[...c.requires]});
 }
 const receipts=new Map(),history=[];
 for(const event of events){
  if(!event||!["WITHDRAW","OBSERVE"].includes(event.type)||!event.id||
     !event.receipt_id||!known.has(event.receipt_id))return reject("UNAUTHENTICATED_TRANSITION");
  if(event.source_sha!==source.sha)return reject("WRONG_HEAD_TRANSITION");
  const prior=receipts.get(event.id);
  if(prior&&(!Number.isSafeInteger(event.generation)||event.generation<=prior.generation))
   return reject("NON_MONOTONIC_EVIDENCE_GENERATION");
  if(!Number.isSafeInteger(event.generation)||event.generation<1)return reject("INVALID_GENERATION");
  if(event.type==="OBSERVE"&&!["success","failure","pending"].includes(event.conclusion))
   return reject("INVALID_CONCLUSION");
  receipts.set(event.id,{generation:event.generation,
   conclusion:event.type==="WITHDRAW"?"withdrawn":event.conclusion});
  const frame={event:event.type,evidence_id:event.id,generation:event.generation,claims:[]};
  for(const [id,c] of states){
   let status="OBSERVED";
   for(const dep of c.requires){
    const v=receipts.get(dep)?.conclusion;
    if(v==="failure"){status="BLOCKED";break;}
    if(v!=="success")status=status==="BLOCKED"?"BLOCKED":"UNKNOWN";
   }
   c.status=status;frame.claims.push({id,status});
  }
  history.push(frame);
 }
 return {state:[...states.values()].some(s=>s.status==="BLOCKED")?"BLOCKED":
   [...states.values()].some(s=>s.status==="UNKNOWN")?"UNKNOWN":"OBSERVED",
   permission:"ADVISORY_ONLY",source,history,claims:[...states].map(([id,v])=>({id,status:v.status}))};
}
