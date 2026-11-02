// No credentials: exercised only by the local workerd regression harness.
import {githubClient} from './github.mjs';
import {mintScopedToken} from './auth.mjs';
export default {async fetch(request){
 const repo='metalogiclabs/L4YAML';
 try{
  if(new URL(request.url).pathname==='/scope')await mintScopedToken(async()=>({token:'runtime-test-only',permissions:{contents:'read',metadata:'read'}}),1,repo,{contents:'read'});
  else await githubClient('runtime-test-only',{repository:repo})('/repos/'+repo+'/installation');
  return new Response('UNEXPECTED_SUCCESS',{status:500});
 }catch(e){return new Response(e.message);}
}};
