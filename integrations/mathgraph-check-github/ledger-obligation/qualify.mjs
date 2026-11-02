import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {assessLedgerReceipt,ledgerCheck} from './adapter.mjs';
const root=process.argv[2]??'ledger-results';
// Only invoked with artifacts produced in this same trusted push workflow.
// Verify every archived byte before making the native receipt available.
const manifest=await readFile(`${root}/SHA256SUMS`,'utf8');
const entries=manifest.trim().split('\n').map(line=>/^([a-f0-9]{64})  ([A-Za-z0-9_.-]+)$/.exec(line));
if(entries.some(x=>!x)||new Set(entries.map(x=>x[2])).size!==entries.length||!entries.some(x=>x[2]==='receipt.json'))throw Error('INVALID_ARCHIVE_MANIFEST');
for(const [,digest,name] of entries){if(createHash('sha256').update(await readFile(`${root}/${name}`)).digest('hex')!==digest)throw Error('ARCHIVE_BYTES_CHANGED');}
const receipt=JSON.parse(await readFile(`${root}/receipt.json`,'utf8'));
const report=assessLedgerReceipt(receipt,{subjectRepository:'metalogiclabs/L4YAML',subjectHead:'821c715217f135c73abb643df2878557ca099380',verifierHead:process.env.GITHUB_SHA,runId:Number(process.env.GITHUB_RUN_ID),authenticated:true});
const check=ledgerCheck(report,{carrierSha:process.env.GITHUB_SHA,runUrl:`https://github.com/metalogiclabs/mathgraph/actions/runs/${process.env.GITHUB_RUN_ID}`});
await writeFile(`${root}/assessment.json`,JSON.stringify(report,null,2)+'\n');
await writeFile(`${root}/check.json`,JSON.stringify(check,null,2)+'\n');
console.log(JSON.stringify(report));
if(report.status!=='PASS')process.exitCode=1;
