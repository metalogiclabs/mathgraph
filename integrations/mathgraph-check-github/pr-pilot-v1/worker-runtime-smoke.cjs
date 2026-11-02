// Install miniflare@4.20260730.0 in an external temporary prefix; no production secrets.
const {createRequire}=require('node:module');
const path=require('node:path');
const assert=require('node:assert/strict');
const runtimeRequire=createRequire(path.resolve(process.env.MATHGRAPH_RUNTIME_PREFIX,'package.json'));
const {Miniflare}=runtimeRequire('miniflare');
(async()=>{
 const mf=new Miniflare({modules:true,modulesRoot:__dirname,scriptPath:path.join(__dirname,'worker-runtime-fixture.mjs'),compatibilityDate:'2026-07-29',compatibilityFlags:['nodejs_compat'],outboundService:r=>r.method==='DELETE'?new Response(null,{status:204}):new Response(null,{status:302,headers:{Location:'https://example.invalid/redirect'}})});
 try{
  assert.equal(await (await mf.dispatchFetch('http://local/client')).text(),'GITHUB_HTTP_302');
  assert.equal(await (await mf.dispatchFetch('http://local/scope')).text(),'TOKEN_SCOPE_UNAVAILABLE_HTTP_302');
  console.log('workerd: client and scope redirects rejected without following; PASS');
 }finally{await mf.dispose();}
})().catch(e=>{console.error(e);process.exitCode=1;});
