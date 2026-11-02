// Parses one native Rust regression result without treating arbitrary command
// failure, zero selected tests, or a different panic as evidence of the bug.
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { evaluateNyxEventFrameV1 } from './nyx-event-frame-v1.mjs';
const NAME = 'propagation::stopcond::longitude_event_in_rotating_frame';
const SETUP_FAILURE = /error:\s*(could not compile|failed to|linking with|failed to download)|Caused by:\s*(failed to|could not)/i;

export function parseNyxNativeRunV1({ exitCode, stdout, stderr, expectedMode } = {}) {
  const text = String(stdout ?? '') + '\n' + String(stderr ?? '');
  const base = { exitCode, testCount: 0, regressionMarker: null };
  if (!Number.isSafeInteger(exitCode) || !['base','head'].includes(expectedMode))
    return { ...base, reason: 'INVALID_INVOCATION' };
  if (SETUP_FAILURE.test(text)) return { ...base, reason: 'SETUP_FAILED' };
  if (/^running 0 tests?$/m.test(text)) return { ...base, reason: 'ZERO_TESTS' };
  if (!/^running 1 test$/m.test(text)) return { ...base, reason: 'UNEXPECTED_FAILURE' };

  const selected = text.split('\n').some(line =>
    line.trim() === `test ${NAME} ... ok` || line.trim() === `test ${NAME} ... FAILED`);
  if (!selected) return { ...base, reason: 'UNEXPECTED_FAILURE' };
  const count = { ...base, testCount: 1 };
  const passed = exitCode === 0 &&
    text.includes(`test ${NAME} ... ok`) &&
    /test result: ok\. 1 passed; 0 failed;/.test(text);
  const failedAsExpected = exitCode !== 0 &&
    text.includes(`test ${NAME} ... FAILED`) &&
    /test result: FAILED\. 0 passed; 1 failed;/.test(text) &&
    text.includes('Earth-fixed longitude zero must be found in the requested event frame: EventNotFound');
  if (expectedMode === 'base') {
    if (passed) return { ...count, reason: 'UNEXPECTED_PASS' };
    if (failedAsExpected) return { ...count, regressionMarker: 'EventNotFound', reason: 'EXPECTED_REGRESSION' };
  } else if (passed) return { ...count, reason: 'PASSED' };
  return { ...count, reason: 'UNEXPECTED_FAILURE' };
}

export function buildNyxRunReceiptV1({mode,exitCode,stdout,stderr,sourceSha} = {}) {
  const parsed = parseNyxNativeRunV1({exitCode,stdout,stderr,expectedMode:mode});
  return {
    ...parsed,
    sourceSha,
    logSha256: createHash('sha256').update(String(stdout??'')+'\n'+String(stderr??'')).digest('hex')
  };
}

export function combineNyxRunReceiptsV1({base,head,rustc,cargoLockSha256,workflowRunUrl} = {}) {
  const source={
    repository:'nyx-space/nyx',
    baseSha:'d1c3598d5ccf4c984a1d3dd82c450e2af363e821',
    headSha:'ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b',
    testBlobSha:'830919f246536ccc65be4041e9a4b775220f57bb'
  };
  const receipt={source,base,head,toolchain:{rustc,cargoLockSha256},runner:{workflowRunUrl}};
  const verdict=evaluateNyxEventFrameV1(receipt);
  if (base?.sourceSha!==source.baseSha || head?.sourceSha!==source.headSha) {
    verdict.status='UNKNOWN';
    verdict.evidence=null;
    verdict.unknowns.push('LEG_SOURCE_MISMATCH');
  }
  return {receipt,verdict};
}

export async function runNyxCliV1(args = []) {
  if (args.length%2!==0) throw new Error('INVALID_ARGUMENT_PAIRS');
  const options=new Map();
  for (let i=0;i<args.length;i+=2) {
    if (!args[i].startsWith('--') || options.has(args[i])) throw new Error('INVALID_ARGUMENT');
    options.set(args[i],args[i+1]);
  }
  const get=key=>{const value=options.get('--'+key);if(!value)throw Error('MISSING_'+key.toUpperCase().replaceAll('-','_'));return value;};
  const mode=get('mode');
  if (mode==='base'||mode==='head') {
    const exitCode=Number(get('exit'));
    const [stdout,stderr]=await Promise.all([readFile(get('stdout'),'utf8'),readFile(get('stderr'),'utf8')]);
    const result=buildNyxRunReceiptV1({mode,exitCode,stdout,stderr,sourceSha:get('source-sha')});
    await writeFile(get('out'),JSON.stringify(result,null,2)+'\n');
    return result;
  }
  if (mode==='finalize') {
    const [base,head]=await Promise.all([readFile(get('base'),'utf8'),readFile(get('head'),'utf8')]);
    const result=combineNyxRunReceiptsV1({
      base:JSON.parse(base),head:JSON.parse(head),rustc:get('rustc'),
      cargoLockSha256:get('cargo-lock-sha256'),workflowRunUrl:get('run-url')
    });
    await writeFile(get('out'),JSON.stringify(result,null,2)+'\n');
    return result;
  }
  throw new Error('INVALID_MODE');
}

if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const result=await runNyxCliV1(process.argv.slice(2));
  console.log(JSON.stringify(result.verdict ?
    {status:result.verdict.status,unknowns:result.verdict.unknowns} :
    {reason:result.reason,testCount:result.testCount,sourceSha:result.sourceSha}));
  if (result.verdict && result.verdict.status!=='CANDIDATE_BOUNDED') process.exitCode=1;
}
