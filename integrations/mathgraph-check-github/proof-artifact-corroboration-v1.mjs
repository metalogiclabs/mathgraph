/**
 * Corroborate *bytes* of a pinned Lean CI artifact, without calling this a
 * fresh kernel replay. The caller MUST obtain `trustedReceipt` from a protected
 * policy and must separately authenticate the GitHub run/job/artifact metadata.
 * Neither a PR-controlled JSON record nor its own SHA-256 is a trust root.
 */
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFileSync,statSync} from 'node:fs';

export const LEAN_ARTIFACT_SCHEMA='mathgraph.lean-artifact-corroboration.v1';
const SHA40=/^[0-9a-f]{40}$/;
const SHA64=/^[0-9a-f]{64}$/;
const NAME=/^[A-Za-z0-9._/-]+$/;
const keys=['repository','commit','run','job','theorem','artifact_sha256',
 'lean_build_commit','expected_theorem_type'];
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
 (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const unknown=reason=>({schema:LEAN_ARTIFACT_SCHEMA,status:'UNKNOWN',reason,
 permission:'ADVISORY_ONLY',proof_replay:'NOT_PERFORMED',
 complete_yaml_grammar:'UNKNOWN',receipt_ref:null});

function validReceipt(p){
 return obj(p)&&Object.keys(p).length===keys.length&&keys.every(k=>Object.hasOwn(p,k))&&
  p.repository==='metalogiclabs/L4YAML'&&SHA40.test(p.commit)&&
  Number.isSafeInteger(p.run)&&p.run>0&&Number.isSafeInteger(p.job)&&p.job>0&&
  typeof p.theorem==='string'&&NAME.test(p.theorem)&&p.theorem.length<180&&
  SHA64.test(p.artifact_sha256)&&SHA40.test(p.lean_build_commit)&&
  typeof p.expected_theorem_type==='string'&&p.expected_theorem_type.length>40&&
  p.expected_theorem_type.length<2000&&p.expected_theorem_type.startsWith(p.theorem+' ');
}

/**
 * Read only a small fixed set of files from the ZIP. No extracted paths are
 * written to disk; no archive entry names are executed as shell commands.
 */
export function corroborateLeanProofArtifact(archivePath,trustedReceipt){
 if(!validReceipt(trustedReceipt))return unknown('TRUSTED_RECEIPT_POLICY_REQUIRED');
 if(typeof archivePath!=='string'||!archivePath||archivePath.length>1024)
  return unknown('ARTIFACT_BYTES_MISSING');
 try{
  const stat=statSync(archivePath);
  if(!stat.isFile()||stat.size<=0||stat.size>16*1024*1024)
   return unknown('ARTIFACT_SIZE_OR_TYPE_INVALID');
  const digest=createHash('sha256').update(readFileSync(archivePath)).digest('hex');
  if(digest!==trustedReceipt.artifact_sha256)
   return unknown('ARTIFACT_BYTES_DIGEST_MISMATCH');
  // Never resolve an executable through PR-controllable PATH or inherit host
  // API tokens and reviewer credentials into the ZIP decoder subprocess.
  const cmd=(args,limit=1024*1024)=>execFileSync('/usr/bin/unzip',args,{
   encoding:'utf8',maxBuffer:limit,timeout:5000,stdio:['ignore','pipe','ignore'],
   env:{PATH:'/usr/bin:/bin',LANG:'C'}});
  const entries=cmd(['-Z1',archivePath],128*1024).trimEnd().split('\n');
  if(entries.length>1000||entries.length!==new Set(entries).size||
    entries.some(s=>s.includes('\\')||s.startsWith('/')||s.split('/').includes('..')))
   return unknown('ARTIFACT_ARCHIVE_STRUCTURE_INVALID');
  const read=entry=>{
   if(!entries.includes(entry))throw Error('missing archive member');
   return cmd(['-p',archivePath,entry]);
  };
  const prefix='directive-evidence/capstone/';
  if(read(prefix+'head.txt').trim()!==trustedReceipt.commit)
   return unknown('ARTIFACT_SOURCE_COMMIT_MISMATCH');
  if(!read(prefix+'lean-version.txt').includes('commit '+trustedReceipt.lean_build_commit+','))
   return unknown('ARTIFACT_LEAN_BUILD_MISMATCH');
  const statuses=read(prefix+'status.tsv');
  const statusRows=statuses.split('\n').filter(Boolean);
  for(const [name,result] of [
   ['CapstoneCommentBoundary','0'],['CapstoneQualification','0'],
   ['DirectiveRed-expected-failure','1']]){
   if(statusRows.filter(s=>s.startsWith(name+'\t')).length!==1||
     !statusRows.includes(name+'\t'+result))
    return unknown('ARTIFACT_PROOF_OR_CONTROL_NOT_QUALIFIED');
  }
  const axiomLine=`${trustedReceipt.theorem}: [propext,\n Classical.choice,\n Quot.sound]`;
  const qlog=read(prefix+'CapstoneQualification.log');
  const qualifiers=qlog.split('\n').filter(s=>s.startsWith(
   'QUALIFIED_AXIOMS '+trustedReceipt.theorem+':'));
  if(qualifiers.length!==1||!qlog.includes(trustedReceipt.expected_theorem_type)||
    !qlog.includes('QUALIFIED_AXIOMS '+axiomLine))
   return unknown('ARTIFACT_THEOREM_TYPE_OR_AXIOMS_MISMATCH');
  const theoremLog=read(prefix+'CapstoneCommentBoundary.log');
  if(!theoremLog.includes(`'${trustedReceipt.theorem}' depends on axioms: [propext,\n Classical.choice,\n Quot.sound]`))
   return unknown('ARTIFACT_KERNEL_AXIOM_LOG_MISMATCH');
  const source=read('research/whole-source/CapstoneCommentBoundary.lean');
  if(!source.includes('lemma no_normative_iff_on_frozen_runtime')||
    !source.includes('def commentInput')||!source.includes('def NoRawSOH')||
    !source.includes('#guard (TokenParser.parseYaml commentInput).isOk'))
   return unknown('ARTIFACT_PROOF_SOURCE_MISMATCH');
  return {schema:LEAN_ARTIFACT_SCHEMA,status:'CORROBORATED',
   permission:'ADVISORY_ONLY',proof_replay:'NOT_PERFORMED',
   evidence_kind:'HISTORICAL_CI_ARTIFACT_BYTES_AND_LOGS',
   complete_yaml_grammar:'UNKNOWN',theorem:trustedReceipt.theorem,
   receipt_ref:`${trustedReceipt.repository}@${trustedReceipt.commit}:run-${trustedReceipt.run}:job-${trustedReceipt.job}:${trustedReceipt.theorem}`,
   artifact_sha256:digest};
 }catch{
  return unknown('ARTIFACT_READING_OR_STRUCTURE_INCOMPLETE');
 }
}
