import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const CLI=new URL('./run-math-source-environment-collector-v1.mjs',import.meta.url).pathname;
function run(content,token){
  const dir=mkdtempSync(join(tmpdir(),'mathgraph-env-cli-'));
  try{
    const path=join(dir,'config.json');writeFileSync(path,content);
    return spawnSync(process.execPath,[CLI,path],{encoding:'utf8',timeout:5000,
      env:{...process.env,MATHGRAPH_GITHUB_APP_TOKEN:token}});
  }finally{rmSync(dir,{recursive:true,force:true});}
}
test('V2 app job will never run without its own scoped installation token',()=>{
  const r=run('{}','');
  assert.equal(r.status,2);
  assert.equal(r.stdout,'');
  assert.match(r.stderr,/MISSING_INSTALLATION_TOKEN/);
});
test('V2 app job rejects invalid or V1 admin scope and prints no secret',()=>{
  for(const body of ['{oops}',JSON.stringify({repository:'metalogiclabs/mathgraph',
    pr:228,runId:41356752114,trusted:{workflowPath:
    '.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml'}})]){
    const r=run(body,'temporary-installation-token-not-printed');
    assert.equal(r.status,2);
    assert.equal(r.stdout,'');
    assert.match(r.stderr,/INVALID_V2_ADMIN_MANIFEST/);
    assert.doesNotMatch(r.stderr,/temporary-installation-token-not-printed|config.json/);
  }
});
