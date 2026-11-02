// Bounded native gate qualification. The trusted caller must authenticate the
// workflow/run and artifact bytes before supplying authenticated=true. Receipt
// JSON, model text and green CI alone cannot confer that authority.
const CASES=['clean','direct','no_bytecode','isolated','warning_option','heredoc_data','literal_backslashes'];
const ARMS=['original','repaired','withdrawn'];
const SHA=/^[a-f0-9]{40}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function assessLedgerReceipt(r,c={}) {
 const common={permission:'ADVISORY_ONLY',subject:{repository:c.subjectRepository,head_sha:c.subjectHead},verifier_head:c.verifierHead};
 const unknown=reason=>({...common,status:'UNKNOWN',reason});
 if(c.authenticated!==true)return unknown('UNAUTHENTICATED_RECEIPT');
 if(c.subjectRepository!=='metalogiclabs/L4YAML'||!SHA.test(c.subjectHead??'')||!SHA.test(c.verifierHead??''))return unknown('INVALID_TRUSTED_CONTEXT');
 if(r?.schema!=='mathgraph.ledger-obligation.v1'||r?.subject?.repository!==c.subjectRepository||r?.subject?.head_sha!==c.subjectHead||!SHA.test(r?.subject?.base_sha??'')||r.subject.base_sha===c.subjectHead)return unknown('SOURCE_MISMATCH');
 if(r?.verifier?.repository!=='metalogiclabs/mathgraph'||r?.verifier?.head_sha!==c.verifierHead||r?.verifier?.toolchain!=='leanprover/lean4:v4.35.0')return unknown('VERIFIER_MISMATCH');
 if(!Number.isSafeInteger(c.runId)||r?.run?.id!==c.runId||r?.run?.attempt!==1)return unknown('RUN_MISMATCH');
 if(!same(r.cases,CASES)||!Array.isArray(r.arms)||!same(r.arms.map(x=>x?.id),ARMS))return unknown('INCOMPLETE_PROTOCOL');
 const assessed=[];
 for(const arm of r.arms){
  if(arm.source_sha!==(arm.id==='repaired'?c.subjectHead:r.subject.base_sha)||arm.restored_clean!==true)return unknown('ARM_SOURCE_MISMATCH');
  if(![0,1].includes(arm.guards_exit)||!Array.isArray(arm.rows)||!same(arm.rows.map(x=>x?.id),CASES)||!Array.isArray(arm.repository_exits)||arm.repository_exits.length!==4||arm.repository_exits.some(x=>![0,1].includes(x)))return unknown('INCOMPLETE_NATIVE_RESULTS');
  const failures=[];
  for(const row of arm.rows){
   if(row.oracle_exit!==0||![0,1].includes(row.gate_exit)||typeof row.oracle_executed!=='boolean')return unknown('NATIVE_EXECUTION_UNKNOWN');
   const executes=!['clean','heredoc_data'].includes(row.id);
   if(row.oracle_executed!==executes)return unknown('ORACLE_CONTROL_MISMATCH');
   if(row.gate_exit!==(executes?1:0))failures.push({case:row.id,reason:executes?'FALSE_GREEN':'FALSE_REFUSAL'});
  }
  assessed.push({id:arm.id,status:failures.length?'FAIL':'PASS',failures,guards_exit:arm.guards_exit,repository_exits:arm.repository_exits});
 }
 const [original,repaired,withdrawn]=assessed;
 const expectedNegative=x=>x.status==='FAIL'&&same(x.failures.map(f=>f.case),['no_bytecode','isolated','warning_option'])&&x.guards_exit===1&&same(x.repository_exits,[0,1,0,0]);
 const qualified=expectedNegative(original)&&repaired.status==='PASS'&&repaired.guards_exit===0&&same(repaired.repository_exits,[0,1,1,0])&&expectedNegative(withdrawn);
 return {...common,status:qualified?'PASS':'FAIL',reason:qualified?'BOUNDED_REPAIR_QUALIFIED':'PROTOCOL_OBLIGATION_FAILED',arms:assessed};
}
export function ledgerCheck(report,{carrierSha,runUrl}={}) {
 if(!SHA.test(carrierSha??'')||report?.verifier_head!==carrierSha)throw Error('STALE_CARRIER');
 if(report?.permission!=='ADVISORY_ONLY'||!['PASS','FAIL','UNKNOWN'].includes(report?.status))throw Error('UNQUALIFIED_REPORT');
 if(!/^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[0-9]+$/.test(runUrl??''))throw Error('INVALID_RECEIPT_URL');
 const rows=(report.arms??[]).map(a=>`| ${a.id} | ${a.status} | ${a.failures?.map(x=>x.case).join(', ')||'none in frozen cases'} |`).join('\n');
 return {name:'MathGraph Check / ledger obligation',head_sha:carrierSha,status:'completed',conclusion:'neutral',external_id:`ledger-obligation-v1:${carrierSha}`,details_url:runUrl,output:{title:`MathGraph Check: ${report.status} — bounded gate qualification`,summary:[
 '**Advisory only. Finite native controls; not general shell equivalence or merge approval.**',
 `Watched subject: ${report.subject.repository}@${report.subject.head_sha}. This Check is attached to the MathGraph verifier commit, not to the watched repository.`,
 '| Gate source | Independent verdict | Counterexamples |\n|---|---|---|\n'+rows,
 `Qualification: ${report.reason}. Repair means the same frozen controls pass, original regression guards fail before repair, and withdrawal restores the observed false greens.`,
 'The boundary is the standalone upstream native gate and Bash/Python fixtures, including a real repository inventory replay. The full L4YAML library and CI are outside this check.',
 `[Native receipts and source identities](${runUrl})`
 ].join('\n\n')}};
}
