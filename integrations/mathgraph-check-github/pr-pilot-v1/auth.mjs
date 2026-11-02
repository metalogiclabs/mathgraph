import {githubClient} from './github.mjs';
export async function mintScopedToken(app,installation,repository,permissions,{fetcher=fetch}={}){
 const t=await app(`/app/installations/${installation}/access_tokens`,{method:'POST',body:{repositories:[repository.split('/')[1]],permissions}});
 if(typeof t.token!=='string')throw Error('TOKEN_NOT_RETURNED');
 const client=githubClient(t.token,{repository,fetcher});
 try{
  if(!t.permissions||Object.entries(permissions).some(([k,v])=>t.permissions[k]!==v)||Object.keys(t.permissions).some(k=>k!=='metadata'&&!Object.hasOwn(permissions,k)))throw Error('TOKEN_PERMISSION_SCOPE_MISMATCH');
  const response=await fetcher('https://api.github.com/installation/repositories?per_page=100',{headers:{Authorization:'Bearer '+t.token,Accept:'application/vnd.github+json'},redirect:'manual',signal:AbortSignal.timeout(20000)});
  if(!response.ok)throw Error('TOKEN_SCOPE_UNAVAILABLE');const repos=await response.json();
  if(repos.total_count!==1||repos.repositories?.length!==1||repos.repositories[0].full_name!==repository)throw Error('TOKEN_REPOSITORY_SCOPE_MISMATCH');
  return t.token;
 }catch(e){await client('/installation/token',{method:'DELETE'});throw e;}
}
