import {createHash} from 'node:crypto';
import {isDeepStrictEqual as same} from 'node:util';
import cases from './report-status-cases.json' with {type:'json'};
import {inspectArm} from '../lean-investigator-v1/contracts.mjs';
import {REPORT_PROFILE} from './report-integrity.mjs';

export const STATUS_METHOD='junit-status-preservation-v1';
export const STATUS_CASES=Object.freeze(cases.map(c=>Object.freeze(c)));
export const STATUS_CORPUS_SHA='3b42ef2d3c47bd2c4c997d797386b53c71c07acc7998893ffc0cff79a95603b8';
export const STATUS_REFERENCE_SHA='b3b59888b1a15888aff3a144acadce7ae7479e69de35ea512f0fcca8bf481079';
export const STATUS_SCOPE='Eight fixed JUnit outcome cases through the actual junitCases and pythonFfiHtml functions, under Lean 4.35.0 with the declared empty HtmlReport dependency. Error and failure map to FAIL in this selected three-status renderer. HTML projection requires the fixed single-section layout and stylesheet; unsupported markup is UNKNOWN. Full JUnit conformance, error-versus-failure distinction, full dependency environment, report CLI and whole-repository correctness remain UNKNOWN.';
const PRODUCER='https://github.com/pytest-dev/pytest/blob/13ba5cba07f56728d25d89cc7f5f0b24b06c3b95/src/_pytest/junitxml.py';
const hash=x=>createHash('sha256').update(x).digest('hex');
const PASS='GUARD_PASSED',FAIL='CANDIDATE_ASSERTION_FAILURE';
const groups=[{id:'error_preservation',hypothesis:'Explicit errors remain nonpassing'},
 {id:'ordinary_outcomes',hypothesis:'Pass, failure and skip controls retain their outcomes'},
 {id:'composition',hypothesis:'Mixed rows and harmless text preserve status and totals'}];
export function statusPlan(){return {summary:'Retained test-outcome preservation through the actual report consumer',
 requirement:{producer:PRODUCER,policy:'Direct error/failure children map to FAIL/fail; skipped to SKIP/skip; otherwise PASS/pass. Rendered rows and counts preserve those outcomes.',scope:STATUS_SCOPE},tests:structuredClone(groups)};}

export function statusObserver(c){return `import ${REPORT_PROFILE.module}
open ${REPORT_PROFILE.namespace} Lean
def main : IO Unit := do
  let result : Json := match junitCases ${JSON.stringify(c.input)} with
    | .error e => Json.mkObj [("id", toJson ${JSON.stringify(c.id)}), ("accepted", toJson false), ("message", toJson e)]
    | .ok rows =>
      let (html, n) := pythonFfiHtml [⟨"Check", rows⟩]
      Json.mkObj [("id", toJson ${JSON.stringify(c.id)}), ("accepted", toJson true),
        ("rows", toJson (rows.map (fun (c : Case) => [c.name, c.status, c.css, c.time]))),
        ("html", toJson html), ("count", toJson n)]
  IO.println result.compress
`;}

// The selected single-section renderer has a deliberately closed layout. Requiring
// it prevents comment/script/style text from being mistaken for emitted cells.
const HTML_HEAD=`<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Python API Test Results</title>
<style>
body{font-family:system-ui,sans-serif;margin:2em;background:#f8f9fa}
h1{color:#1a1a2e} h2{color:#16213e;margin-top:2em}
table{border-collapse:collapse;width:100%;margin:1em 0}
th,td{border:1px solid #dee2e6;padding:6px 12px;text-align:left}
th{background:#343a40;color:#fff}
.pass{background:#d4edda;color:#155724}
.fail{background:#f8d7da;color:#721c24}
.skip{background:#fff3cd;color:#856404}
.summary{font-size:1.1em;margin:0.5em 0}
</style></head><body>
<h1>Python API Test Results</h1>
<h2>Check</h2>`;
const decode=s=>s.replace(/&(amp|lt|gt|quot|#x27);/g,(_,key)=>({amp:'&',lt:'<',gt:'>',quot:'"','#x27':"'"}[key]));
const textCell='((?:[^<&]|&(?:amp|lt|gt|quot|#x27);)*)';
const caseRow=new RegExp('^<tr><td>'+textCell+'</td><td class="([^"<>&]*)">([^<>&]*)</td><td>'+textCell+'</td></tr>$');
// A projection of this exact emitted structure, not a general HTML parser.
export function projectStatusObservation(raw,id){
 if(!raw||raw.id!==id||typeof raw.accepted!=='boolean')return null;
 if(!raw.accepted)return typeof raw.message==='string'?{accepted:false,message:raw.message}:null;
 if(!Array.isArray(raw.rows)||!raw.rows.every(r=>Array.isArray(r)&&r.length===4&&r.every(x=>typeof x==='string'))||
  !Number.isSafeInteger(raw.count)||raw.count<0||typeof raw.html!=='string'||raw.html.length>1024*1024)return null;
 const lines=raw.html.split('\n');
 if(lines.length<22||lines.slice(0,16).join('\n')!==HTML_HEAD||
  lines[17]!=='<table><tr><th>Test</th><th>Status</th><th>Time (s)</th></tr>'||
  lines.at(-4)!=='</table>'||lines.at(-3)!=='<hr>'||lines.at(-1)!=='</body></html>')return null;
 const section=lines[16].match(/^<p class="summary">Total: (\d+) &mdash; <span class="pass">Passed: (\d+)<\/span> &middot; <span class="fail">Failed: (\d+)<\/span> &middot; <span class="skip">Skipped: (\d+)<\/span><\/p>$/);
 const totals=lines.at(-2).match(/^<p class="summary (pass|fail)">Grand Total: (\d+) &mdash; Passed: (\d+), Failed: (\d+), Skipped: (\d+)<\/p>$/);
 if(!section||!totals)return null;
 const [,css,...numbers]=totals;const [total,passed,failed,skipped]=numbers.map(Number);
 const sectionNumbers=section.slice(1).map(Number);
 if(![total,passed,failed,skipped,...sectionNumbers].every(Number.isSafeInteger))return null;
 const rendered_rows=[];
 for(const line of lines.slice(18,-4)){
  const m=line.match(caseRow);if(!m)return null;
  rendered_rows.push([decode(m[1]),m[3],m[2],decode(m[4])]);
 }
 const [st,sp,sf,ss]=sectionNumbers;
 return {accepted:true,rows:raw.rows,count:raw.count,summary:{total,passed,failed,skipped,css},
  section_summary:{total:st,passed:sp,failed:sf,skipped:ss},rendered_rows,
  rendered_statuses:rendered_rows.map(r=>[r[1],r[2]])};
}

export function assessStatusRevision(arm,source){
 // Reuse the same native source/build/control boundary; status groups are derived
 // from observed structured values, rather than inferred from false guards.
 const boundary=inspectArm(arm,{profile:REPORT_PROFILE,plan:{tests:[]},source});
 const nativeCases=Array.isArray(arm?.cases)?arm.cases:[];
 const exact=same(nativeCases.map(c=>c?.id).sort(),STATUS_CASES.map(c=>c.id).sort());
 const observations=[];let observed=true;
 for(const c of STATUS_CASES){
  const row=nativeCases.find(r=>r?.id===c.id);
  const value=row?.exit_code===0&&row.test_file_sha256===hash(statusObserver(c))?projectStatusObservation(row.observation,c.id):null;
  if(!value){observed=false;continue;}
  const {css,...section_summary}=c.expected.summary;
  const expected={...c.expected,section_summary,rendered_rows:c.expected.rows,rendered_statuses:c.expected.rows.map(r=>[r[1],r[2]])};
  const differences=Object.keys(expected).filter(k=>!same(expected[k],value[k]));
  observations.push({...c,expected,observed:value,passed:differences.length===0,differences});
 }
 const complete=boundary.complete&&exact&&observed;
 const reason=complete?null:arm?.build_exit!==0?'MODULE_BUILD_FAILED':!boundary.source_ok?'SOURCE_BINDING_MISMATCH':
  !boundary.controls_ok?'NATIVE_CONTROLS_FAILED':!boundary.baseline_ok?'SELECTED_GATE_FAILED':
  !boundary.complete?'NATIVE_BOUNDARY_INCOMPLETE':!exact?'CASE_IDENTITIES_INCOMPLETE':'CASE_OBSERVATIONS_INCOMPLETE';
 return {complete,reason,groups:groups.map(g=>({id:g.id,meaning:'UNVERIFIED',execution:!complete?'UNKNOWN':
  observations.some(o=>o.group===g.id&&!o.passed)?FAIL:PASS})),
  observations:complete?observations:[],mismatches:complete?observations.filter(o=>!o.passed):[]};
}

const display=x=>({[PASS]:'Pass',[FAIL]:'Discrepancy',UNKNOWN:'Unknown'}[x]??'Unknown');
function view(value,axis){
 if(!value)return 'Unknown';if(axis==='acceptance')return value.accepted?'Accepted':'Rejected';
 if(!value.accepted)return 'Not rendered';
 if(axis==='rows')return JSON.stringify(value.rows);
 if(axis==='rendered_rows')return JSON.stringify(value.rendered_rows);
 if(axis==='rendered')return value.rendered_statuses.map(r=>r.join('/')).join(', ')||'No status cells';
 if(axis==='count')return String(value.count);
 if(axis==='totals'||axis==='section'){
  const s=axis==='section'?value.section_summary:value.summary;
  return `${s.total} total / ${s.passed} passed / ${s.failed} failed / ${s.skipped} skipped`;
 }
 return value.summary.css;
}
export function renderStatusReport(r){
 const title=r.status==='UNKNOWN'?'Comparison incomplete':r.status==='OBSERVED_MISMATCH'?
  'The head disagrees with the selected test-outcome requirements':'The head preserves the selected test outcomes';
 const lines=['# MathGraph Check — JUnit outcome preservation','',`**${title}.**`,'',
  '## Requirement','',
  'An explicit test error must remain nonpassing through the report. This selected renderer uses PASS/FAIL/SKIP; both errors and assertion failures belong in FAIL and in the failed total. Pass, failure, skip, ordering and harmless-text controls accompany the error cases.','',
  `[Pinned pytest producer semantics](${PRODUCER}) support the error/nonpass distinction. The finite three-status mapping is explicit; ElementTree supplies XML structure, not semantic authority.`,'',
  r.reference?.status==='OBSERVED_AGREEMENT'?'This run independently replayed the reference for all eight status cases.':'Reference execution has not been qualified in this run.',''];
 if(r.reason)lines.push('**Reason:** '+r.reason,'');
 lines.push('## Source revisions','');
 for(const label of ['base','head']){const s=r.subjects?.[label];if(s)lines.push(`- **${label}:** \`${s.revision}\`; source SHA-256 \`${s.source_sha256}\`.`);}
 lines.push('','Source identity comes from local Git objects; remote publisher authentication is outside this check.','');
 if(r.comparison?.length){
  lines.push('## Obligation comparison','','| Obligation | Base | Head | Change |','| --- | --- | --- | --- |');
  for(const row of r.comparison)lines.push(`| ${groups.find(g=>g.id===row.id).hypothesis} | ${display(row.base)} | ${display(row.head)} | ${row.change.replaceAll('_',' ').toLowerCase()} |`);
  lines.push('');
 }
 for(const label of ['base','head'])if(r[label])lines.push(`**${label}:** ${r[label].complete?r[label].observations.length+' cases observed; '+r[label].mismatches.length+' discrepancies.':'UNKNOWN — '+r[label].reason+'.'}`,'');
 const witness=(r.head?.mismatches?.length?r.head.mismatches:r.base?.mismatches??[]).toSorted((a,b)=>Buffer.byteLength(a.input)-Buffer.byteLength(b.input))[0];
 if(witness){
  const base=r.base?.observations?.find(o=>o.id===witness.id)?.observed,head=r.head?.observations?.find(o=>o.id===witness.id)?.observed;
  lines.push('## A distinguishing input','','Smallest failing input in this fixed corpus:','','```xml',witness.input,'```','',
   '| Observation | Requirement | Base | Head |','| --- | --- | --- | --- |');
  for(const [label,axis] of [['XML acceptance','acceptance'],['Case rows: name, status, class, time','rows'],
   ['Rendered rows: name, status, class, time','rendered_rows'],['Returned count','count'],
   ['Rendered section totals','section'],['Rendered grand totals','totals'],['Grand-total class','css']]){
   const cell=v=>view(v,axis).replaceAll('|','\\|').replaceAll('\n','\\n');
   lines.push(`| ${label} | ${cell(witness.expected)} | ${cell(base)} | ${cell(head)} |`);
  }
  lines.push('','Compared fields that disagree: '+witness.differences.map(k=>'`'+k+'`').join(', ')+'.');
  lines.push('');
 }
 lines.push('## Reuse and cost','',
  'The eight-case status profile is separate from the unchanged nineteen-case envelope profile. A successful envelope check does not establish test-outcome preservation. Both revisions require fresh execution.','',
  `- Wall time: ${r.cost.wall_seconds.toFixed(3)} seconds.`,
  `- Native subprocesses: ${r.cost.native_processes??'not completed'}.`,
  '- Model calls: 0. Human effort, external operator use and comparative advantage: NOT_RUN.','',
  '## Next step','',r.status==='UNKNOWN'?'Resolve the recorded source, runtime or observation problem and rerun into a new output directory.':
   r.status==='OBSERVED_MISMATCH'?'Review the actual row and rendered counts above. Recheck a candidate repair with this unchanged profile and run the separate envelope profile.':
   'Review the exact source change and normal repository CI. The selected test-outcome requirements agree.','',
  '## Scope','',STATUS_SCOPE,'',
  'Report generation may successfully return zero while displaying failed tests. This profile does not impose a different CLI exit policy or grant hosted admission or automatic repair permission.','',
  '## Evidence','','- `result.json`: source/method identities, actual observations, comparisons and measured costs.');
 for(const name of ['request.json','reference.json','native.json','driver.log'])if(r.evidence?.[name])lines.push('- `'+name+'`: evidence retained from this invocation.');
 if(Object.keys(r.evidence??{}).some(k=>k.startsWith('native-logs/')))lines.push('- `native-logs/`: actual execution output, including the emitted JSON and HTML.');
 return lines.join('\n')+'\n';
}
