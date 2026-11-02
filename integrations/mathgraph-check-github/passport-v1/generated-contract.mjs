import {GENERATED_PINS} from './generated-pins.mjs';
const requireEvidence=(ok,code)=>{if(!ok)throw Error(code);};
const ORIGINAL='219f133cc93172fea46b08d09edf9b3b6441c0a4';
const PACKAGED='fba155bf31918f9b03394ae9bfb8cd17c91ecfb8';
const IDS=['compact_shell_operator','assignment_argument','pytest_directory_boundary'];
export function assessGeneratedSource(o,now=Date.now()) {
  const unknown={status:'UNKNOWN',head:null,checkedAt:null};
  if(!o||o.repository!=='metalogiclabs/L4YAML'||o.number!==2||!['open','closed'].includes(o.state)||!(/^[a-f0-9]{40}$/).test(o.head))return unknown;
  const time=Date.parse(o.checked_at);
  if(!Number.isFinite(time)||time>now+10000||now-time>300000)return unknown;
  return {status:o.state==='closed'?'SOURCE_CLOSED':o.head===PACKAGED?'MATCHES_OBSERVED_HEAD':'SOURCE_MOVED',head:o.head,checkedAt:new Date(time).toISOString()};
}
export async function verifyGenerated({files,hash,pins=GENERATED_PINS}) {
  requireEvidence(files&&typeof files==='object'&&typeof hash==='function','INPUT_REFUSED');
  requireEvidence(pins?.schema===GENERATED_PINS.schema&&pins.archive_sha256===GENERATED_PINS.archive_sha256&&Object.keys(pins.digests??{}).length===Object.keys(GENERATED_PINS.digests).length&&Object.entries(GENERATED_PINS.digests).every(([name,d])=>pins.digests[name]===d),'MANIFEST_CHANGED');
  const names=Object.keys(GENERATED_PINS.digests);
  requireEvidence(Object.keys(files).length===names.length&&names.every(n=>Object.hasOwn(files,n)),'FILE_SET_CHANGED');
  for(const name of names){requireEvidence(typeof files[name]==='string'&&files[name].length<100000,'FILE_REFUSED');requireEvidence(await hash(files[name])===GENERATED_PINS.digests[name],'DIGEST_MISMATCH');}
  const read=name=>JSON.parse(files[name]);
  const a=read('revision/assessment.json'),n=read('revision/native-repair.json'),p=read('packaged/assessment.json'),pn=read('packaged/native.json'),plan=read('revision/plan.json'),first=read('attempt1/assessment.json'),firstNative=read('attempt1/native-repair.json'),origin=read('packaged/origin-receipt.json');
  requireEvidence(a.context.run_id===41520661597&&a.context.verifier_sha==='dd69fa8b6f25a9e5526896841f5f6b6154c9f59b'&&p.context.run_id===41522396688&&p.context.verifier_sha==='8ae82b8727ee336fbafad0d63f461c3d188a3cdc','IDENTITY_REFUSED');
  requireEvidence(a.subject.repository==='metalogiclabs/L4YAML'&&a.subject.head_sha===ORIGINAL&&p.subject.head_sha===PACKAGED&&a.meaning==='UNVERIFIED'&&p.meaning==='UNVERIFIED'&&a.permission==='ADVISORY_ONLY'&&p.permission==='ADVISORY_ONLY','SCOPE_REFUSED');
  requireEvidence(a.repair.status==='PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'&&a.repair.protected_guards===157&&p.source_guard_count===160&&plan.tests.length===3,'CONTRACT_REFUSED');
  requireEvidence(n.context.run_id===a.context.run_id&&n.context.verifier_sha===a.context.verifier_sha&&n.source_sha===ORIGINAL&&pn.source_sha===PACKAGED&&pn.context.run_id===p.context.run_id&&pn.context.verifier_sha===p.context.verifier_sha&&n.test_digest===pn.test_digest,'IDENTITY_REFUSED');
  const expectedDigest=n.test_digest;
  requireEvidence(await hash(JSON.stringify(plan.tests))===expectedDigest,'PROBE_BINDING_REFUSED');
  for(const [arm,exit]of [[n.original,1],[n.repaired,0],[n.withdrawn,1],[pn.arm,0]]){
    requireEvidence(arm.build_exit===0&&arm.repository_gate_exit===0&&arm.probes.length===3&&arm.controls.pass.exit_code===0&&arm.controls.fail.exit_code===1&&arm.controls.fail.guard_false===true&&arm.controls.fail.other_errors===false,'NATIVE_GATE_REFUSED');
    for(const id of IDS){const rows=arm.probes.filter(x=>x.id===id),original=n.original.probes.find(x=>x.id===id);requireEvidence(rows.length===1&&rows[0].exit_code===exit&&rows[0].guard_false===(exit===1)&&rows[0].other_errors===false&&rows[0].test_file_sha256===original.test_file_sha256,'NATIVE_PROBE_REFUSED');}
  }
  requireEvidence(n.original.source_sha256===a.subject.source_sha256&&n.withdrawn.source_sha256===n.original.source_sha256&&n.repaired.source_sha256===a.repair.patched_sha256&&pn.arm.source_sha256===p.subject.source_sha256&&origin.implementation_sha256===n.repaired.source_sha256&&origin.packaged_source_sha256===pn.arm.source_sha256&&origin.implementation_changed===false&&origin.generated_guards_embedded===3,'SOURCE_BINDING_REFUSED');
  requireEvidence(first.repair.status==='UNKNOWN'&&firstNative.repaired.build_exit!==0,'FAILED_ATTEMPT_MISSING');
  const published=read('packaged/published-check.json');requireEvidence(published.app==='mathgraph-check'&&published.id===125542085622&&published.head_sha===p.context.verifier_sha,'PUBLISHER_REFUSED');
  return {historical:'FROZEN_CHECKS_PASSED',meaning:'UNVERIFIED',permission:'ADVISORY_ONLY',firstRepair:'UNKNOWN',checks:plan.tests,protectedGuards:157,packagedGuards:160,original:ORIGINAL,packaged:PACKAGED,assessment:a,packageAssessment:p,native:n,firstNative,filesChecked:names.length,digests:GENERATED_PINS.digests};
}
