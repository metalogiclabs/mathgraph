import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {runBraheCliV1} from './brahe-cli-v1.mjs';

const guard='if !crossed && current_crossing.abs() > detector.value_tolerance() {';
const fixed='let near_target_in_direction = current_crossing.abs() <= detector.value_tolerance()';
const marker='#[cfg(test)]\nmod tests {';

test('CLI physically transplants only the head test module, retaining the base implementation',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'brahe-test-'));
  const base=join(dir,'base.rs'),head=join(dir,'head.rs'),manifest=join(dir,'manifest.json');
  const baseCode=`${guard}\n${guard}\n`;
  const headTests=`${marker}\n#[test] fn regression() {}\n}\n`;
  await writeFile(base,baseCode+marker+'\n}\n');
  await writeFile(head,`${fixed}\n${fixed}\n${headTests}`);
  const outcome=await runBraheCliV1(['--mode','transplant','--base',base,'--head',head,'--manifest',manifest]);
  assert.equal(await readFile(base,'utf8'),baseCode+headTests);
  assert.equal(outcome.patchedBaseSource,undefined);
  assert.equal(JSON.parse(await readFile(manifest,'utf8')).source.repository,'duncaneddy/brahe');
});

test('CLI reads actual raw log files and rejects duplicate arguments',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'brahe-receipt-'));
  const stdout=join(dir,'out'),stderr=join(dir,'err'),out=join(dir,'receipt.json');
  await writeFile(stdout,'running 0 tests\n');await writeFile(stderr,'');
  const receipt=await runBraheCliV1(['--mode','base','--exit','101','--source-sha','323c4542ad915aa1b6a1dbf65f1f6a8040609294','--stdout',stdout,'--stderr',stderr,'--out',out]);
  assert.equal(receipt.reason,'ZERO_TESTS');
  assert.equal(JSON.parse(await readFile(out,'utf8')).reason,'ZERO_TESTS');
  await assert.rejects(()=>runBraheCliV1(['--mode','base','--mode','head']),/INVALID_ARGUMENT/);
});
