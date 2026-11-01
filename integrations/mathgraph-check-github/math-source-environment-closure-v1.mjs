/**
 * Resolved Lake dependency closure for the pinned Lean 4.28 Artin replay.
 * No JSON report, manifest or toolchain version string can alone establish
 * native execution; the authenticated GitHub run is a separate obligation.
 */
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {readStrictEvidenceZip} from './math-source-evidence-bytes-v1.mjs';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';

export const MATHLIB_428_COMMIT='8f9d9cff6bd728b17a24e163c9402775d9e6a365';
export const ARTIN_ENVIRONMENT_MEMBERS=Object.freeze([
  'lake-manifest.json','artin-toolchain.txt',
  'artin-lean-version.txt','artin-lake-version.txt','artin-environment.json',
]);
const SHA40=/^[a-f0-9]{40}$/;
const sha=x=>createHash('sha256').update(x).digest('hex');
const ensure=(ok,code)=>{if(!ok)throw Error(code);};
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
  Object.getPrototypeOf(x)===Object.prototype;

function checkedText(bytes,max,reason){
  ensure(Buffer.isBuffer(bytes)&&bytes.length>0&&bytes.length<=max,reason);
  const str=bytes.toString('utf8').trim();
  ensure(str.length>0&&!/[\x00-\x08\x0b-\x1f\x7f]/u.test(str),reason);
  return str;
}

function checkedManifest(bytes){
  const raw=checkedText(bytes,128*1024,'INVALID_RESOLVED_LAKE_MANIFEST');
  let doc;
  try{doc=JSON.parse(raw);}catch{throw Error('INVALID_RESOLVED_LAKE_MANIFEST');}
  ensure(plain(doc)&&/^\d+\.\d+\.\d+$/.test(doc.version??'')&&
    doc.packagesDir==='.lake/packages'&&Array.isArray(doc.packages)&&
    doc.packages.length>0&&doc.packages.length<=64,
  'INVALID_RESOLVED_LAKE_MANIFEST');
  const seen=new Set();
  const deps=[];
  for(const p of doc.packages){
    ensure(plain(p)&&typeof p.name==='string'&&
      /^[A-Za-z0-9_-]{1,80}$/.test(p.name)&&!seen.has(p.name)&&
      p.type==='git'&&SHA40.test(p.rev??'')&&
      typeof p.inputRev==='string'&&p.inputRev.length>0&&p.inputRev.length<=100&&
      typeof p.url==='string'&&
      /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\.git)?$/.test(p.url),
    'INVALID_RESOLVED_LAKE_MANIFEST');
    seen.add(p.name);
    deps.push({name:p.name,rev:p.rev});
  }
  const mathlib=doc.packages.find(p=>p.name==='mathlib');
  ensure(mathlib?.inputRev===ARTIN_PIN.targetMathlib&&
    mathlib.rev===MATHLIB_428_COMMIT&&
    mathlib.url.replace(/\.git$/,'')==='https://github.com/leanprover-community/mathlib4',
  'INVALID_RESOLVED_LAKE_MANIFEST');
  deps.sort((a,b)=>a.name.localeCompare(b.name));
  return deps;
}

export function makeArtinEnvironmentReport({
  manifestBytes,toolchainBytes,leanVersionBytes,lakeVersionBytes,
}={}){
  const dependencies=checkedManifest(manifestBytes);
  const toolchain=checkedText(toolchainBytes,100,'INVALID_PINNED_LEAN_ENVIRONMENT');
  const leanVersion=checkedText(leanVersionBytes,4096,'INVALID_PINNED_LEAN_ENVIRONMENT');
  const lakeVersion=checkedText(lakeVersionBytes,4096,'INVALID_PINNED_LEAN_ENVIRONMENT');
  ensure(toolchain===ARTIN_PIN.targetLean&&
    /^Lean \(version 4\.28\.0[,)]/u.test(leanVersion)&&
    /^Lake version /u.test(lakeVersion),
  'INVALID_PINNED_LEAN_ENVIRONMENT');
  const identity={schema:'mathgraph.artin-resolved-environment-identity.v1',
    theorem:ARTIN_PIN.theorem,requested_lean:ARTIN_PIN.targetLean,
    requested_mathlib:ARTIN_PIN.targetMathlib,
    toolchain_sha256:sha(toolchainBytes),manifest_sha256:sha(manifestBytes),
    lean_version:leanVersion,lake_version:lakeVersion,
    mathlib_revision:MATHLIB_428_COMMIT,resolved_dependencies:dependencies};
  return {...identity,schema:'mathgraph.artin-resolved-environment.v1',
    environment_sha256:sha(JSON.stringify(identity)),
    resolved_dependency_count:dependencies.length,
    native_lean_replay:'WORKFLOW_SUCCESS_STILL_REQUIRED',
    qualified_human_review:'UNKNOWN',intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY'};
}

/** Correlate five independently ZIP-digested machine files, no native claim. */
export function verifyPinnedArtinEnvironmentArtifactBytes({zipBytes,artifactDigest}={}){
  ensure(typeof artifactDigest==='string'&&/^sha256:[a-f0-9]{64}$/.test(artifactDigest),
    'INVALID_ENVIRONMENT_ARTIFACT_DIGEST');
  ensure(Buffer.isBuffer(zipBytes)&&'sha256:'+sha(zipBytes)===artifactDigest,
    'ENVIRONMENT_ARTIFACT_DIGEST_MISMATCH');
  const files=readStrictEvidenceZip(zipBytes,ARTIN_ENVIRONMENT_MEMBERS);
  const expected=makeArtinEnvironmentReport({
    manifestBytes:files.get('lake-manifest.json'),
    toolchainBytes:files.get('artin-toolchain.txt'),
    leanVersionBytes:files.get('artin-lean-version.txt'),
    lakeVersionBytes:files.get('artin-lake-version.txt'),
  });
  let report;
  try{report=JSON.parse(files.get('artin-environment.json').toString('utf8'));}
  catch{throw Error('ENVIRONMENT_REPORT_MISMATCH');}
  ensure(plain(report)&&JSON.stringify(report)===JSON.stringify(expected),
    'ENVIRONMENT_REPORT_MISMATCH');
  return {schema:'mathgraph.artin-environment-bytes.v1',
    status:'ENVIRONMENT_MANIFEST_BYTES_PINNED',
    archive_sha256:sha(zipBytes),
    manifest_sha256:expected.manifest_sha256,
    environment_sha256:expected.environment_sha256,
    toolchain_sha256:expected.toolchain_sha256,
    mathlib_revision:expected.mathlib_revision,
    resolved_dependency_count:expected.resolved_dependency_count,
    resolved_dependencies:expected.resolved_dependencies,
    native_replay:'WORKFLOW_SUCCESS_STILL_REQUIRED',
    source_review:'UNKNOWN',receipt_qualification:'NOT_YET_CONTRACT_BOUND',
    intent_verification:'NOT_ESTABLISHED',permission:'ADVISORY_ONLY'};
}

// The native workflow runs this script after Lake dependency resolution.
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  try{
    if(process.argv.length!==6)throw Error('USAGE: environment MODULE MANIFEST TOOLCHAIN LEAN_VERSION LAKE_VERSION');
    const [, ,manifest,toolchain,leanVersion,lakeVersion]=process.argv;
    process.stdout.write(JSON.stringify(makeArtinEnvironmentReport({
      manifestBytes:readFileSync(manifest),toolchainBytes:readFileSync(toolchain),
      leanVersionBytes:readFileSync(leanVersion),lakeVersionBytes:readFileSync(lakeVersion),
    }),null,2)+'\n');
  }catch(e){process.stderr.write(/^[A-Z_]+$/.test(e.message)?e.message:'ENVIRONMENT_CHECK_FAILED');
    process.exitCode=1;}
}
