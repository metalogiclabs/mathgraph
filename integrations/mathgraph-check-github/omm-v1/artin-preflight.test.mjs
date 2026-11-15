import test from 'node:test';
import assert from 'node:assert/strict';
import {artinStrongSource,artinRepairSource} from '../mention-artin-control-v1.mjs';
import {checkPublishedArtinInput} from './artin-preflight.mjs';

const reference='published-exercise';
const sample=(n=239)=>({
  number:n,state:'open',changed_files:n===239?2:1,
  head:{sha:n===239?'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17':'06f09cd5aaa866365ceb6540cd06389bd37a727c',repo:{full_name:'metalogiclabs/mathgraph'}},
  base:{sha:n===239?'dfd87d1e921953badedcfae21ade76bb38f5c04a':'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',repo:{full_name:'metalogiclabs/mathgraph'}}
});
function fixture(n=239,{mutate,source}={}){
 const pull=sample(n);mutate?.(pull);
 const files=n===239?[{filename:'mathgraph-demo/ArtinGenerators.lean',status:'added'},{filename:'mathgraph-demo/README.md',status:'added'}]:[{filename:'mathgraph-demo/ArtinGenerators.lean',status:'modified'}];
 const inputs=[];
 const fetch=async(url)=>{
  inputs.push(url);
  let body;
  if(url.endsWith(`/pulls/${n}`))body=JSON.stringify(pull);
  else if(url.endsWith(`/pulls/${n}/files?per_page=100`))body=JSON.stringify(files);
  else if(url.includes('/ProofNet-Verified/'))body=reference;
  else if(url.includes('/ArtinGenerators.lean'))body=source??(n===239?artinStrongSource:artinRepairSource);
  else throw Error('UNEXPECTED_URL');
  return {ok:true,text:async()=>body};
 };
 return {fetch,inputs};
}
test('both fixed public Artin controls are pinned to authenticated PR identity and exact candidate bytes',async()=>{
 for(const n of [239,240]){
  const {fetch,inputs}=fixture(n);
  const p=await checkPublishedArtinInput({number:n,fetch,
   verifyReference:reference==='published-exercise'?()=>true:undefined});
  assert.equal(p.request.number,n);
  assert.equal(p.request.head_sha,sample(n).head.sha);
  assert.equal(p.source,n===239?artinStrongSource:artinRepairSource);
  assert.equal(p.publishedSource,reference);
  assert.equal(inputs.length,4);
 }
});
test('changed head, foreign source or unexpected changed files all fail closed',async()=>{
 const changed=fixture(239,{mutate:p=>{p.head.sha='1'.repeat(40)}});
 await assert.rejects(checkPublishedArtinInput({number:239,fetch:changed.fetch,verifyReference:()=>true}),/PR_IDENTITY_CHANGED/);
 const candidate=fixture(240,{source:artinStrongSource});
 await assert.rejects(checkPublishedArtinInput({number:240,fetch:candidate.fetch,verifyReference:()=>true}),/SOURCE_BYTES_CHANGED/);
 const {fetch}=fixture(239);
 await assert.rejects(checkPublishedArtinInput({number:238,fetch,verifyReference:()=>true}),/UNREGISTERED_ARTIN_PR/);
});
test('unverified published original never reaches native qualification',async()=>{
 const {fetch}=fixture(239);
 await assert.rejects(checkPublishedArtinInput({number:239,fetch,verifyReference:()=>false}),/PUBLISHED_TARGET_CHANGED/);
});
