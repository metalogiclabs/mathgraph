/**
 * Bounded byte-level checks for the archived ProofNet-Verified Artin example.
 *
 * Callers MUST acquire the GitHub artifact digest independently from the
 * authenticated artifact API and acquire upstream bytes from the exact Git
 * commit. These pure functions do not authenticate their caller, run Lean,
 * verify mathematical meaning, or mint MathGraph intent-probes receipts.
 */
import {createHash} from 'node:crypto';
import {inflateRawSync} from 'node:zlib';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';

const CLAIM_SHA256='a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0';
const ARCHIVE_MAX=2*1024*1024;
const MEMBER_MAX=128*1024;
const JSON_MAX=32*1024;
const FILES=new Set(['artin-preflight.json','artin-axiom-audit.json']);
const sha=x=>createHash('sha256').update(x).digest('hex');
const requireFact=(v,reason)=>{if(!v)throw Error(reason);};
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
  (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const exactKeys=(x,keys)=>plain(x)&&Object.keys(x).length===keys.length&&
  keys.every(k=>Object.hasOwn(x,k));
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const crc32=bytes=>{
  let c=0xffffffff;
  for(const b of bytes){c^=b;for(let i=0;i<8;i++)
    c=(c>>>1)^((c&1)?0xedb88320:0);}
  return (c^0xffffffff)>>>0;
};

function unzipEvidence(bytes){
  requireFact(Buffer.isBuffer(bytes)&&bytes.length>=22&&bytes.length<=ARCHIVE_MAX,
    'ARTIFACT_ZIP_SIZE_INVALID');
  const endMin=Math.max(0,bytes.length-65557);
  let end=-1;
  for(let p=bytes.length-22;p>=endMin;p--){
    if(bytes.readUInt32LE(p)===0x06054b50&&
      p+22+bytes.readUInt16LE(p+20)===bytes.length){end=p;break;}
  }
  requireFact(end>=0,'ARTIFACT_ZIP_END_MISSING');
  const count=bytes.readUInt16LE(end+10),directorySize=bytes.readUInt32LE(end+12);
  const directoryOffset=bytes.readUInt32LE(end+16);
  requireFact(bytes.readUInt16LE(end+4)===0&&bytes.readUInt16LE(end+6)===0&&
    bytes.readUInt16LE(end+8)===count&&count===2&&
    directoryOffset!==0xffffffff&&directorySize!==0xffffffff&&
    directoryOffset+directorySize===end&&directoryOffset<=end,
  'ARTIFACT_ZIP_DIRECTORY_INVALID');

  const names=new Set(),items=new Map();
  let cursor=directoryOffset;
  const bounds=[];
  for(let i=0;i<count;i++){
    requireFact(cursor+46<=end&&bytes.readUInt32LE(cursor)===0x02014b50,
      'ARTIFACT_ZIP_ENTRY_INVALID');
    const madeBy=bytes.readUInt16LE(cursor+4),flags=bytes.readUInt16LE(cursor+8);
    const method=bytes.readUInt16LE(cursor+10);
    const crc=bytes.readUInt32LE(cursor+16);
    const compressed=bytes.readUInt32LE(cursor+20),size=bytes.readUInt32LE(cursor+24);
    const nameLength=bytes.readUInt16LE(cursor+28);
    const extraLength=bytes.readUInt16LE(cursor+30);
    const commentLength=bytes.readUInt16LE(cursor+32);
    const external=bytes.readUInt32LE(cursor+38);
    const localOffset=bytes.readUInt32LE(cursor+42);
    const next=cursor+46+nameLength+extraLength+commentLength;
    requireFact(next<=end&&nameLength>0&&nameLength<80&&
      compressed<=ARCHIVE_MAX&&size<=MEMBER_MAX&&
      localOffset!==0xffffffff&&compressed!==0xffffffff&&size!==0xffffffff&&
      (flags&~(0x0008|0x0800))===0&&[0,8].includes(method)&&
      // A symlink can redirect extraction in consumers that ignore names.
      ((madeBy>>>8)!==3||(external>>>16&0xf000)!==0xa000),
    'ARTIFACT_ZIP_ENTRY_UNSAFE');
    const name=bytes.subarray(cursor+46,cursor+46+nameLength).toString('utf8');
    requireFact(FILES.has(name)&&!names.has(name),'ARTIFACT_ZIP_FILE_SET_INVALID');
    names.add(name);
    requireFact(localOffset+30<=directoryOffset&&
      bytes.readUInt32LE(localOffset)===0x04034b50,
    'ARTIFACT_ZIP_LOCAL_HEADER_INVALID');
    const localFlags=bytes.readUInt16LE(localOffset+6);
    const localNameSize=bytes.readUInt16LE(localOffset+26);
    const localExtraSize=bytes.readUInt16LE(localOffset+28);
    const rawOffset=localOffset+30+localNameSize+localExtraSize;
    const rawEnd=rawOffset+compressed;
    requireFact(localFlags===flags&&bytes.readUInt16LE(localOffset+8)===method&&
      localNameSize===nameLength&&
      rawEnd<=directoryOffset&&
      bytes.subarray(localOffset+30,localOffset+30+localNameSize).equals(
        bytes.subarray(cursor+46,cursor+46+nameLength))&&
      ((flags&0x0008)!==0||(
        bytes.readUInt32LE(localOffset+14)===crc&&
        bytes.readUInt32LE(localOffset+18)===compressed&&
        bytes.readUInt32LE(localOffset+22)===size)),
    'ARTIFACT_ZIP_LOCAL_HEADER_MISMATCH');
    bounds.push([localOffset,rawEnd]);
    let unpacked;
    const raw=bytes.subarray(rawOffset,rawEnd);
    try{unpacked=method===0?raw:inflateRawSync(raw,{maxOutputLength:MEMBER_MAX+1});}
    catch{throw Error('ARTIFACT_ZIP_DECOMPRESSION_FAILED');}
    requireFact(unpacked.length===size&&crc32(unpacked)===crc,
      'ARTIFACT_ZIP_DATA_MISMATCH');
    items.set(name,unpacked);
    cursor=next;
  }
  bounds.sort((a,b)=>a[0]-b[0]);
  requireFact(cursor===end&&names.size===2&&
    bounds.every(([start,stop],i)=>start>=0&&stop<=directoryOffset&&
      (i===0||start>=bounds[i-1][1])),
  'ARTIFACT_ZIP_STRUCTURE_INVALID');
  return items;
}

function parseReport(bytes,reason){
  requireFact(bytes.length<=JSON_MAX,reason);
  let value;
  try{value=JSON.parse(bytes.toString('utf8'));}catch{throw Error(reason);}
  requireFact(plain(value),reason);
  return value;
}

function validatePreflight(p){
  const expected={
    schema:'mathgraph.proofnet-artin-preflight.v1',
    upstream:{repository:ARTIN_PIN.repository,commit:ARTIN_PIN.commit},
    theorem:ARTIN_PIN.theorem,source_sha256:ARTIN_PIN.sourceSha256,
    claim_sha256:CLAIM_SHA256,statement_sha256:ARTIN_PIN.formalSha256,
    gold_archive_sha256:ARTIN_PIN.zipSha256,gold_proof_sha256:ARTIN_PIN.goldSha256,
    requested_lean:ARTIN_PIN.targetLean,requested_mathlib:ARTIN_PIN.targetMathlib,
    artifact_preflight:'PINNED_GOLD_PROOF_IDENTIFIED',native_lean_replay:'NOT_RUN',
    qualified_human_review:'UNKNOWN',intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY',
  };
  requireFact(exactKeys(p,Object.keys(expected))&&eq(p,expected),
    'ARTIFACT_PREFLIGHT_MISMATCH');
}

function validateAudit(a){
  const expected={schema:'mathgraph.artin-axiom-audit.v1',
    theorem:ARTIN_PIN.theorem,
    allowed_axioms:['propext','Classical.choice','Quot.sound'],
    observed_axioms:['propext','Classical.choice','Quot.sound'],
    verdict:'AXIOMS_WITHIN_CLASSICAL_LEAN_ALLOWLIST',
    source_review:'UNKNOWN',intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY'};
  requireFact(exactKeys(a,Object.keys(expected))&&eq(a,expected),
    'ARTIFACT_AXIOM_AUDIT_MISMATCH');
}

/** Confirm what an independently digest-pinned GitHub artifact ZIP says. */
export function verifyPinnedArtinArtifactBytes({zipBytes,artifactDigest}={}){
  requireFact(typeof artifactDigest==='string'&&
    /^sha256:[a-f0-9]{64}$/.test(artifactDigest),
  'INVALID_INDEPENDENT_ARTIFACT_DIGEST');
  requireFact(Buffer.isBuffer(zipBytes)&&
    'sha256:'+sha(zipBytes)===artifactDigest,'ARTIFACT_DIGEST_MISMATCH');
  const entries=unzipEvidence(zipBytes);
  validatePreflight(parseReport(entries.get('artin-preflight.json'),
    'ARTIFACT_PREFLIGHT_MISMATCH'));
  validateAudit(parseReport(entries.get('artin-axiom-audit.json'),
    'ARTIFACT_AXIOM_AUDIT_MISMATCH'));
  return {schema:'mathgraph.artin-evidence-bytes.v1',status:'ARTIFACT_BYTES_PINNED',
    archive_sha256:sha(zipBytes),source_sha256:ARTIN_PIN.sourceSha256,
    claim_sha256:CLAIM_SHA256,statement_sha256:ARTIN_PIN.formalSha256,
    native_replay:'WORKFLOW_SUCCESS_STILL_REQUIRED',source_review:'UNKNOWN',
    receipt_qualification:'NOT_YET_CONTRACT_BOUND',intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY'};
}

/**
 * Verify source and first JSONL theorem at the caller-authenticated git SHA.
 * Caller MUST pin repository, paths and commit outside untrusted PR content.
 */
export function verifyPinnedArtinUpstreamBytes({observedCommit,sourceBytes,jsonlBytes}={}){
  requireFact(observedCommit===ARTIN_PIN.commit,'UNPINNED_UPSTREAM_COMMIT');
  requireFact(Buffer.isBuffer(sourceBytes)&&
    sha(sourceBytes)===ARTIN_PIN.sourceSha256,'UPSTREAM_SOURCE_BYTES_CHANGED');
  requireFact(Buffer.isBuffer(jsonlBytes)&&jsonlBytes.length<=4*1024*1024,
    'UPSTREAM_DATASET_TOO_LARGE');
  const first=jsonlBytes.toString('utf8').split('\n',1)[0];
  let entry;
  try{entry=JSON.parse(first);}catch{throw Error('UPSTREAM_DATASET_INVALID');}
  requireFact(plain(entry)&&entry.index===1&&entry.name===ARTIN_PIN.theorem&&
    typeof entry.informal_stmt==='string'&&typeof entry.formal_stmt==='string',
  'UPSTREAM_DATASET_THEOREM_MISMATCH');
  requireFact(sha(entry.informal_stmt)===CLAIM_SHA256,
    'UPSTREAM_CLAIM_CHANGED');
  requireFact(sha(entry.formal_stmt)===ARTIN_PIN.formalSha256&&
    sourceBytes.toString('utf8').includes(entry.formal_stmt),
  'UPSTREAM_STATEMENT_CHANGED');
  return {schema:'mathgraph.artin-upstream-bytes.v1',status:'UPSTREAM_SOURCE_BYTES_PINNED',
    upstream:{repository:ARTIN_PIN.repository,commit:ARTIN_PIN.commit},
    source_sha256:ARTIN_PIN.sourceSha256,claim_sha256:CLAIM_SHA256,
    statement_sha256:ARTIN_PIN.formalSha256,
    source_review:'UNKNOWN',receipt_qualification:'NOT_YET_CONTRACT_BOUND',
    intent_verification:'NOT_ESTABLISHED',permission:'ADVISORY_ONLY'};
}
