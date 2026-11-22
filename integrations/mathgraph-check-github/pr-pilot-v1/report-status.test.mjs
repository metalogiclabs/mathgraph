import test from 'node:test';
import assert from 'node:assert/strict';
import {projectStatusObservation,renderStatusReport} from './report-status.mjs';

// Literal selected-consumer output; mutation tests below are not native claims.
const html=`<!DOCTYPE html>
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
<h2>Check</h2>
<p class="summary">Total: 1 &mdash; <span class="pass">Passed: 1</span> &middot; <span class="fail">Failed: 0</span> &middot; <span class="skip">Skipped: 0</span></p>
<table><tr><th>Test</th><th>Status</th><th>Time (s)</th></tr>
<tr><td>.ok</td><td class="pass">PASS</td><td>0</td></tr>
</table>
<hr>
<p class="summary pass">Grand Total: 1 &mdash; Passed: 1, Failed: 0, Skipped: 0</p>
</body></html>`;
const raw={id:'plain_pass',accepted:true,rows:[['.ok','PASS','pass','0']],count:1,html};

test('HTML projection accepts the selected structure and rejects hidden or unsupported markup',()=>{
 assert.notEqual(projectStatusObservation(raw,'plain_pass'),null);
 for(const changed of ['<!--'+html+'-->',html.replace('>PASS</td>','><span>PASS</span></td>'),
  html.replace('.pass{background:','.pass{display:none;background:'),
  html.replace('<table>','<script><table>'),html+'\n'+html])
  assert.equal(projectStatusObservation({...raw,html:changed},'plain_pass'),null);
});

test('projection binds rendered case identity and section totals to actual HTML',()=>{
 const observed=projectStatusObservation({...raw,html:html.replace('<td>.ok</td>','<td>.different</td>').replace('>Total: 1','>Total: 2')},'plain_pass');
 assert.equal(observed.rendered_rows[0][0],'.different');
 assert.equal(observed.section_summary.total,2);
 assert.equal(observed.summary.total,1);
});

test('count-only and metadata-only discrepancies are visible in the witness',()=>{
 const expected=projectStatusObservation(raw,'plain_pass');
 for(const [key,change,needle] of [['count',o=>{o.count=2;},/Returned count \| 1 \| 1 \| 2/],
  ['rows',o=>{o.rows[0][0]='.changed';o.rows[0][3]='9.5';},/\.changed.*9\.5/]]){
  const actual=structuredClone(expected);change(actual);
  const base={id:'plain_pass',input:'<testsuite><testcase name="ok"/></testsuite>',expected,observed:expected,passed:true,differences:[]};
  const head={...base,observed:actual,passed:false,differences:[key]};
  const report=renderStatusReport({status:'OBSERVED_MISMATCH',subjects:{},evidence:{},
   base:{complete:true,observations:[base],mismatches:[]},head:{complete:true,observations:[head],mismatches:[head]},
   cost:{wall_seconds:1,native_processes:1}});
  assert.match(report,needle);
 }
});
