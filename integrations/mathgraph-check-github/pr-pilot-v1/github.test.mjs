import test from 'node:test';
import assert from 'node:assert/strict';
import {githubClient} from './github.mjs';
import {mintScopedToken} from './auth.mjs';
const repo='metalogiclabs/L4YAML';
test('Worker-compatible fetch disables redirect following and rejects redirect responses',async()=>{
 let options;
 const api=githubClient('dummy',{repository:repo,fetcher:async(url,o)=>{options=o;assert.equal(o.redirect,'manual');return new Response(null,{status:302,headers:{Location:'https://example.invalid'}});}});
 await assert.rejects(()=>api('/repos/'+repo+'/installation'),/GITHUB_HTTP_302/);
 assert.equal(options.headers.Authorization,'Bearer dummy');
});
test('scope verification uses Worker-compatible no-follow fetch and revokes on redirect',async()=>{
 let revoked=false;
 const app=async()=>({token:'dummy',permissions:{contents:'read',metadata:'read'}});
 await assert.rejects(()=>mintScopedToken(app,1,repo,{contents:'read'},{fetcher:async(url,o)=>{
  assert.equal(o.redirect,'manual');if(o.method==='DELETE'){revoked=true;return new Response(null,{status:204});}
  return new Response(null,{status:302,headers:{Location:'https://example.invalid'}});
 }}),/TOKEN_SCOPE_UNAVAILABLE/);
 assert.equal(revoked,true);
});
