// Statement-agnostic prospective proof experiment. No registered repair, gold
// proof or theorem-specific lemma is supplied to the proposing model.
import {createHash} from 'node:crypto';
const hash=x=>createHash('sha256').update(x).digest('hex');
const ensure=(ok,code)=>{if(!ok)throw Error(code);};
const allowedAxioms=new Set(['propext','Classical.choice','Quot.sound']);
export function freezeTheorem(source,provenance){
 ensure(typeof source==='string'&&source.length<=12000,'SOURCE_TEMPLATE_REFUSED');
 const declarations=[...source.matchAll(/^theorem ([A-Za-z][A-Za-z0-9_]*)\b/gm)];ensure(declarations.length===1,'SOURCE_TEMPLATE_REFUSED');
 const start=declarations[0].index,name=declarations[0][1],tail=source.slice(start),match=tail.match(/^([\s\S]*?) := by\s+sorry\s*$/);ensure(match,'SOURCE_TEMPLATE_REFUSED');
 const header=match[1],rest=header.slice(('theorem '+name).length).trim();let depth=0,split=-1;
 for(let i=0;i<rest.length;i++){const c=rest[i];if('([{'.includes(c))depth++;else if(')]}'.includes(c))depth--;else if(c===':'&&depth===0){split=i;break;}ensure(depth>=0,'SOURCE_TEMPLATE_REFUSED');}
 ensure(split>=0,'SOURCE_TEMPLATE_REFUSED');const binders=rest.slice(0,split).trim(),goal=rest.slice(split+1).trim();ensure(goal&&!/[#;]/.test(header),'SOURCE_TEMPLATE_REFUSED');
 const context=source.slice(0,start).replace(/\/-[\s\S]*?-\//g,'').replace(/--[^\n]*/g,'').split('\n').map(l=>l.trim()).filter(Boolean);
 ensure(context[0]==='import Mathlib'&&context.every(l=>l==='import Mathlib'||/^open (?:scoped )?[A-Za-z0-9_. ]+$/.test(l)),'SOURCE_CONTEXT_REFUSED');
 const prelude=context.join('\n')+'\n\n';
 return {schema:'mathgraph.frozen-formal-target.v1',name,source,header,prelude,target_type:binders?'∀ '+binders+', '+goal:goal,source_sha256:hash(source),target_sha256:hash(header),provenance:structuredClone(provenance??{}),registered_repair:false,informal_equivalence:'NOT_CERTIFIED'};
}
export function renderCandidate(frozen,proof){
 ensure(typeof proof==='string'&&proof.length<=12000&&/^by(?:\s|$)/.test(proof),'UNSUPPORTED_PROOF_BODY');
 ensure(!/[#`"«»\r]/.test(proof)&&!(/\b(?:sorry|sorryAx|admit|axiom|unsafe|unsafeCast|set_option|run_tac|run_elab|run_meta|elab|macro|syntax|initialize|builtin_initialize|attribute|declare_syntax_cat|notation|infix|prefix|postfix|instance|class|structure|abbrev|export|local|scoped|command_elab|elab_rules|macro_rules|variable|universe|open|mutual|partial|noncomputable|theorem|example|def|opaque|import|namespace|section|end|IO|System|native_decide|ofReduceBool|ofReduceNat)\b/.test(proof)),'UNSUPPORTED_PROOF_BODY');
 return frozen.prelude+frozen.header+' := '+proof.trim()+'\n';
}
export function originalConsumer(frozen){return 'import Candidate\n\n'+frozen.prelude.replace(/^import Mathlib\n\n/,'')+'example : '+frozen.target_type+' := @'+frozen.name+'\n#print axioms '+frozen.name+'\n';}
export function auditFresh(output,name){
 const escaped=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const match=output.match(new RegExp("^'"+escaped+"' (?:does not depend on any axioms|depends on axioms: \\[([^\\]]*)\\])\\s*$",'m'));
 if(!match)return null;const axioms=match[1]?match[1].split(',').map(x=>x.trim()):[];return axioms.every(x=>allowedAxioms.has(x))&&new Set(axioms).size===axioms.length?axioms:null;
}
export async function verifyFresh({frozen,proof,run}){
 let candidate;try{candidate=renderCandidate(frozen,proof);}catch(e){return {status:'UNKNOWN',diagnostic:e.message,axioms:null};}
 let compiled;try{compiled=await run('Candidate',candidate);}catch(e){if(e.message==='NATIVE_CLEANUP_UNCONFIRMED')throw e;return {status:'UNKNOWN',diagnostic:'NATIVE_RESOURCE_LIMIT_OR_EXECUTION_INCOMPLETE',axioms:null};}if(compiled.code!==0)return {status:'UNKNOWN',diagnostic:compiled.output.slice(-8000),axioms:null};
 let consumer;try{consumer=await run('Consumer',originalConsumer(frozen));}catch(e){if(e.message==='NATIVE_CLEANUP_UNCONFIRMED')throw e;return {status:'UNKNOWN',diagnostic:'NATIVE_RESOURCE_LIMIT_OR_EXECUTION_INCOMPLETE',axioms:null};}const axioms=auditFresh(consumer.output,frozen.name);
 return {status:consumer.code===0&&axioms!==null?'ORIGINAL_TARGET_VERIFIED':'UNKNOWN',diagnostic:consumer.output.slice(-8000),axioms,source_sha256:hash(candidate),target_sha256:frozen.target_sha256};
}
export async function runFreshComparison({frozen,generate,verify,onProposal=async()=>{}}){
 let calls=0;const proposals=[];
 const propose=async context=>{ensure(calls<3,'EXPERIMENT_CALL_CAP');calls++;const p=await generate({frozen_target:frozen.header,prelude:frozen.prelude,...context});ensure(typeof p.proof_body==='string'&&p.usage&&Number.isSafeInteger(p.usage.input_tokens)&&p.usage.input_tokens>=0&&p.usage.input_tokens<=24000&&Number.isSafeInteger(p.usage.output_tokens)&&p.usage.output_tokens>=0&&p.usage.output_tokens<=4096,'MODEL_USAGE_INVALID');proposals.push({arm:context.arm,...p});await onProposal(proposals);return p.proof_body;};
 const firstProof=await propose({arm:'shared-first'}),first=await verify(firstProof);
 if(first.status==='ORIGINAL_TARGET_VERIFIED')return {schema:'mathgraph.fresh-proof-comparison.v1',comparison:'SHARED_FIRST_CANDIDATE_PASSED_NO_ADVANTAGE_SHOWN',registered_repair_used:false,unique_api_calls:calls,llm_alone:first,mathgraph:first,proposals};
 const baselineProof=await propose({arm:'llm-alone-revision',previous_proof:firstProof,instructions:'Reconsider your proof without compiler feedback. Preserve the exact theorem statement.'});
 const baseline=await verify(baselineProof);
 const guidedProof=await propose({arm:'native-feedback-revision',previous_proof:firstProof,native_feedback:first.diagnostic??'Native acceptance was not established.',instructions:'Repair the proof using this native diagnostic. Preserve the exact theorem statement.'});
 const guided=await verify(guidedProof);
 return {schema:'mathgraph.fresh-proof-comparison.v1',comparison:guided.status==='ORIGINAL_TARGET_VERIFIED'&&baseline.status!=='ORIGINAL_TARGET_VERIFIED'?'NATIVE_FEEDBACK_ADVANTAGE_ON_ONE_FIXED_CASE':'NO_NATIVE_FEEDBACK_ADVANTAGE_SHOWN',registered_repair_used:false,unique_api_calls:calls,shared_first:first,llm_alone:baseline,mathgraph:guided,proposals};
}

export function authorizeProspectiveRun(current,history){
 ensure(current?.event==='push'&&current.run_attempt===1&&current.actor?.id===32909488&&current.head_branch==='feat/mathgraph-mention-agent-v1-20261102'&&current.path==='.github/workflows/mathgraph-fresh-proof-v1.yml'&&Array.isArray(history?.workflow_runs)&&history.total_count===history.workflow_runs.length&&history.workflow_runs.some(r=>r.id===current.id)&&history.workflow_runs.filter(r=>r.id<=current.id).length===1,'PROSPECTIVE_EPOCH_REFUSED');return true;
}
