import {mkdtemp,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {nativeDemo,dockerRunner,brokenSource,repairedSource} from './mention-native-demo-v1.mjs';
const dir=await mkdtemp(join(tmpdir(),'mathgraph-native-controls-'));
try{
 const nativeRun=await dockerRunner(dir);
 const run=async(name,source)=>{const result=await nativeRun(name,source);console.log(JSON.stringify({unit:name,exit_code:result.code,native_output:result.output.slice(0,8000)}));return result;};
 const sanity=await run('Sanity','import Std\nexample : 1 + 1 = 2 := by decide\n');
 const negative=await run('Negative','import Std\nexample : False := by trivial\n');
 if(sanity.code!==0||negative.code!==1)throw Error('NATIVE_CONTROLS_FAILED');
 const baseline=await nativeDemo({source:brokenSource,run});
 const fixed=await nativeDemo({source:repairedSource('by simp'),run});
 console.log(JSON.stringify({baseline,fixed},null,2));
 if(baseline.status!=='CLAIM_NOT_ESTABLISHED'||fixed.status!=='ORIGINAL_TARGET_VERIFIED')throw Error('NATIVE_DEMO_BOUNDARY_FAILED');
}finally{await rm(dir,{recursive:true,force:true});}
