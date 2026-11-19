'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {runTrial,rankUniqueFiles,lexicalScore,gitBlobSha}=require('../experiments/source_obligation_selection/run_v6_blind_trial');
const dirs=[];
test.after(()=>dirs.forEach(p=>fs.rmSync(p,{recursive:true,force:true})));
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'v6-holdout-test-'));dirs.push(root);
 execFileSync('git',['-C',root,'init','-q']);
 const files={'src/ol/source/A.js':'const cache=new Map(); function get(x){return cache.get(x)}\n',
   'src/ol/source/B.js':'function plain(x){return x}\n'};
 const selected_files=[];
 for(const [p,text] of Object.entries(files).sort(([a],[b])=>a.localeCompare(b))){
  const abs=path.join(root,p);fs.mkdirSync(path.dirname(abs),{recursive:true});fs.writeFileSync(abs,text);
  selected_files.push({path:p,bytes:Buffer.byteLength(text),git_blob_sha:gitBlobSha(Buffer.from(text))});
 }
 execFileSync('git',['-C',root,'add','.']);
 execFileSync('git',['-C',root,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture']);
 return {root,manifest:{target_ref:execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),
   expected_path_count:2,selected_files}};
}
const scannerRoot=process.env.AST_V6_FROZEN_DIR||path.resolve(__dirname,'../../v6-runner');
test('Git blob SHA is exact, not a plain file digest',()=>{
 assert.equal(gitBlobSha(Buffer.from('hello\n')),'ce013625030ba8dba906f756967f9e9ca394464a');
});
test('frozen lexical baseline counts only whole tokens',()=>{
 assert.equal(lexicalScore('Cache cache map Maps hash floor round lookup reuse'),8);
 assert.equal(lexicalScore('caches maplike hashed'),0);
});
test('unique-file top-three has stable path ties and no repeated file',()=>{
 const sorted=rankUniqueFiles([{file:'z.js',id:'a',score:8},{file:'z.js',id:'b',score:10},
  {file:'b.js',id:'b',score:10},{file:'a.js',id:'a',score:10},{file:'q.js',id:'q',score:1}],3);
 assert.deepEqual(sorted.map(x=>x.file),['a.js','b.js','z.js']);
});
test('exact source yields four rankings but no warrant',()=>{
 const f=fixture(),r=runTrial({manifest:f.manifest,sourceRoot:f.root,scannerRoot});
 assert.equal(r.source_integrity,'PER_BLOB_CHECKED');
 assert.deepEqual(Object.keys(r.rankings).sort(),['file_size','lexical_cache','v5','v6']);
 assert.equal(r.coverage.selected_count,2);
 assert.equal(r.candidate_status,'CANDIDATE_ONLY');
 assert.equal(r.requirement_status,'UNKNOWN');
 assert.equal(r.change_permission,false);
});
test('same-size source alteration refuses old frozen blob',()=>{
 const f=fixture(),file=path.join(f.root,'src/ol/source/B.js');
 const bytes=fs.readFileSync(file,'utf8');fs.writeFileSync(file,bytes.replace('plain','OTHER'));
 assert.throws(()=>runTrial({manifest:f.manifest,sourceRoot:f.root,scannerRoot}),/BLOB_MISMATCH/);
});
test('wrong source commit or duplicate and traversal paths fail closed',()=>{
 const f=fixture();f.manifest.target_ref='0'.repeat(40);
 assert.throws(()=>runTrial({manifest:f.manifest,sourceRoot:f.root,scannerRoot}),/SOURCE_COMMIT_MISMATCH/);
 f.manifest.target_ref=execFileSync('git',['-C',f.root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 f.manifest.selected_files.push({...f.manifest.selected_files[0]});f.manifest.expected_path_count++;
 assert.throws(()=>runTrial({manifest:f.manifest,sourceRoot:f.root,scannerRoot}),/DUPLICATE_SOURCE_PATH/);
 f.manifest.selected_files.pop();f.manifest.expected_path_count--;
 f.manifest.selected_files[0].path='../outside.js';
 assert.throws(()=>runTrial({manifest:f.manifest,sourceRoot:f.root,scannerRoot}),/INVALID_SOURCE_PATH/);
});
