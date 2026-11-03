// Read-only admission qualification against the real App draft and producer.
import {mkdir,readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {executionContext} from '../../integrations/mathgraph-check-github/pr-pilot-v1/context.mjs';
import {githubClient} from '../../integrations/mathgraph-check-github/pr-pilot-v1/github.mjs';
import {admitRequest} from '../../integrations/mathgraph-check-github/pr-pilot-v1/policy.mjs';
import {captureProducer,resolveProducer} from '../../integrations/mathgraph-check-github/pr-pilot-v1/producer-transport.mjs';
import {reviewedPlan} from '../../integrations/mathgraph-check-github/pr-pilot-v1/expectations.mjs';
const dir=process.argv[2]??'transport',context=executionContext(),repository='metalogiclabs/L4YAML';
const api=githubClient(process.env.GITHUB_TOKEN,{repository}),pr=await api('/repos/'+repository+'/pulls/27'),comparison=await api('/repos/'+repository+'/compare/'+pr.base.sha+'...'+pr.head.sha);
const request=admitRequest({repository,pr,files:comparison.files,filesComplete:pr.changed_files===comparison.files.length,permission:'admin',comment:{id:context.run_id,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}}});
assert.equal(request.profile.expectation_candidate,true);assert.equal(request.profile.expectation_profile,undefined);
const envelope=await captureProducer(request,context,api,api,process.env.GITHUB_TOKEN),admission=resolveProducer(envelope,request,context);
assert.equal(reviewedPlan(admission.subject),null);assert.equal(reviewedPlan(admission.subject,JSON.parse(JSON.stringify(admission.token))),null);assert.equal(reviewedPlan(admission.subject,admission.token).tests.length,2);
request.profile.expectation_profile='ledger-shell-producer-v1';request.qualification_only=true;
await mkdir(dir,{recursive:true});const save=async(n,v)=>writeFile(dir+'/'+n+'.json',JSON.stringify(v,null,2)+'\n');
await save('request',request);await save('producer-envelope',envelope);await save('producer-warrant',admission.graph);
await save('publication',{context,state:'QUALIFICATION_ONLY',run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/'+context.run_id});
// This separate fixture drives mutations against authenticated responses, never
// a live admission decision or an output label supplied by the source PR.
await writeFile(dir+'/producer-test-envelope.json',JSON.stringify({envelope,request}));
const hashes={};for(const n of(await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=createHash('sha256').update(await readFile(dir+'/'+n)).digest('hex');
await save('manifest',{context,hashes});
