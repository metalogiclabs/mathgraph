#!/usr/bin/env node
// Public GitHub readback for one reporter-authored issue and AI-assisted PR.
// Run before and after native tests. Fails closed on head/base or source drift.
// Does NOT establish a project-maintainer-approved acceptance requirement.
import {createHash} from 'node:crypto'
const tag=process.argv[2]
if(!['before','after'].includes(tag))throw Error('BAD_SOURCE_PIN_PHASE')
const get=async u=>{
 const r=await fetch(u,{headers:{
   Accept:'application/vnd.github+json','User-Agent':'metalogic-research-source-pin'}})
 if(!r.ok)throw Error('GITHUB_SOURCE_READ_FAILED '+r.status+' '+u)
 return r.json()
}
const [pr,issue]=await Promise.all([
 get('https://api.github.com/repos/eemeli/yaml/pulls/738'),
 get('https://api.github.com/repos/eemeli/yaml/issues/733')
])
const HEAD='9a1c4bd1a5c76272fd66a7a75c3aa37c54fd129d'
const BASE='528ef30d6ded4bd9f2c3521b670eb2b29d503c5c'
if(pr.state!=='open'||pr.head?.sha!==HEAD||pr.base?.sha!==BASE||
 issue.number!==733||issue.state!=='open'||
 issue.updated_at!=='2026-10-22T17:34:17Z'||
 !issue.body?.includes('### Expected behaviour')||
 !pr.body?.includes('fixes #733')||
 !pr.body?.includes('### LLM Use'))
 throw Error('PUBLIC_SOURCE_DRIFT_OR_AUTHORITY_MISMATCH')
const sha=s=>createHash('sha256').update(s).digest('hex')
const out={schema:'mathgraph-check-source-readback-yaml733-v0',
 phase:tag,observedAt:new Date().toISOString(),
 repository:'eemeli/yaml',issue:733,issueUpdated:issue.updated_at,
 issueTitle:issue.title,issueAuthor:issue.user?.login,
 issueBodySha256:sha(issue.body),
 pr:738,prAuthor:pr.user?.login,prTitle:pr.title,
 prDescriptionSha256:sha(pr.body),prBaseSha:pr.base.sha,prHeadSha:pr.head.sha,
 prState:pr.state,prMerged:pr.merged===true,
 reporterAuthoredRequirement:true,maintainerApprovalOfCorrectness:false,
 sourceReadType:'READ_ONLY_PUBLIC_GITHUB_API',ownerAuthority:'NOT_AUTHENTICATED',
 permission:'ADVISORY_ONLY'}
process.stdout.write(JSON.stringify(out,null,2)+'\n')
