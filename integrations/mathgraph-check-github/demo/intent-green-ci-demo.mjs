// Synthetic, local-only demonstration. Never authenticate live CI with this.
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {refund} from './agent-refund.mjs';
import {expectedRefund} from './independent-refund-oracle.mjs';
import {auditIntent,digestContract,renderIntentReport,SCHEMA} from '../intent-contract-v1.mjs';
const root=dirname(fileURLToPath(import.meta.url));
const sha256=x=>createHash('sha256').update(x).digest('hex');
const ORACLE_PIN='6714ff76a5162ef8a4a6a91bd2449f57546cb1692125f61676e498310d293952';
export function buildSyntheticDemo(){
 if(sha256(readFileSync(join(root,'independent-refund-oracle.mjs')))!==ORACLE_PIN)
   throw Error('SYNTHETIC_ORACLE_PIN_CHANGED');
 const happy={id:'order-open',amount:49,status:'PENDING'};
 if(refund(happy).status!=='REFUNDED')throw Error('AGENT_HAPPY_PATH_NOT_GREEN');
 const test={id:'order-already-refunded',amount:49,status:'REFUNDED'};
 const actual=refund(test),expected=expectedRefund(test);
 if(JSON.stringify(actual)===JSON.stringify(expected))throw Error('SYNTHETIC_GAP_MISSING');
 const source='b'.repeat(40),verifier='c'.repeat(40);
 const contract={schema:SCHEMA,subject:{
   repository:'example/synthetic-mathgraph-intent-demo',pr:1,
   base_sha:'a'.repeat(40),head_sha:source
 },claims:[{
   id:'no-double-refund',statement:'Already refunded orders must be denied without a second refund.',
   requires:['already-refunded-case']
 }],probes:[{
   id:'already-refunded-case',input_sha256:sha256(JSON.stringify(test)),
   oracle_sha256:ORACLE_PIN,verifier_sha:verifier
 }]};
 const witness={input:test,observed:actual,expected};
 const csha=digestContract(contract);
 const receipts=[{
   id:'synthetic-independent-probe-1',probe_id:'already-refunded-case',
   subject_sha:source,contract_sha256:csha,
   input_sha256:contract.probes[0].input_sha256,
   oracle_sha256:ORACLE_PIN,verifier_sha:verifier,
   result:'COUNTEREXAMPLE',exit_code:1,log_sha256:sha256(JSON.stringify({
     agent_happy_path:'PASS',independent_probe:'FAIL'})),
   witness_sha256:sha256(JSON.stringify(witness))
 }];
 // This simulates a trusted host. It is NOT a real GitHub authentication.
 const simulatedAuthority={
   allowedRepositories:[contract.subject.repository],expectedHeadSha:source,
   expectedContractSha256:csha,authenticatedReceiptIds:[receipts[0].id],
   qualifiedVerifierShas:[verifier],qualifiedOracleShas:[ORACLE_PIN]
 };
 const report=auditIntent(contract,receipts,simulatedAuthority);
 if(report.status!=='BLOCKED'||report.permission!=='ADVISORY_ONLY')
   throw Error('DEMO_FAIL_CLOSED');
 return {demo_only:true,agent_tests:'GREEN_HAPPY_PATH_ONLY',
   independent_oracle:'FAIL_ON_ALREADY_REFUNDED',witness,contract,receipts,report};
}
export function writeSyntheticDemo(out){
 const result=buildSyntheticDemo();
 mkdirSync(out,{recursive:true});
 writeFileSync(join(out,'report.json'),JSON.stringify(result,null,2)+'\n');
 const html=renderIntentReport(result.report).replace('<main>',
   '<main><div class="eyebrow">SYNTHETIC DEMO · NOT A LIVE CUSTOMER AUDIT</div>'+
   '<p>Agent: DONE &nbsp;·&nbsp; Its tests: GREEN &nbsp;·&nbsp; Independent requirement: FAILED</p>');
 writeFileSync(join(out,'report.html'),html);
 return result;
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1]){
 const out=process.argv[2]||'/tmp/mathgraph-intent-demo';
 const r=writeSyntheticDemo(out);
 console.log('SYNTHETIC_AGENT_TESTS_GREEN');
 console.log('SYNTHETIC_INDEPENDENT_COUNTEREXAMPLE='+r.report.results[0].probes[0].witness_sha256);
 console.log('REPORT_STATUS='+r.report.status);
 console.log('REPORT_DIR='+out);
}
