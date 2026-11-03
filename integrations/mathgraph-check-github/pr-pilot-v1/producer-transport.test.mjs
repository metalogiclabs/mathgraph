import test from 'node:test';import assert from 'node:assert/strict';
import {downloadProducerArtifact} from './producer-transport.mjs';
test('artifact credential is limited to GitHub API and not forwarded to signed storage',async()=>{
 const calls=[];const fetcher=async(url,options)=>{calls.push({url,options});return calls.length===1?new Response(null,{status:302,headers:{location:'https://productionresults.blob.core.windows.net/receipt?sig=fixture'}}):new Response('zip-bytes');};
 assert.equal((await downloadProducerArtifact(123,'fixture-token',fetcher)).toString(),'zip-bytes');
 assert.equal(calls[0].options.headers.Authorization,'Bearer fixture-token');assert.equal(calls[1].options.headers,undefined);assert.equal(calls[1].options.redirect,'error');
});
for(const url of ['http://example.com/x','https://api.github.com/other','https://evilblob.core.windows.net.evil.test/x','https://user:pass@receipt.blob.core.windows.net/x'])test('reject unsafe download location '+new URL(url).hostname,async()=>{
 let n=0;await assert.rejects(downloadProducerArtifact(123,'fixture-token',async()=>{n++;return new Response(null,{status:302,headers:{location:url}});}));assert.equal(n,1);
});
test('oversized download fails at the byte boundary',async()=>{await assert.rejects(downloadProducerArtifact(123,'fixture-token',async()=>new Response(new Uint8Array(20*1024*1024+1))));});
