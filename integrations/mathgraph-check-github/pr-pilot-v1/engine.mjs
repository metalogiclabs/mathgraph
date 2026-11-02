import {activeSource,guardBlocks} from '../lean-investigator-v1/contracts.mjs';
import {profileFor} from './policy.mjs';
export function modelSnapshot(s){const {base_source,base_cli_source,cli_source,...packet}=s;return packet;}
export function validatePilotSnapshot(s){
 const p=profileFor(s.repository);for(const [k,v]of Object.entries(p))if(s[k]!==v)throw Error('UNTRUSTED_PILOT_PROFILE');
 if(!['check','fix'].includes(s.command)||!Number.isSafeInteger(s.number)||s.number<1||!/^[a-f0-9]{40}$/.test(s.head_sha??'')||!/^[a-f0-9]{40}$/.test(s.base_sha??'')||s.cli_source!==s.base_cli_source)throw Error('INVALID_PILOT_SOURCE');admitPilotSources(s.base_source,s.source);return s;
}
export function compareProbeRows(base,head,{complete=true}={}){if(!complete)base=[];return head.map(h=>{const b=base.find(b=>b.id===h.id),ok='GUARD_PASSED',fail='CANDIDATE_ASSERTION_FAILURE';return {id:h.id,base:b?.execution??'UNKNOWN',head:h.execution,change:!b||![ok,fail].includes(b.execution)?'BASE_UNKNOWN':b.execution===ok&&h.execution===fail?'NEW_FAILURE':b.execution===fail&&h.execution===fail?'PRE_EXISTING_FAILURE':b.execution===fail&&h.execution===ok?'RESOLVED_FAILURE':h.execution===ok?'BOTH_PASS':'HEAD_UNKNOWN'};});}

export function admitPilotSources(base,head){
 for(const source of [base,head]){
  const {code,interpolations}=activeSource(source);
  const forbidden=/\b(?:IO|System|Lean|unsafe\w*|sorry\w*|admit\w*|axiom|opaque|theorem|lemma|import|elab\w*|macro\w*|syntax|initialize|builtin_initialize|run_cmd|set_option|attribute|extern|implemented_by)\b/;
  if(forbidden.test(code)||interpolations.some(x=>forbidden.test(x))||/[«»]/.test(code)||/#(?!guard\b|\[)/.test(code))throw Error('UNSUPPORTED_LEAN_SOURCE_CAPABILITY');
 }
 const old=guardBlocks(base),after=guardBlocks(head);
 for(const g of old)if(after.filter(x=>x===g).length<old.filter(x=>x===g).length)throw Error('BASE_GUARD_REMOVED_OR_CHANGED');
 return true;
}
