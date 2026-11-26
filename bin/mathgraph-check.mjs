#!/usr/bin/env node
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs,runCatalogue} from '../integrations/mathgraph-check-github/catalogue-check-v1/run.mjs';
import {PROFILES} from '../integrations/mathgraph-check-github/catalogue-check-v1/catalogue.mjs';
import {runNumerical,PROFILE,SCOPE} from '../integrations/mathgraph-check-github/telemetry-integer-v1/run.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const MAP='docs/releases/check-local-pilot-20261126.source-map.json';
const hash=x=>createHash('sha256').update(x).digest('hex');
const json=x=>JSON.stringify(x,null,2)+'\n';
const ENTRY_FILES=['bin/mathgraph-check.mjs',MAP,
 'integrations/mathgraph-check-github/telemetry-integer-v1/run.mjs',
 'integrations/mathgraph-check-github/telemetry-integer-v1/native.py',
 'integrations/mathgraph-check-github/telemetry-integer-v1/corpus.py'];

export function capabilities(){return {release:'local-pilot-20261126',status:'CANDIDATE',permission:'ADVISORY_ONLY',
 profiles:[{id:'l4yaml-retained-v1',checks:PROFILES.map(p=>({id:p.id,cases:p.case_count,boundary:p.boundary})),
  boundary:'Five finite retained L4YAML profiles. The 104-prompt ledger is not 104 executable detectors.'},
 {id:PROFILE,cases:108,boundary:SCOPE}],
 requirements:{node:'24',python:'3.10+',lean:'4.35.0 for l4yaml-retained-v1 only'},
 operator_use:'NOT_RUN',comparative_value:'NOT_ESTABLISHED',
 source_handling:'Reviewed local Git objects only; no automatic acquisition, App keys or model calls.'};}

export function parseOperatorArgs(argv){
 if(argv.length===1&&['--help','--capabilities','--source-map'].includes(argv[0]))return {display:argv[0]};
 const rest=[];let profile;
 for(let i=0;i<argv.length;i+=2){
  if(argv[i]==='--profile'){
   if(profile!==undefined||!argv[i+1])throw Error('INVALID_PROFILE_ARGUMENT');profile=argv[i+1];
  }else rest.push(argv[i],argv[i+1]);
 }
 if(!['l4yaml-retained-v1',PROFILE].includes(profile))throw Error('SELECT_SUPPORTED_PROFILE: use --capabilities');
 if(rest.includes('--help'))throw Error('HELP_MUST_BE_STANDALONE');
 if(profile===PROFILE&&rest.includes('--profiles'))throw Error('SUBPROFILE_SELECTION_NOT_SUPPORTED');
 return {profile,options:parseArgs(rest)};
}

async function identity(){
 const files={};for(const path of ENTRY_FILES)files[path]=hash(await readFile(join(ROOT,path)));
 const p=spawnSync('git',['-C',ROOT,'rev-parse','HEAD'],{encoding:'utf8',timeout:10000});
 const commit=p.status===0&&/^[a-f0-9]{40}$/.test(p.stdout.trim())?p.stdout.trim():null;
 const dirty=spawnSync('git',['-C',ROOT,'status','--porcelain','--untracked-files=all','--',...ENTRY_FILES],{encoding:'utf8',timeout:10000});
 return {name:'local-pilot-20261126',commit,entry_files:files,
  tracked_entry_clean:dirty.status===0&&!dirty.stdout.trim(),qualification:'EXACT_SOURCE_RUN_REQUIRED'};
}

export async function runOperator(argv){
 const parsed=parseOperatorArgs(argv);
 if(parsed.display==='--capabilities')return {text:json(capabilities()),exit_code:0};
 if(parsed.display==='--source-map')return {text:await readFile(join(ROOT,MAP),'utf8'),exit_code:0};
 if(parsed.display==='--help')return {exit_code:0,text:
  'MathGraph Check — local pilot candidate\n\n'+
  'node bin/mathgraph-check.mjs --profile PROFILE --repo LOCAL_GIT --base REV --head REV --out NEW_DIRECTORY\n'+
  '  [--python python3] [--lean LEAN_4_35_BINARY] [--timeout-seconds 120]\n\n'+
  'Profiles: l4yaml-retained-v1, telemetry-integer-identity-v1.\n'+
  '--capabilities lists finite scopes; --source-map lists reconciled source roles.\n'+
  'Reviewed source only. No automatic network acquisition, model usage, installation or repair.\n'+
  'Existing output is never overwritten. Exit 0: declared finite head agreement; 1: completed discrepancy; 2: UNKNOWN/incomplete/omitted profile or command error.\n'+
  'Each invocation reexecutes the exact revisions. Results grant no deployment permission.\n'};
 const before=await identity();
 const run=await (parsed.profile===PROFILE?runNumerical:runCatalogue)(parsed.options);
 const result=run.result;let exit_code=run.exit_code;
 const after=await identity();
 const changed=JSON.stringify(before)!==JSON.stringify(after);
 if(changed){result.status='UNKNOWN';result.reason='OPERATOR_METHOD_CHANGED_DURING_EXECUTION';exit_code=2;}
 result.release={...before,profile:parsed.profile,source_map_sha256:before.entry_files[MAP]};
 const out=resolve(parsed.options.out),report=join(out,'report.md');
 await writeFile(join(out,'result.json'),json(result));
 await writeFile(report,(changed?'**Operator result: UNKNOWN — entry-point evidence changed during execution. The following component observations do not qualify this operator run.**\n\n':'')+
  (await readFile(report,'utf8'))+'\n## Operator entry point\n\n'+
  `Release candidate: local-pilot-20261126. Verifier commit: ${before.commit??'unavailable'}.\n\n`+
  'The result records entry-point/source-map hashes and whether the entry files match Git. This identity does not independently qualify the run or its requirement.\n');
 return {exit_code,text:json({status:result.status,profile:parsed.profile,report,verifier:before.commit,
  permission:'ADVISORY_ONLY',cost:result.cost})};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{const r=await runOperator(process.argv.slice(2));process.stdout.write(r.text);process.exitCode=r.exit_code;}
 catch(e){console.error(e.message);process.exitCode=2;}
}
