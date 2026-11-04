import test from 'node:test';import assert from 'node:assert/strict';
import * as peer from './public-review.mjs';
const head='1'.repeat(40),base='2'.repeat(40),subject={repository:'metalogiclabs/L4YAML',number:31,head_sha:head,base_sha:base};
const record=(body='## ✅ Devin Review: No Issues Found',commit=head)=>({id:5745174112,user:{id:158243242,login:'devin-ai-integration[bot]',type:'Bot'},state:'COMMENTED',commit_id:commit,body,submitted_at:'2026-11-03T00:02:04Z',html_url:'https://github.com/nasa-jpl/L4YAML/pull/212#pullrequestreview-5745174112'});
const packet=(reviews=[record()],comments=[])=>({subject,upstream:{repository:'nasa-jpl/L4YAML',number:212,head_sha:head,base_sha:base},reviews,comments,complete:true});
const admit=p=>peer.publicReviewSummary?.(p,subject);
test('same-head explicit public verdict retains limits and cannot authorize a repair',()=>{const r=admit(packet());assert.equal(r?.status,'PUBLIC_RECORD_OBSERVED');assert.equal(r.verdict,'NO_ISSUES_REPORTED');assert.equal(r.review_time_base,'UNKNOWN');assert.equal(r.confirmed_misses,'UNKNOWN');assert.equal(r.repair_authority,false);});
test('earlier finding is not transferred to empty same-head reviews',()=>{const r=admit(packet([record('found 2 potential issues','3'.repeat(40)),{...record(''),id:5745174113}]));assert.equal(r?.verdict,'UNKNOWN');assert.equal(r.other_head_review_count,1);});
test('absence of reviews is not a clean verdict',()=>{assert.equal(admit(packet([]))?.verdict,'UNKNOWN');});
test('different source pair withdraws public-record comparison',()=>{const p=packet();p.upstream.base_sha='3'.repeat(40);assert.equal(admit(p)?.status,'UNKNOWN');});
test('spoofed reviewer identity cannot supply a clean verdict',()=>{const p=packet();p.reviews[0].user.id=1;assert.equal(admit(p)?.verdict,'UNKNOWN');});
test('incomplete pagination cannot supply a public verdict',()=>{const p=packet();p.complete=false;assert.equal(admit(p)?.status,'UNKNOWN');});
test('nonempty exact-head public comments are reported independently of summary',()=>{const p=packet([record('')],[{id:4,pull_request_review_id:5745174112,commit_id:head,body:'Observation',user:record().user}]);assert.equal(admit(p)?.public_inline_count,1);assert.equal(admit(p)?.verdict,'PUBLIC_COMMENTS_PRESENT');});
test('only the declared upstream can supply peer context',()=>{const p=packet();p.upstream.repository='other/L4YAML';assert.equal(admit(p)?.status,'UNKNOWN');});
test('capture follows complete review/comment pagination and retains current source pair',async()=>{const calls=[];const api=async p=>{calls.push(p);if(!p.includes('?'))return {base:{sha:base},head:{sha:head}};return p.includes('/reviews?')?[record()]:[];};const p=await peer.capturePublicReview(subject,212,api);assert.equal(admit(p).verdict,'NO_ISSUES_REPORTED');assert.equal(calls.length,3);});
test('capture rejects a full bounded pagination window instead of claiming completeness',async()=>{const api=async p=>!p.includes('?')?{base:{sha:base},head:{sha:head}}:Array.from({length:100},()=>record());await assert.rejects(peer.capturePublicReview(subject,212,api),/PAGINATION_INCOMPLETE/);});

test('old inline anchors remain historical even inside a same-head review submission',()=>{const p=packet([record('')],[{id:4,pull_request_review_id:5745174112,commit_id:'3'.repeat(40),body:'Fixed in current head',user:record().user}]);const r=admit(p);assert.equal(r.public_inline_count,0);assert.equal(r.other_head_inline_count,1);assert.equal(r.verdict,'UNKNOWN');});
