/**
 * Exact-artifact preflight for the independently published ProofNet-Verified
 * Artin example. A successful preflight is NOT a Lean replay, human review,
 * mathematical equivalence certificate, or qualified MathGraph Check receipt.
 *
 * The gold proof is read directly from the upstream zip at runtime; it is
 * deliberately not checked in here or printed to logs.
 */
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {inflateRawSync} from 'node:zlib';

export const ARTIN_PIN=Object.freeze({
  repository:'marcusm117/ProofNet-Verified',
  commit:'14879cb23e078d122adecd9578dd26a7304f753b',
  theorem:'Artin_exercise_2_2_9',
  sourcePath:'data/archive/proofnet-verified-4.28/proofnet-1.lean',
  jsonlPath:'data/archive/proofnet-verified-4.28.jsonl',
  zipPath:'data/archive/proofnet-verified_gt-4.28.zip',
  zipMember:'proofnet_verified_gt/proofnet-1.lean',
  sourceSha256:'a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc',
  formalSha256:'dc80af468161394ffc1415b4e1ff0585b6859dc80198abb6d2c7d4439888262b',
  zipSha256:'e1cf0e5eb34ca13067efb61365a1b8c534e140eb02518e5a7801dac1fce79445',
  goldSha256:'84abeb60969d2c4a8aa3483806e2d71cb2d762e49fd855e7953770b5fbabbc0d',
  targetLean:'leanprover/lean4:v4.28.0',
  targetMathlib:'v4.28.0',
});

const sha=x=>createHash('sha256').update(x).digest('hex');
const requireEq=(actual,expected,code)=>{
  if(actual!==expected)throw Error(code);
};

/** Read one named ZIP member. The entire archive is SHA-pinned first. */
function zipMember(bytes,member){
  let end=-1;
  for(let p=bytes.length-22;p>=Math.max(0,bytes.length-65557);p--){
    if(bytes.readUInt32LE(p)===0x06054b50){end=p;break;}
  }
  if(end<0)throw Error('INVALID_GOLD_ARCHIVE');
  const entries=bytes.readUInt16LE(end+10);
  let p=bytes.readUInt32LE(end+16);
  for(let i=0;i<entries;i++){
    if(bytes.readUInt32LE(p)!==0x02014b50)throw Error('INVALID_GOLD_ARCHIVE');
    const method=bytes.readUInt16LE(p+10);
    const compressedSize=bytes.readUInt32LE(p+20);
    const size=bytes.readUInt32LE(p+24);
    const nameLength=bytes.readUInt16LE(p+28);
    const extraLength=bytes.readUInt16LE(p+30);
    const commentLength=bytes.readUInt16LE(p+32);
    const localOffset=bytes.readUInt32LE(p+42);
    const name=bytes.subarray(p+46,p+46+nameLength).toString('utf8');
    if(name===member){
      if(bytes.readUInt32LE(localOffset)!==0x04034b50)
        throw Error('INVALID_GOLD_ARCHIVE');
      const start=localOffset+30+bytes.readUInt16LE(localOffset+26)+
        bytes.readUInt16LE(localOffset+28);
      const raw=bytes.subarray(start,start+compressedSize);
      const unpacked=method===0?raw:method===8?inflateRawSync(raw):null;
      if(!unpacked||unpacked.length!==size)throw Error('INVALID_GOLD_ARCHIVE');
      return unpacked.toString('utf8');
    }
    p+=46+nameLength+extraLength+commentLength;
  }
  throw Error('MISSING_GOLD_PROOF_MEMBER');
}

export function preflightArtinFixture(root,options={}){
  const dir=resolve(root);
  // Only the caller can authenticate a git commit; this function does not
  // infer trust from a local .git directory or from the data's own claims.
  requireEq(options.observedCommit,ARTIN_PIN.commit,'UNPINNED_UPSTREAM_COMMIT');

  const source=readFileSync(join(dir,ARTIN_PIN.sourcePath));
  const zipPath=join(dir,ARTIN_PIN.zipPath);
  const archive=readFileSync(zipPath);
  requireEq(sha(source),ARTIN_PIN.sourceSha256,'SOURCE_BYTES_CHANGED');
  requireEq(sha(archive),ARTIN_PIN.zipSha256,'GOLD_ARCHIVE_CHANGED');

  const firstLine=readFileSync(join(dir,ARTIN_PIN.jsonlPath),'utf8').split('\n',1)[0];
  const entry=JSON.parse(firstLine);
  requireEq(entry.index,1,'WRONG_DATASET_INDEX');
  requireEq(entry.name,ARTIN_PIN.theorem,'WRONG_DATASET_THEOREM');
  requireEq(sha(entry.formal_stmt),ARTIN_PIN.formalSha256,'FORMAL_STATEMENT_CHANGED');
  const sourceText=source.toString('utf8');
  if(!sourceText.includes(entry.formal_stmt))throw Error('SOURCE_STATEMENT_DISAGREES');

  const gold=zipMember(archive,ARTIN_PIN.zipMember);
  requireEq(sha(gold),ARTIN_PIN.goldSha256,'GOLD_PROOF_CHANGED');
  const head=entry.formal_stmt.replace(/:= by\s+sorry\s*$/u,':= by');
  if(head===entry.formal_stmt||!gold.includes(head))
    throw Error('GOLD_STATEMENT_DISAGREES');
  if(/\bsorry\b|\badmit\b/u.test(gold))
    throw Error('GOLD_PROOF_HAS_UNRESOLVED_PLACEHOLDER');

  if(options.extractPath){
    // The caller chooses a single file path in its isolated working directory.
    // No recursive extraction of the upstream zip is ever performed.
    writeFileSync(resolve(options.extractPath),gold,{flag:'wx',mode:0o600});
  }

  return {
    schema:'mathgraph.proofnet-artin-preflight.v1',
    upstream:{repository:ARTIN_PIN.repository,commit:ARTIN_PIN.commit},
    theorem:ARTIN_PIN.theorem,
    source_sha256:sha(source),
    claim_sha256:sha(entry.informal_stmt),
    statement_sha256:sha(entry.formal_stmt),
    gold_archive_sha256:sha(archive),
    gold_proof_sha256:sha(gold),
    requested_lean:ARTIN_PIN.targetLean,
    requested_mathlib:ARTIN_PIN.targetMathlib,
    artifact_preflight:'PINNED_GOLD_PROOF_IDENTIFIED',
    native_lean_replay:'NOT_RUN',
    qualified_human_review:'UNKNOWN',
    intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY',
  };
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  try{
    const [, ,dir,extract]=process.argv;
    if(!dir||process.argv.length>4)throw Error('USAGE: node proofnet-artin-replay-v1.mjs UPSTREAM_DIR [EXTRACT_PATH]');
    process.stdout.write(JSON.stringify(preflightArtinFixture(dir,{
      observedCommit:process.env.PROOFNET_OBSERVED_COMMIT,extractPath:extract,
    }),null,2)+'\n');
  }catch(error){
    process.stderr.write(String(error.message)+'\n');
    process.exitCode=1;
  }
}
