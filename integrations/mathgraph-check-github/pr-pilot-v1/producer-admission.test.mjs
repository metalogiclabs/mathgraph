import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
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
});
