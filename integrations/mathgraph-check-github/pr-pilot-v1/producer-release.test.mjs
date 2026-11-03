import test from 'node:test';import assert from 'node:assert/strict';
import {producerRelease} from './producer-admission.mjs';
test('historical release is explicit; current release requires actual execution context',()=>{
 assert.equal(producerRelease({head_sha:'a6651de78193d70bbb72e59e868670e675981bf4'}),'0ffe73933f3ea6b505c4862e43e0280d0160eacc');
 assert.equal(producerRelease({head_sha:'24bf74d5f2feaa398763b0e5a7aef77c05bf6966'}),'5fb0effff54763acbedc422857ba0b6c708265af');
 const run={head_sha:'a'.repeat(40)},context={scheduler_sha:'a'.repeat(40),verifier_sha:'b'.repeat(40)};
 assert.equal(producerRelease(run,context),context.verifier_sha);
 assert.throws(()=>producerRelease(run));assert.throws(()=>producerRelease(run,{...context,scheduler_sha:'c'.repeat(40)}));
});
