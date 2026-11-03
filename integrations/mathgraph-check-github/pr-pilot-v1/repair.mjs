import {createHash} from 'node:crypto';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export async function createRepair(request,patch,publication,api){
 const root='/repos/'+request.repository;
 const isFresh=p=>p.state==='open'&&p.head?.sha===request.head_sha&&p.base?.sha===request.base_sha&&p.head.repo?.full_name===request.repository;
 const pr=await api(root+'/pulls/'+request.number);ensure(isFresh(pr),'STALE_REPAIR');
 const name=`mathgraph/pr-${request.number}-${request.head_sha.slice(0,10)}-${patch.patched_sha256.slice(0,10)}`;
 const head=await api(root+'/git/commits/'+request.head_sha);
 ensure(/^[a-f0-9]{40}$/.test(head.tree?.sha??''),'INVALID_BASE_TREE');
 const tree=await api(root+'/git/trees',{method:'POST',body:{base_tree:head.tree.sha,tree:[{path:request.profile.path,mode:'100644',type:'blob',content:patch.content}]}});
 const commit=await api(root+'/git/commits',{method:'POST',body:{message:'fix: satisfy frozen independent ledger probes',tree:tree.sha,parents:[request.head_sha]}});
 const comparison=await api(root+'/compare/'+request.head_sha+'...'+commit.sha);
 const blob=createHash('sha1').update('blob '+Buffer.byteLength(patch.content)+'\0'+patch.content).digest('hex');
 ensure(comparison.files?.length===1&&comparison.files[0].filename===request.profile.path&&comparison.files[0].status==='modified'&&comparison.files[0].sha===blob,'REPAIR_DIFF_MISMATCH');
 ensure(isFresh(await api(root+'/pulls/'+request.number)),'STALE_REPAIR');
 // A qualified draft may already have been published through a research replay.
 // Reuse only the same one-parent tree on the exact source, never a similar diff.
 const drafts=await api(root+'/pulls?state=open&base='+encodeURIComponent(pr.head.ref)+'&per_page=100');
 ensure(Array.isArray(drafts),'INVALID_REPAIR_HISTORY');
 for(const candidate of drafts){
  if(!candidate.draft||candidate.state!=='open'||candidate.base?.sha!==request.head_sha||candidate.head?.repo?.full_name!==request.repository)continue;
  const prior=await api(root+'/git/commits/'+candidate.head.sha);
  if(prior.tree?.sha!==tree.sha||prior.parents?.length!==1||prior.parents[0].sha!==request.head_sha)continue;
  const current=await api(root+'/pulls/'+candidate.number);
  ensure(current.draft===true&&current.state==='open'&&current.head?.sha===candidate.head.sha&&current.base?.sha===request.head_sha,'REPAIR_CANDIDATE_CHANGED');
  ensure(isFresh(await api(root+'/pulls/'+request.number)),'STALE_REPAIR');return current.html_url;
 }
 const listPath=root+'/pulls?state=all&head='+encodeURIComponent(request.repository.split('/')[0]+':'+name)+'&base='+encodeURIComponent(pr.head.ref);
 let created=false,prAttempted=false;
 try{
  try{await api(root+'/git/refs',{method:'POST',body:{ref:'refs/heads/'+name,sha:commit.sha}});created=true;}catch(e){
   if(e.message!=='GITHUB_HTTP_422')throw e;const existing=await api(root+'/git/ref/heads/'+name),c=await api(root+'/git/commits/'+existing.object.sha);ensure(c.tree.sha===tree.sha&&c.parents.length===1&&c.parents[0].sha===request.head_sha,'REPAIR_BRANCH_COLLISION');
  }
  const candidates=await api(listPath);
  if(candidates.length){ensure(candidates.length===1&&candidates[0].draft===true&&candidates[0].state==='open','REPAIR_PR_COLLISION');return candidates[0].html_url;}
  ensure(isFresh(await api(root+'/pulls/'+request.number)),'STALE_REPAIR');
  prAttempted=true;
  const repair=await api(root+'/pulls',{method:'POST',body:{title:'Repair independently reproduced ledger probe failures',head:name,base:pr.head.ref,draft:true,body:`Candidate repair for #${request.number}, source ${request.head_sha}.\n\nThe model-generated patch passes the unchanged generated probes, protected original guards and repository gate in the recorded finite scope. Withdrawal reproduces the observed failures. Model-inferred requirements remain unverified; this is not full-library correctness or merge approval.\n\nEvidence: ${publication.run_url}`}});
  ensure(repair.draft===true&&repair.base.sha===request.head_sha,'REPAIR_READBACK_MISMATCH');return repair.html_url;
 }catch(e){
  // Delete only a ref created by this attempt, still pointing to this exact commit,
  // and only when no draft could have been created. An ambiguous API failure keeps
  // the ref as evidence rather than risking another actor's branch or draft.
  if(created){let safe=!prAttempted;if(prAttempted){try{safe=(await api(listPath)).length===0;}catch{safe=false;}}
   if(safe){const current=await api(root+'/git/ref/heads/'+name);if(current.object.sha===commit.sha)await api(root+'/git/refs/heads/'+name,{method:'DELETE'});}
  }throw e;
 }
}
