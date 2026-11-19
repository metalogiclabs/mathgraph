#!/usr/bin/env node
'use strict';
/** Reconstructed orchestration of preregistered v5/v6/file-size/lexical arms.
 * Scanner code and source selection are immutable; no bug/repair warrant. */
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
function gitBlobSha(bytes){return crypto.createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');}
function lexicalScore(s){return (s.match(/\b(?:cache|Map|Set|hash|floor|round|lookup|reuse)\b/gi)||[]).length;}
function rankUniqueFiles(candidates,n=3){
 const seen=new Set(),result=[];
 for(const x of candidates.slice().sort((a,b)=>b.score-a.score||a.file.localeCompare(b.file)||String(a.id||'').localeCompare(String(b.id||'')))){
  if(seen.has(x.file))continue;
  seen.add(x.file);result.push(x);if(result.length===n)break;
 }return result;
}
function checkManifest(m){
 if(!m||!Array.isArray(m.selected_files)||m.expected_path_count!==m.selected_files.length||
    !/^[0-9a-f]{40}$/.test(m.target_ref||''))throw Error('INVALID_MANIFEST');
 const seen=new Set();for(const f of m.selected_files){
  if(typeof f.path!=='string'||!f.path.startsWith('src/ol/')||!f.path.endsWith('.js')||
    path.isAbsolute(f.path)||f.path.includes('\\')||f.path.split('/').some(s=>!s||s==='..'||s==='.'))throw Error('INVALID_SOURCE_PATH');
  if(seen.has(f.path))throw Error('DUPLICATE_SOURCE_PATH');seen.add(f.path);
  if(!Number.isInteger(f.bytes)||f.bytes<0||!/^[0-9a-f]{40}$/.test(f.git_blob_sha||''))throw Error('INVALID_SOURCE_RECORD');
 }
}
function verifyScanner(root,name,expected){
 if(!expected)return;
 const actual=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex');
 if(actual!==expected)throw Error('SCANNER_DIGEST_MISMATCH:'+name);
}
function runTrial({manifest,sourceRoot,scannerRoot}){
 checkManifest(manifest);
 const commit=execFileSync('git',['-C',sourceRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 if(commit!==manifest.target_ref)throw Error('SOURCE_COMMIT_MISMATCH');
 verifyScanner(scannerRoot,'mathgraph_ast_obligations_v5.js',manifest.scanner_v5_sha256);
 verifyScanner(scannerRoot,'mathgraph_ast_obligations_v6.js',manifest.scanner_v6_sha256);
 // Verify ALL original source before using a single observation for ranking.
 const checked=manifest.selected_files.map(f=>{
  const target=path.join(sourceRoot,f.path);
  if(!fs.existsSync(target))throw Error('MISSING_SOURCE:'+f.path);
  if(!fs.lstatSync(target).isFile())throw Error('NONREGULAR_SOURCE:'+f.path);
  const bytes=fs.readFileSync(target);
  if(bytes.length!==f.bytes)throw Error('SIZE_MISMATCH:'+f.path);
  if(gitBlobSha(bytes)!==f.git_blob_sha)throw Error('BLOB_MISMATCH:'+f.path);
  return {f,source:bytes.toString('utf8')};
 });
 const scanV5=require(path.join(scannerRoot,'mathgraph_ast_obligations_v5.js')).scan;
 const scanV6=require(path.join(scannerRoot,'mathgraph_ast_obligations_v6.js')).scan;
 const ts=require(path.join(scannerRoot,'node_modules/typescript'));
 const hot5=[],hot6=[],files=[],failures=[];
 for(const {f,source} of checked){
  const file=f.path;
  const parsed=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
  const diag=parsed.parseDiagnostics.map(x=>({line:parsed.getLineAndCharacterOfPosition(x.start).line+1,code:x.code}));
  const e={file,git_blob_sha:f.git_blob_sha,bytes:f.bytes,lexical_score:lexicalScore(source),parse_diagnostics:diag};
  try{
   const a=scanV5(source,file),b=scanV6(source,file);
   if(JSON.stringify(a.hotspots.map(x=>x.id).sort())!==JSON.stringify(b.hotspots.map(x=>x.id).sort()))throw Error('SCANNER_RELATION_CHANGED');
   e.method_count_v5=a.method_count;e.method_count_v6=b.method_count;
   e.candidates_v5=a.hotspots.length;e.candidates_v6=b.hotspots.length;
   for(const x of a.hotspots)hot5.push({file,id:x.id,score:x.score,loss_class:x.loss_class,judgment:x.judgment});
   for(const x of b.hotspots)hot6.push({file,id:x.id,score:x.score,v5_score:x.v5_score,
    loss_class:x.loss_class,consumer_demand:x.consumer_demand,judgment:x.judgment,contract:x.contract});
  }catch(err){e.scanner_failure=true;failures.push({file,error:String(err.message||err)});}
  files.push(e);
 }
 const rankings={
  v6:rankUniqueFiles(hot6),v5:rankUniqueFiles(hot5),
  file_size:rankUniqueFiles(files.map(x=>({file:x.file,id:x.file,score:x.bytes}))),
  lexical_cache:rankUniqueFiles(files.map(x=>({file:x.file,id:x.file,score:x.lexical_score})))
 };
 return {schema:'mathgraph/ast-v6-openlayers-blind-result-v1',source_ref:commit,
  source_integrity:'PER_BLOB_CHECKED',candidate_status:'CANDIDATE_ONLY',requirement_status:'UNKNOWN',change_permission:false,
  coverage:{selected_count:checked.length,checked_count:checked.length,
   scanned_count:checked.length-failures.length,diagnostic_files:files.filter(x=>x.parse_diagnostics.length).length,scanner_failures:failures},
  rankings,review_union:[...new Set(Object.values(rankings).flat().map(x=>x.file))].sort(),
  candidate_counts:{v5:hot5.length,v6:hot6.length},source_evidence:files,
  limits:['Static ranking; no admitted requirement or native behavioral oracle',
   'Same-file consumer demand is not exhaustive; external callers and shared effects remain UNKNOWN',
   'A top-three candidate does not establish a bug, fix permission or whole-repo safety']};
}
if(require.main===module){
 const [manifestFile,sourceRoot,scannerRoot,outputFile]=process.argv.slice(2);
 if(!manifestFile||!sourceRoot||!scannerRoot){console.error('Usage: node runner.js manifest sourceRoot scannerRoot [output]');process.exit(2);}
 try{
  const manifest=JSON.parse(fs.readFileSync(manifestFile,'utf8'));
  const result=runTrial({manifest,sourceRoot,scannerRoot});
  const output=JSON.stringify(result,null,2)+'\n';
  if(outputFile)fs.writeFileSync(outputFile,output);
  console.log(JSON.stringify({integrity:result.source_integrity,coverage:result.coverage,
   candidate_counts:result.candidate_counts,rankings:result.rankings,review_union:result.review_union}));
 }catch(err){console.error(err.stack||err);process.exitCode=1;}
}
module.exports={runTrial,rankUniqueFiles,lexicalScore,gitBlobSha};
