// Advisory projection ONLY: input receipt must first be independently authenticated.
// Never treats this module as a verifier, native re-execution, or merge authority.
const BASE = Object.freeze({P1:"WARRANTED_BOUNDED",P2:"REJECTED_BOUNDED",P3:"UNKNOWN",
  Y1:"UNKNOWN",Y2:"REJECTED_BOUNDED",Y3:"UNKNOWN"});
const DEPS = Object.freeze({P1:["pkc-decl","pkc-verifier"],
 P2:["pkc-decl","pkc-annotation","pkc-verifier"],P3:["pkc-annotation"],
 Y1:["yaml-oracle"],Y2:["yaml-dump","yaml-oracle","yaml-verifier"],Y3:["yaml-source"]});
const PROTOCOL="9c8b427c679398fd80ea56d9a91a1627b2e96b6d";
const unknown=reason=>({title:"EVIDENCE_UNKNOWN",conclusion:"neutral",merge:"UNKNOWN",
 authorization:"NONE",summary:"UNKNOWN: "+reason});
export function advisory(receipt,{sourceHead,expectedHead,withdrawn=[]}={}) {
 if(!receipt || receipt.protocol_commit!==PROTOCOL) return unknown("protocol mismatch");
 if(!sourceHead || sourceHead!==expectedHead) return unknown("source head missing or stale");
 if(receipt.mode!=="authenticated archived native verifier replay + modeled dependency withdrawal" ||
    receipt.new_native_sources_executed!==false) return unknown("unrecognized evidence mode");
 if(!receipt.baseline || Object.keys(BASE).some(k=>receipt.baseline[k]!==BASE[k]) ||
    Object.keys(receipt.baseline).length!==Object.keys(BASE).length)
    return unknown("baseline mismatch");
 const allowed=new Set(Object.values(DEPS).flat());
 if(!Array.isArray(withdrawn)||withdrawn.some(x=>!allowed.has(x))) return unknown("invalid withdrawal");
 const verdicts=Object.fromEntries(Object.keys(BASE).map(k=>[k,
   DEPS[k].some(d=>withdrawn.includes(d))?"UNKNOWN_WITHDRAWN":BASE[k]]));
 return {title:"CROSS_DOMAIN_ADVISORY_BOUNDED",conclusion:"neutral",merge:"UNKNOWN",
  authorization:"NONE",verdicts,
  summary:["PKC/L4YAML are external research subjects, NOT carrier code defects.",
   "Historical native evidence + modeled dependency withdrawal; no native re-execution here.",
   ...Object.entries(verdicts).map(([k,v])=>k+": "+v),
   "Restoration requires independent native verifier replay. No merge authority."].join("\n")};
}
