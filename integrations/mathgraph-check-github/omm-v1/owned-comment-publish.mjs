// An independently requalified, *first-party* neutral App Check for one real
// owner comment on frozen PR239. Not a production issue_comment listener.
const REPO='metalogiclabs/mathgraph',NUMBER=239,OWNER=32909488,APP_ID=5308912;
const HEAD='2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17';
const BASE='dfd87d1e921953badedcfae21ade76bb38f5c04a';
const SOURCE='e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9';
const NAME='MathGraph Check / OMM owner opt-in (advisory)';
const SHA256=/^[a-f0-9]{64}$/;
const root='/repos/'+REPO;
const fail=(ok)=>{if(!ok)throw Error('OWNED_OPTIN_NOT_QUALIFIED');};
const external=id=>`mathgraph-omm-owner-optin-v1:${REPO}:${NUMBER}:${HEAD}:${id}`;

export function buildOwnedCommentCheck({admission,assessment,runUrl}={}){
 fail(admission?.schema==='mathgraph.omm.owned-comment-admission.v1'&&
  admission.status==='SOURCE_ADMITTED_ONLY'&&admission.repository===REPO&&
  admission.number===NUMBER&&Number.isSafeInteger(admission.comment_id)&&admission.comment_id>0&&
  admission.head_sha===HEAD&&admission.base_sha===BASE&&admission.source_sha256===SOURCE&&
  admission.native_receipt==='UNKNOWN'&&admission.original_target==='UNKNOWN'&&
  admission.intent_fidelity==='UNKNOWN'&&admission.evidence_warrant==='UNKNOWN'&&
  admission.publication_permission==='DENIED'&&admission.repair_permission==='DENIED'&&
  /^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(admission.comment_created_at??'')&&
  admission.comment_created_at===admission.comment_updated_at&&
  assessment?.schema==='mathgraph.omm.claim-assessment.v1'&&
  assessment.status==='NATIVE_RECEIPT_BOUND'&&assessment.repository===REPO&&
  assessment.number===NUMBER&&assessment.head_sha===HEAD&&assessment.base_sha===BASE&&
  assessment.candidate_sha256===SOURCE&&assessment.candidate_proof==='LEAN_COMPILED'&&
  assessment.original_target==='NOT_ESTABLISHED_IN_THIS_REPLAY'&&
  assessment.formal_statement_relation==='UNKNOWN'&&assessment.intent_fidelity==='UNKNOWN'&&
  assessment.evidence_warrant==='UNKNOWN'&&assessment.candidate_dependence==='UNKNOWN'&&
  SHA256.test(assessment.native_receipt_sha256??'')&&
  /^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9][0-9]*$/.test(runUrl??''));
 return {name:NAME,head_sha:HEAD,external_id:external(admission.comment_id),
  status:'completed',conclusion:'neutral',output:{
   title:'Owner opt-in: native original target not established (advisory)',
   summary:[`Authenticated first-party [owner request](https://github.com/${REPO}/pull/${NUMBER}#issuecomment-${admission.comment_id}) (`+
    `comment ID ${admission.comment_id}; created ${admission.comment_created_at}).`,
    `Source: [frozen PR239](https://github.com/${REPO}/pull/${NUMBER}) at commit \`${HEAD}\`; candidate SHA-256 \`${SOURCE}\`.`,
    `Native receipt SHA-256: \`${assessment.native_receipt_sha256}\`; [qualification run](${runUrl}).`,
    '| Question | Observation |','|---|---|',
    '| Original request identity | SOURCE_ADMITTED_ONLY |',
    '| Candidate Lean compilation | LEAN_COMPILED |',
    '| Original-target consumer | NOT_ESTABLISHED_IN_THIS_REPLAY |',
    '| Formal-statement relation | UNKNOWN |',
    '| Mathematical intent | UNKNOWN |',
    '| Independent evidence warrant | UNKNOWN |',
    '| Repair permission | DENIED |',
    '', 'This is a push-triggered, frozen first-party qualification, not an active issue_comment listener or a community verification service. A failing original-target consumer does not prove mathematical inequivalence. The evidence is source- and run-specific, not a proof of paper-to-Lean fidelity.'].join('\n')}
 };
}

/** Only this registered App, one comment and exact owned PR head may publish. */
export async function reconcileOwnedCommentCheck({admission,assessment,runUrl,api,verifyAdmission,write=false}={}){
 const payload=buildOwnedCommentCheck({admission,assessment,runUrl});
 fail(typeof api==='function'&&typeof verifyAdmission==='function');
 const confirmAdmission=async()=>{
  const result=await verifyAdmission(admission);
  fail(JSON.stringify(result)===JSON.stringify(admission));
 };
 const confirmSource=async()=>{
  const pr=await api(root+'/pulls/'+NUMBER);
  if(pr?.number!==NUMBER||pr.state!=='open'||pr.user?.id!==OWNER||
   pr.head?.sha!==HEAD||pr.base?.sha!==BASE||
   pr.head?.repo?.full_name!==REPO||pr.base?.repo?.full_name!==REPO)
   throw Error('STALE_PR_HEAD');
 };
 await confirmAdmission();await confirmSource();
 const path=root+'/commits/'+HEAD+'/check-runs?check_name='+encodeURIComponent(NAME)+'&filter=all&per_page=100';
 const list=await api(path);
 if(!Array.isArray(list?.check_runs)||!Number.isSafeInteger(list.total_count)||
  list.total_count!==list.check_runs.length||list.total_count>100)
  throw Error('APP_CHECK_RECONCILIATION_INCOMPLETE');
 const matching=list.check_runs.filter(x=>x.name===NAME);
 if(matching.some(x=>x.app?.id!==APP_ID))throw Error('FOREIGN_APP_CHECK_NAME_COLLISION');
 if(matching.length>1)throw Error('DUPLICATE_OWNED_OMM_CHECK');
 if(matching.length===1&&(matching[0].head_sha!==HEAD||
  matching[0].external_id!==external(admission.comment_id)||
  !Number.isSafeInteger(matching[0].id)))throw Error('OWNED_CHECK_IDENTITY_CHANGED');
 await confirmAdmission();await confirmSource();
 if(!write)return {mode:'PREVIEW',existing:matching.length};
 let result,mode;
 if(matching.length){
  const old=matching[0];
  if(old.status==='completed'&&old.conclusion==='neutral'&&
   old.output?.title===payload.output.title&&old.output?.summary===payload.output.summary){
   result=old;mode='UNCHANGED';
  }else{
   result=await api(root+'/check-runs/'+old.id,{method:'PATCH',body:{
    status:'completed',conclusion:'neutral',external_id:payload.external_id,output:payload.output}});
   mode='UPDATED';
  }
 }else{result=await api(root+'/check-runs',{method:'POST',body:payload});mode='CREATED';}
 if(!Number.isSafeInteger(result?.id))throw Error('APP_CHECK_WRITE_UNCONFIRMED');
 const observed=await api(root+'/check-runs/'+result.id);
 if(observed?.id!==result.id||observed.app?.id!==APP_ID||observed.name!==NAME||
  observed.head_sha!==HEAD||observed.external_id!==payload.external_id||
  observed.status!=='completed'||observed.conclusion!=='neutral'||
  observed.output?.title!==payload.output.title||observed.output?.summary!==payload.output.summary)
  throw Error('APP_CHECK_READBACK_MISMATCH');
 await confirmAdmission();await confirmSource();
 return {mode,number:NUMBER,comment_id:admission.comment_id,app_id:APP_ID,
  check_run_id:result.id,head_sha:HEAD,source_sha256:SOURCE,
  original_target:'NOT_ESTABLISHED_IN_THIS_REPLAY',intent_fidelity:'UNKNOWN',
  evidence_warrant:'UNKNOWN'};
}
