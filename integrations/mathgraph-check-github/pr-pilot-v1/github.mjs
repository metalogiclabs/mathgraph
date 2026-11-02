export function githubClient(token,{fetcher=fetch,repository}={}){
 return async(path,{method='GET',body}={})=>{
  if(!path.startsWith('/repos/'+repository+'/')&&!path.startsWith('/repos/metalogiclabs/mathgraph/')&&path!=='/installation/token'&&!/^\/app\/installations\/[1-9][0-9]*\/access_tokens$/.test(path))throw Error('GITHUB_PATH_FORBIDDEN');
  const response=await fetcher('https://api.github.com'+path,{method,redirect:'manual',headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json','Content-Type':'application/json','User-Agent':'MathGraph-Check-PR-Pilot'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  if(!response.ok)throw Error('GITHUB_HTTP_'+response.status);return response.status===204?{}:response.json();
 };
}
