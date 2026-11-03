import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {admitNativeRecheck} from './native-recheck-producer.mjs';
test('a native status label cannot authorize an expectation set',()=>assert.throws(()=>admitNativeRecheck({status:'WARRANTED_BOUNDED_NATIVE'},{})));
const path=process.env.NATIVE_RECHECK_ENVELOPE;
test('authenticated real native candidate is bound to the exact publication',{skip:!path},()=>{
 const x=JSON.parse(readFileSync(path));assert.equal(admitNativeRecheck(x.envelope,x.request).subject.head_sha,x.request.head_sha);
 for(const mutate of [e=>e.run.head_sha='a'.repeat(40),e=>e.run.conclusion='failure',e=>e.artifact.digest='sha256:'+'b'.repeat(64),e=>e.commit.parents=[],e=>e.comparison.files.push(e.comparison.files[0]),e=>e.source+='\n',e=>e.cli_source+='\n']){const v=structuredClone(x);mutate(v.envelope);assert.throws(()=>admitNativeRecheck(v.envelope,v.request));}
});
