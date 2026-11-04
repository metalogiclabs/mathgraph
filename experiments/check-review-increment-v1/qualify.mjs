import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {executionContext} from '../../integrations/mathgraph-check-github/pr-pilot-v1/context.mjs';
import {githubClient} from '../../integrations/mathgraph-check-github/pr-pilot-v1/github.mjs';
import {admitRequest} from '../../integrations/mathgraph-check-github/pr-pilot-v1/policy.mjs';
import {captureRepositorySnapshot} from '../../integrations/mathgraph-check-github/pr-pilot-v1/repository-contract.mjs';
import {captureClaimSnapshot} from '../../integrations/mathgraph-check-github/pr-pilot-v1/claim.mjs';
import {capturePublicReview,publicReviewSummary} from '../../integrations/mathgraph-check-github/pr-pilot-v1/public-review.mjs';
const [phase,dir,number]=process.argv.slice(2),context=executionContext(),repository='metalogiclabs/L4YAML';
const cohort=JSON.parse(await readFile(new URL('./FOLLOWUP-2026-11-04.json',import.meta.url))),rows=[cohort.primary,...cohort.secondary];
const expected={31:{upstream:212,profile:'traceof',cases:7,parity:4,differences:3},32:{upstream:211,profile:'ledger-diff',cases:11,parity:11,differences:0},33:{upstream:209,profile:'residue-classes',cases:9,parity:4,differences:5}};
const save=async(n,v)=>writeFile(dir+'/'+n+'.json',JSON.stringify(v,null,2)+'\n'),get=async n=>JSON.parse(await readFile(dir+'/'+n+'.json'));
if(phase==='prepare'){
 await mkdir(dir,{recursive:true});const e=expected[number];assert.ok(e);const frozen=rows.find(r=>(r.number??r.upstream_pr)===e.upstream);
 const api=githubClient(process.env.GITHUB_TOKEN,{repository}),upstream=githubClient(process.env.GITHUB_TOKEN,{repository:'nasa-jpl/L4YAML'});
 const pr=await api('/repos/'+repository+'/pulls/'+number),files=await api('/repos/'+repository+'/pulls/'+number+'/files?per_page=100');
 assert.equal(pr.head.sha,frozen.head_sha);assert.equal(pr.base.sha,frozen.base_sha);
 const request=admitRequest({repository,pr,files,filesComplete:files.length===pr.changed_files,permission:'admin',comment:{id:context.run_id,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}}});
 assert.equal(request.support.supported,true);assert.equal(request.profile.cli_profile,e.profile);assert.equal(request.profile.public_review_pr,e.upstream);request.qualification_only=true;
 let snapshot=await captureRepositorySnapshot(request,api);if(request.profile.claim_profile)snapshot=await captureClaimSnapshot(request,snapshot,upstream);
 snapshot.public_review=await capturePublicReview({repository,number:request.number,head_sha:request.head_sha,base_sha:request.base_sha},e.upstream,upstream);
 await save('request',request);await save('contract-snapshot',snapshot);await save('qualification',{context,kind:'READ_ONLY_NO_APP_PUBLICATION_NO_MODEL_CALLS'});
 const hashes={};for(const n of(await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=createHash('sha256').update(await readFile(dir+'/'+n)).digest('hex');await save('manifest',{context,hashes});
}else if(phase==='verify'){
 const a=await get('assessment'),r=await get('request'),e=expected[r.number];assert.ok(e);assert.equal(a.cases.length,e.cases);assert.equal(a.cases.filter(c=>c.state==='PARITY').length,e.parity);assert.equal(a.cases.filter(c=>c.state==='DIFFERENCE').length,e.differences);
 const peer=publicReviewSummary(a.public_review,{repository:r.repository,number:r.number,head_sha:r.head_sha,base_sha:r.base_sha});assert.equal(peer.status,'PUBLIC_RECORD_OBSERVED');assert.equal(peer.verdict,e.upstream===209?'UNKNOWN':'NO_ISSUES_REPORTED');
 if(r.number===31)assert.equal(a.claim.status,'SUPPORTED');
 console.log(JSON.stringify({pr:r.number,native:a.status,cases:e.cases,peer:peer.verdict,whole_pr:'UNKNOWN'}));
}else throw Error('UNKNOWN_PHASE');
