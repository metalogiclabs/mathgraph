import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {admitProducer} from './producer-admission.mjs';
// Supplied by the read-only hosted qualification, never an admission credential.
const path=process.env.PRODUCER_TEST_ENVELOPE;
test('serialized warranted labels cannot admit a producer',()=>{
 assert.throws(()=>admitProducer({status:'WARRANTED_BOUNDED_NATIVE',artifact_sha256:'a'.repeat(64)},{}));
});
test('authenticate real producer, then reject independently changed dependencies',{skip:!path},()=>{
 const original=JSON.parse(readFileSync(path));
 assert.equal(admitProducer(original.envelope,original.request).facts.subject.head_sha,original.request.head_sha);
 for(const mutate of [
  x=>x.envelope.run.conclusion='failure',x=>x.envelope.run.event='push',
  x=>x.envelope.artifact.digest='sha256:'+'a'.repeat(64),
  x=>x.envelope.commit.parents=[],x=>x.envelope.comparison.files.push({...x.envelope.comparison.files[0]}),
  x=>x.request.head_sha='a'.repeat(40),x=>x.request.base_sha='b'.repeat(40),
  x=>x.envelope.source+='\n',x=>x.envelope.cli_source+='\n',
  x=>x.envelope.workflow=x.envelope.workflow.replaceAll('0ffe73933f3ea6b505c4862e43e0280d0160eacc','a'.repeat(40)),
  x=>x.envelope.raw['native-repair.json']=x.envelope.raw['native-repair.json'].replace('"build_exit": 0','"build_exit": 1'),
  x=>x.envelope.check.app.id=1,x=>x.envelope.check.output.summary='self-asserted pass',
 ]){const x=structuredClone(original);mutate(x);assert.throws(()=>admitProducer(x.envelope,x.request));}
 // Reseal deliberately changed JSON to exercise semantic admission, separately
 // from artifact-byte integrity. These fabricated fixtures are never live input.
 for(const [name,mutate]of [
  ['native-repair',o=>o.repaired.controls.pass.exit_code=1],
  ['native-repair',o=>o.repaired.repository_gate_exit=1],
  ['native-repair',o=>o.repaired.probes[0].test_file_sha256='a'.repeat(64)],
  ['native-repair',o=>o.withdrawn.probes[1].exit_code=0],
  ['plan',o=>o.tests[0].contract='Unreviewed replacement requirement'],
  ['expectation-reference',o=>o.reference.records.find(r=>r.Obligation.id==='attached_redirect').Verification.repeat.calls=[]],
 ]){const x=structuredClone(original),raw=x.envelope.raw,n=name+'.json',o=JSON.parse(raw[n]);mutate(o);raw[n]=JSON.stringify(o);const manifest=JSON.parse(raw['manifest.json']);manifest.hashes[n]=createHash('sha256').update(raw[n]).digest('hex');raw['manifest.json']=JSON.stringify(manifest);assert.throws(()=>admitProducer(x.envelope,x.request));}
});
test('final C39 scheduler authenticates its immutable producer independently of current release',async()=>{const {producerRelease}=await import('./producer-admission.mjs');assert.equal(producerRelease({head_sha:'c01dcfdb441cb9c49ba1833a65a2c30972553182'}),'c39d0ec486c90147b080af3ca8e669f933c4aafb');});
