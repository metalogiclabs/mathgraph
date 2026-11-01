import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const CLI=new URL('./run-math-source-evidence-collector-v1.mjs',import.meta.url).pathname;

function invoke(content,token){
  const dir=mkdtempSync(join(tmpdir(),'mathgraph-collector-cli-'));
  try{
    const file=join(dir,'trusted.json');
    writeFileSync(file,content);
    return spawnSync(process.execPath,[CLI,file],{encoding:'utf8',timeout:5000,
      env:{...process.env,MATHGRAPH_GITHUB_APP_TOKEN:token}});
  }finally{rmSync(dir,{recursive:true,force:true});}
}

test('a missing installation token is rejected before network access or evidence claims',()=>{
  const result=invoke('{"repository":"metalogiclabs/mathgraph"}','');
  assert.equal(result.status,2);
  assert.equal(result.stdout,'');
  assert.match(result.stderr,/MISSING_INSTALLATION_TOKEN/);
  assert.doesNotMatch(result.stderr,/https:|PRIVATE_KEY|proofnet/i);
});

test('invalid administrator manifest is rejected without printing secrets or paths',()=>{
  for(const content of ['{bad-json}',JSON.stringify({repository:'evil/repo'}),
    JSON.stringify({repository:'metalogiclabs/mathgraph',pr:0,runId:12,trusted:{}})]){
    const result=invoke(content,'scoped-token-should-never-be-logged');
    assert.equal(result.status,2);
    assert.equal(result.stdout,'');
    assert.match(result.stderr,/INVALID_ADMIN_MANIFEST/);
    assert.doesNotMatch(result.stderr,/scoped-token-should-never-be-logged|trusted.json/);
  }
});

test('CLI rejects missing manifest path with bounded no-credential output',()=>{
  const result=spawnSync(process.execPath,[CLI],{encoding:'utf8',timeout:5000,
    env:{...process.env,MATHGRAPH_GITHUB_APP_TOKEN:'scoped-token-should-never-be-logged'}});
  assert.equal(result.status,2);
  assert.equal(result.stdout,'');
  assert.match(result.stderr,/USAGE:.*TRUST_FILE/);
  assert.doesNotMatch(result.stderr,/scoped-token-should-never-be-logged/);
});
